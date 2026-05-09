"""
Hybrid retriever — combines vector (dense) search with BM25 (sparse).
alpha=0.6 means 60% vector weight, 40% BM25 keyword weight.

Metadata fields from rag/chunker.py:
  role       : e.g. "backend-engineer"
  audience   : "fresher" | "experienced" | "all"
  topic      : e.g. "skill-roadmap"
  topic_code : "T1".."T8"
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import numpy as np

from app.core.logging import get_logger
from . import vector_store as vs
from .embeddings import embed_query

logger = get_logger(__name__)

# In-memory BM25 index (rebuilt on first query or after indexing)
_bm25_corpus: list[str] = []
_bm25_ids: list[str] = []
_bm25_index: Any = None
_bm25_loaded: bool = False

_CHROMA_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).resolve().parents[3] / "chroma_db"),
)


def _load_bm25_from_cache() -> None:
    """Load BM25 corpus from the JSON file saved by rag/ingestor.py."""
    global _bm25_corpus, _bm25_ids, _bm25_index, _bm25_loaded
    if _bm25_loaded:
        return

    cache_path = Path(_CHROMA_DIR) / "bm25_corpus.json"
    if not cache_path.exists():
        logger.warning("bm25_corpus_cache_missing", path=str(cache_path))
        _bm25_loaded = True
        return

    try:
        from rank_bm25 import BM25Okapi  # noqa

        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        _bm25_corpus = [d["text"] for d in data]
        _bm25_ids = [d["id"] for d in data]
        tokenized = [t.lower().split() for t in _bm25_corpus]
        _bm25_index = BM25Okapi(tokenized)
        logger.info("bm25_index_loaded_from_cache", docs=len(_bm25_corpus))
    except ImportError:
        logger.warning("rank_bm25_not_installed", hint="pip install rank-bm25")
    except Exception as exc:
        logger.warning("bm25_cache_load_failed", error=str(exc))

    _bm25_loaded = True


def build_bm25_index(documents: list[str], doc_ids: list[str]) -> None:
    """Build (or rebuild) the BM25 index from a list of document strings."""
    global _bm25_corpus, _bm25_ids, _bm25_index, _bm25_loaded

    try:
        from rank_bm25 import BM25Okapi  # noqa

        tokenized = [d.lower().split() for d in documents]
        _bm25_index = BM25Okapi(tokenized)
        _bm25_corpus = documents
        _bm25_ids = doc_ids
        _bm25_loaded = True
        logger.info("bm25_index_built", docs=len(documents))
    except ImportError:
        logger.warning("rank_bm25_not_installed", hint="pip install rank-bm25")
        _bm25_index = None


def _get_bm25_scores(query: str) -> dict[str, float]:
    """Return normalized BM25 scores keyed by doc_id."""
    _load_bm25_from_cache()
    if _bm25_index is None or not _bm25_corpus:
        return {}

    tokens = query.lower().split()
    raw_scores: np.ndarray = _bm25_index.get_scores(tokens)
    max_score = float(raw_scores.max()) if raw_scores.max() > 0 else 1.0
    return {
        doc_id: float(score / max_score)
        for doc_id, score in zip(_bm25_ids, raw_scores)
    }


def _build_where_filter(
    role: Optional[str] = None,
    audience: Optional[str] = None,
    topic: Optional[str] = None,
) -> Optional[dict]:
    """Build a ChromaDB $and filter from optional metadata fields."""
    conditions = []

    if role:
        conditions.append({"role": {"$eq": role}})

    if audience and audience != "all":
        # Match exact audience OR "all" (content meant for everyone)
        conditions.append({"audience": {"$in": [audience, "all"]}})

    if topic:
        conditions.append({"topic": {"$eq": topic}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def hybrid_search(
    query: str,
    top_k: int = 5,
    role: Optional[str] = None,
    audience: Optional[str] = None,
    topic: Optional[str] = None,
    category_filter: Optional[str] = None,  # legacy compat → maps to role
    alpha: float = 0.6,
) -> list[dict[str, Any]]:
    """
    Retrieves top_k most relevant chunks using hybrid scoring.
    Supports new metadata fields: role, audience, topic.
    Legacy category_filter maps to role for backwards compatibility.
    Returns list of dicts with: id, content, metadata, score
    """
    effective_role = role or category_filter

    # 1. Build metadata filter
    where = _build_where_filter(
        role=effective_role,
        audience=audience,
        topic=topic,
    )

    # 2. Vector search (fetch extra for reranking)
    q_emb = embed_query(query).tolist()
    vec_results = vs.search(q_emb, top_k=top_k * 2, where=where)

    docs = vec_results["documents"]
    metas = vec_results["metadatas"]
    distances = vec_results["distances"]
    ids = vec_results["ids"]

    # If no vector results with filter — retry without filter
    if not docs and where:
        logger.warning("hybrid_search_filter_empty", role=effective_role, audience=audience, retrying=True)
        vec_results = vs.search(q_emb, top_k=top_k * 2, where=None)
        docs = vec_results["documents"]
        metas = vec_results["metadatas"]
        distances = vec_results["distances"]
        ids = vec_results["ids"]

    # 3. BM25 scores
    bm25_scores = _get_bm25_scores(query)

    # 4. Combine scores
    combined: dict[str, dict] = {}
    max_dist = max(distances) if distances else 1.0

    for doc, meta, dist, doc_id in zip(docs, metas, distances, ids):
        vec_score = 1.0 - (dist / max_dist) if max_dist > 0 else 0.0
        bm25_score = bm25_scores.get(doc_id, 0.0)
        final_score = alpha * vec_score + (1.0 - alpha) * bm25_score
        combined[doc_id] = {
            "id": doc_id,
            "content": doc,
            "metadata": meta,
            "score": final_score,
        }

    # Add pure BM25 hits not in vector results
    for doc_id, bm25_score in bm25_scores.items():
        if doc_id not in combined:
            try:
                idx = _bm25_ids.index(doc_id)
                combined[doc_id] = {
                    "id": doc_id,
                    "content": _bm25_corpus[idx],
                    "metadata": {},
                    "score": (1.0 - alpha) * bm25_score,
                }
            except ValueError:
                pass

    sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:top_k]
