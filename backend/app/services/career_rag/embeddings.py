"""
Embedding Model — sentence-transformers (local, free, cached).
Uses all-MiniLM-L6-v2 by default: 384-dim, fast, high quality.
"""
from __future__ import annotations

import os
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.logging import get_logger

logger = get_logger(__name__)

_model: SentenceTransformer | None = None
DEFAULT_MODEL = os.environ.get("CAREER_EMBED_MODEL", "all-MiniLM-L6-v2")


def get_model() -> SentenceTransformer:
    """Lazy-load and cache the embedding model."""
    global _model
    if _model is None:
        logger.info("loading_embedding_model", model=DEFAULT_MODEL)
        _model = SentenceTransformer(DEFAULT_MODEL)
        logger.info("embedding_model_loaded", dim=_model.get_sentence_embedding_dimension())
    return _model


def embed_documents(texts: List[str], batch_size: int = 32) -> np.ndarray:
    """
    Embed a list of documents.
    Returns normalized float32 ndarray of shape (N, dim).
    """
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string. Returns shape (dim,)."""
    model = get_model()
    embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embedding.astype(np.float32)
