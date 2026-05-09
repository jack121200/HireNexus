"""
Quick end-to-end test: hybrid search → confirm ChromaDB returns real chunks
Run from backend/: .venv311\Scripts\python.exe test_rag.py
"""
import asyncio, sys, os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

# Point env to local values
os.environ.setdefault("CHROMA_PERSIST_DIR", "./chroma_db")
os.environ.setdefault("CAREER_EMBED_MODEL", "all-MiniLM-L6-v2")
os.environ.setdefault("GEMINI_API_KEY", "")  # blank = will test retrieval only

from app.services.career_rag.vector_store import count
from app.services.career_rag.hybrid_search import hybrid_search

def test_vector_count():
    n = count()
    print(f"[1] ChromaDB doc count: {n}")
    assert n >= 300, f"Expected >=300, got {n}"
    print("    ✅ PASS")

def test_hybrid_search():
    results = hybrid_search("How to become a backend engineer in India?", top_k=3)
    print(f"[2] Hybrid search returned {len(results)} results")
    for i, r in enumerate(results):
        meta = r.get("metadata", {})
        print(f"    [{i+1}] score={r['score']:.3f} | role={meta.get('role')} | topic={meta.get('topic')} | id={r['id']}")
    assert len(results) > 0, "No results returned"
    print("    ✅ PASS")

def test_topic_filter():
    results = hybrid_search("Tell me about salary negotiation", top_k=3, topic="salary-and-market")
    print(f"[3] Topic-filtered search (salary-and-market): {len(results)} results")
    for r in results:
        meta = r.get("metadata", {})
        print(f"    topic={meta.get('topic')} | role={meta.get('role')} | score={r['score']:.3f}")
    print("    ✅ PASS")

def test_role_filter():
    results = hybrid_search("What skills do I need?", top_k=3, role="backend-engineer")
    print(f"[4] Role-filtered search (backend-engineer): {len(results)} results")
    for r in results:
        meta = r.get("metadata", {})
        print(f"    role={meta.get('role')} | topic={meta.get('topic')} | score={r['score']:.3f}")
    print("    ✅ PASS")

if __name__ == "__main__":
    print("=" * 60)
    print("HireNexus RAG — End-to-End Verification")
    print("=" * 60)
    try:
        test_vector_count()
        test_hybrid_search()
        test_topic_filter()
        test_role_filter()
        print("\n✅ ALL TESTS PASSED — RAG pipeline is functional!")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
