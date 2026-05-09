# rag/chunker.py
# Run from backend/ directory: python rag/chunker.py
# Reads 12 role .txt files from data/raw/, splits on === and ## boundaries,
# saves all_chunks.json with full metadata per chunk.

import os
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "chunks" / "all_chunks.json"

# Maps topic codes to readable names
TOPIC_MAP = {
    "T1": "role-overview",
    "T2": "skill-roadmap",
    "T3": "tools-and-tech",
    "T4": "learning-path",
    "T5": "interview-prep",
    "T6": "career-progression",
    "T7": "salary-and-market",
    "T8": "transition-guide",
}


def extract_topic_metadata(header_block: str) -> dict:
    """
    Parses the metadata header between === markers.
    Example:
        TOPIC: T1 — Role Overview
        ROLE: Blockchain Developer
        AUDIENCE: All Levels
        TAGS: role-overview, blockchain, web3
    """
    metadata = {}

    topic_match = re.search(r"TOPIC:\s*(T\d+)", header_block)
    if topic_match:
        code = topic_match.group(1)
        metadata["topic_code"] = code
        metadata["topic"] = TOPIC_MAP.get(code, code.lower())

    role_match = re.search(r"ROLE:\s*(.+)", header_block)
    if role_match:
        raw_role = role_match.group(1).strip()
        metadata["role"] = raw_role.lower().replace(" ", "-")
        metadata["role_display"] = raw_role

    audience_match = re.search(r"AUDIENCE:\s*(.+)", header_block)
    if audience_match:
        raw_audience = audience_match.group(1).strip().lower()
        if "fresher" in raw_audience:
            metadata["audience"] = "fresher"
        elif "experienced" in raw_audience or "career switcher" in raw_audience:
            metadata["audience"] = "experienced"
        else:
            metadata["audience"] = "all"

    tags_match = re.search(r"TAGS:\s*(.+)", header_block)
    if tags_match:
        metadata["tags"] = [t.strip() for t in tags_match.group(1).split(",")]

    return metadata


from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_into_chunks(content: str, chunk_size: int = 2500, chunk_overlap: int = 300) -> list:
    """
    Uses LangChain to split text semantically into overlapping chunks.
    Maintains Markdown structure (paragraphs, headings) better than regex.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n## ", "\n\n", "\n", " ", ""]
    )
    
    docs = text_splitter.create_documents([content])
    return [doc.page_content for doc in docs]


def process_file(filepath: str) -> list:
    """
    Processes one role file.
    Returns list of chunk objects with text + metadata.
    """
    filename = Path(filepath).stem  # e.g. "12_blockchain-developer"
    role_slug = filename.split("_", 1)[-1]  # e.g. "blockchain-developer"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on lines that are purely === characters (3 or more)
    # Handles both short `===` delimiters and long `====...====` file headers
    raw_blocks = re.split(r"\n={3,}\n", content)

    all_chunks = []
    current_metadata: dict = {}

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")

        # Detect metadata header blocks: every non-empty line starts with a known key
        is_header = all(
            line.startswith("TOPIC:")
            or line.startswith("ROLE:")
            or line.startswith("AUDIENCE:")
            or line.startswith("TAGS:")
            or line.strip() == ""
            for line in lines
            if line.strip()
        ) and any(line.startswith("TOPIC:") for line in lines)

        if is_header:
            current_metadata = extract_topic_metadata(block)
            continue

        # Skip blocks before we've seen any topic header (e.g. the file-level header)
        if not current_metadata:
            continue

        # This is a content block — chunk it
        chunks = split_into_chunks(block)

        for i, chunk_text in enumerate(chunks):
            if len(chunk_text.split()) < 30:
                continue  # skip tiny fragments

            chunk_id = (
                f"{role_slug}_{current_metadata.get('topic_code', 'TX')}_chunk_{i + 1}"
            )

            # Filename slug is canonical for API target_role / Chroma filters (e.g. sde-general not sde-(general))
            chunk_obj = {
                "chunk_id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    **current_metadata,
                    "role": role_slug,
                    "source": "HireNexus Career Corpus",
                    "source_file": filename,
                    "chunk_index": i + 1,
                },
            }
            all_chunks.append(chunk_obj)

    return all_chunks


def run_chunking():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_chunks = []

    txt_files = sorted(DATA_DIR.glob("*.txt"))
    if not txt_files:
        print(f"❌ No .txt files found in {DATA_DIR}")
        return

    print(f"Found {len(txt_files)} files to process...\n")

    for filepath in txt_files:
        print(f"Processing: {filepath.name}")
        file_chunks = process_file(str(filepath))
        print(f"  → {len(file_chunks)} chunks extracted")
        all_chunks.extend(file_chunks)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done. Total chunks: {len(all_chunks)}")
    print(f"✅ Saved to: {OUTPUT_FILE}")

    # Breakdown by role
    role_counts: dict = {}
    for c in all_chunks:
        role = c["metadata"].get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    print("\n📊 Chunks per role:")
    for role, count in sorted(role_counts.items()):
        print(f"   {role}: {count} chunks")


if __name__ == "__main__":
    run_chunking()
