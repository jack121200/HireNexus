"""
ChromaDB Vector Store for Career RAG.
Persistent local database — survives server restarts.
Collection name matches what rag/ingestor.py creates.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── ChromaDB lazily imported so startup doesn't crash if not installed ────────
_chroma_client: Any = None
_collection: Any = None

# Allow override via env for docker vs local dev
DB_PATH = os.environ.get(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).resolve().parents[3] / "chroma_db"),
)
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "hirenexus_career_guidance")


def _get_collection():
    """Lazily initialise ChromaDB and return the career collection."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb  # noqa: import-outside-toplevel

        _chroma_client = chromadb.PersistentClient(path=DB_PATH)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("chromadb_ready", path=DB_PATH, collection=COLLECTION_NAME, docs=_collection.count())
    except ImportError:
        logger.error("chromadb_not_installed", hint="pip install chromadb")
        raise

    return _collection


def reset_collection_cache() -> None:
    """Force re-initialisation of the ChromaDB collection (e.g., after re-ingestion)."""
    global _collection, _chroma_client
    _collection = None
    _chroma_client = None


def add_documents(
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    """Upsert documents into ChromaDB."""
    col = _get_collection()
    col.upsert(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info("chromadb_upsert_done", count=len(documents))


def search(
    query_embedding: list[float],
    top_k: int = 5,
    where: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Cosine similarity search with optional ChromaDB metadata filter.
    Returns dict with keys: documents, metadatas, distances, ids.
    """
    col = _get_collection()
    total = col.count() or 1
    n = min(top_k, total)

    try:
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        # Fallback: retry without filter if filter caused an error
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

    return {
        "documents": results["documents"][0] if results["documents"] else [],
        "metadatas": results["metadatas"][0] if results["metadatas"] else [],
        "distances": results["distances"][0] if results["distances"] else [],
        "ids": results["ids"][0] if results["ids"] else [],
    }


def count() -> int:
    """Return total number of documents in the collection."""
    try:
        return _get_collection().count()
    except Exception:
        return 0
