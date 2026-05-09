"""
ChromaDB Indexer — Run this script once to populate the vector database.
Usage: python -m app.services.career_rag.indexer
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "career_knowledge.json"


def build_index() -> None:
    """Load career_knowledge.json, embed chunks, and upsert into ChromaDB."""
    from .embeddings import embed_documents
    from .vector_store import add_documents, count
    from .hybrid_search import build_bm25_index

    print(f"Loading knowledge base from {DATA_PATH}...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for i, entry in enumerate(raw):
        content = entry.get("content", "").strip()
        if not content:
            continue

        doc_id = f"career_{i}"
        documents.append(content)
        metadatas.append({
            "title": entry.get("title", entry.get("role", "Career Guide")),
            "source": entry.get("source", "HireNexus Knowledge Base"),
            "category": entry.get("category", entry.get("type", "general")),
            "role": entry.get("role", "general"),
            "level": entry.get("level", "all"),
        })
        ids.append(doc_id)

    print(f"Embedding {len(documents)} documents...")
    embeddings = embed_documents(documents)

    print("Inserting into ChromaDB...")
    add_documents(
        documents=documents,
        embeddings=[emb.tolist() for emb in embeddings],
        metadatas=metadatas,
        ids=ids,
    )

    print("Building BM25 index...")
    build_bm25_index(documents, ids)

    total = count()
    print(f"\n✅ Done! ChromaDB now has {total} documents.")
    print("Your Career Guide RAG is ready to use.")


if __name__ == "__main__":
    build_index()
