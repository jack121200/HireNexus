"""
Data Processor — cleans, categorizes, and chunks scraped career content.
Run after data_collector.py to prepare chunks for ChromaDB indexing.

Run: python -m app.services.career_rag.data_processor
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAW_PATH = Path(__file__).parent / "data" / "raw_documents.json"
PROCESSED_PATH = Path(__file__).parent / "data" / "processed_chunks.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "resume": ["resume", "cv", "curriculum vitae", "ats", "applicant tracking", "cover letter", "portfolio"],
    "interview": ["interview", "behavioral", "technical interview", "star method", "coding round", "system design", "leet"],
    "salary": ["salary", "negotiat", "compensation", "offer", "ctc", "package", "hike", "pay"],
    "career_path": ["career change", "transition", "career path", "roadmap", "career switch", "pivot", "faang"],
    "skills": ["learn", "upskill", "certification", "course", "skill", "language", "framework", "open source"],
    "job_search": ["job search", "job hunt", "remote job", "apply", "job board", "linkedin", "referral"],
    "networking": ["network", "linkedin", "connect", "community", "meetup", "discord"],
    "general": [],
}

PROMO_PHRASES = [
    r"subscribe to our newsletter",
    r"follow us on",
    r"click here",
    r"sign up now",
    r"limited time offer",
    r"advertisement",
    r"share this article",
    r"read more at",
]


def clean_text(text: str) -> str:
    """Remove noise from scraped text."""
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Remove email addresses
    text = re.sub(r"\S+@\S+\.\S+", "", text)
    # Remove promotional content
    for phrase in PROMO_PHRASES:
        text = re.sub(phrase, "", text, flags=re.IGNORECASE)
    return text.strip()


def categorize(text: str, existing: str = "") -> str:
    """Auto-detect category from text content."""
    if existing and existing in CATEGORY_KEYWORDS:
        return existing

    text_lower = (text + " " + existing).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if cat == "general":
            continue
        if any(kw in text_lower for kw in keywords):
            return cat
    return "general"


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        # Try to break on sentence boundary
        if end < len(text):
            for sep in (". ", ".\n", "\n", " "):
                idx = text.rfind(sep, start, end)
                if idx > start + overlap:
                    end = idx + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if len(c) > 100]


def process_documents(raw_docs: list[dict]) -> list[dict]:
    """Clean, categorize, and chunk all documents."""
    chunks = []
    for doc_i, doc in enumerate(raw_docs):
        content = clean_text(doc.get("content", ""))
        if not content or len(content) < 100:
            continue

        doc_chunks = chunk_text(content)
        title = doc.get("title", "")
        source = doc.get("source", "HireNexus Knowledge Base")
        url = doc.get("url", "")
        cat = categorize(content, doc.get("category", ""))

        for chunk_i, chunk in enumerate(doc_chunks):
            chunks.append({
                "id": f"doc{doc_i}_chunk{chunk_i}",
                "content": chunk,
                "title": title,
                "source": source,
                "url": url,
                "category": cat,
            })

    return chunks


def run():
    if not RAW_PATH.exists():
        print(f"❌ raw_documents.json not found at {RAW_PATH}")
        print("Run data_collector.py first.")
        return

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw_docs = json.load(f)

    print(f"Processing {len(raw_docs)} raw documents...")
    chunks = process_documents(raw_docs)
    print(f"Generated {len(chunks)} chunks.")

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved processed chunks → {PROCESSED_PATH}")

    # Category distribution
    from collections import Counter
    cats = Counter(c["category"] for c in chunks)
    print("\nCategory distribution:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count} chunks")


if __name__ == "__main__":
    run()
