# rag/ingestor.py
# Run from backend/ directory: python rag/ingestor.py
# Reads all_chunks.json, embeds with all-MiniLM-L6-v2 (local, free),
# stores vectors + metadata in ChromaDB (persistent).

import json
import os
from pathlib import Path

CHUNKS_FILE = Path(__file__).resolve().parents[1] / "data" / "chunks" / "all_chunks.json"
CHROMA_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).resolve().parents[1] / "chroma_db"),
)
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "hirenexus_career_guidance")
EMBEDDING_MODEL = os.environ.get("CAREER_EMBED_MODEL", "all-MiniLM-L6-v2")
BATCH_SIZE = 50


def run_ingestion():
    # Load chunks
    print("📂 Loading chunks...")
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"   → {len(chunks)} chunks loaded")

    # Load embedding model (downloads once, cached after)
    print(f"\n🧠 Loading embedding model: {EMBEDDING_MODEL}")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL)
    print("   → Model loaded")

    # Setup ChromaDB (persistent)
    print(f"\n🗄️  Setting up ChromaDB at: {CHROMA_DIR}")
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection if re-ingesting (fresh start)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"   → Existing collection '{COLLECTION_NAME}' deleted (fresh ingest)")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"   → Collection '{COLLECTION_NAME}' created")

    # Ingest in batches
    print(f"\n⚡ Embedding and ingesting (batch size: {BATCH_SIZE})...")
    total = len(chunks)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        batch_end = min(batch_start + BATCH_SIZE, total)

        texts = [c["text"] for c in batch]
        ids = [c["chunk_id"] for c in batch]
        metadatas = []

        for c in batch:
            # ChromaDB metadata values must be str/int/float/bool only
            meta: dict = {}
            for k, v in c["metadata"].items():
                if isinstance(v, list):
                    meta[k] = ",".join(str(x) for x in v)
                elif isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)
            metadatas.append(meta)

        # Match app.services.career_rag.embeddings: normalized float32 for cosine Chroma
        emb = model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        embeddings = emb.astype("float32").tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        print(f"   → Ingested {batch_end}/{total} chunks")

    print(f"\n✅ Ingestion complete!")
    print(f"✅ Total vectors stored: {collection.count()}")
    print(f"✅ ChromaDB saved at: {CHROMA_DIR}")

    # Also build BM25 index file for hybrid search startup
    print("\n🔍 Building BM25 index cache...")
    bm25_cache = [{"id": c["chunk_id"], "text": c["text"]} for c in chunks]
    bm25_path = Path(CHROMA_DIR) / "bm25_corpus.json"
    with open(bm25_path, "w", encoding="utf-8") as f:
        json.dump(bm25_cache, f, ensure_ascii=False)
    print(f"✅ BM25 corpus saved: {bm25_path}")


if __name__ == "__main__":
    run_ingestion()
