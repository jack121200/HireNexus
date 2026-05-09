"""
Full pipeline diagnostic — finds exact break point.
Run: .venv311\Scripts\python.exe diagnose.py
"""
import asyncio, os, sys
os.environ.setdefault("CHROMA_PERSIST_DIR", "./chroma_db")
os.environ.setdefault("CAREER_EMBED_MODEL", "all-MiniLM-L6-v2")
# Load .env manually
from pathlib import Path
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())
    print(f"[env] Loaded backend .env")

print("\n" + "="*60)
print("STEP 1 — ChromaDB count")
print("="*60)
try:
    from app.services.career_rag.vector_store import count
    n = count()
    print(f"  ChromaDB docs: {n}")
    assert n > 0, "ChromaDB empty!"
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("STEP 2 — Embedding model (query embed)")
print("="*60)
try:
    from app.services.career_rag.embeddings import embed_query
    vec = embed_query("How to become a backend engineer?")
    print(f"  Vector shape: {vec.shape}, first 3 dims: {vec[:3]}")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    import traceback; traceback.print_exc()

print("\n" + "="*60)
print("STEP 3 — Hybrid search")
print("="*60)
try:
    from app.services.career_rag.hybrid_search import hybrid_search
    results = hybrid_search("How to become a backend engineer?", top_k=3)
    print(f"  Results: {len(results)}")
    for r in results[:2]:
        meta = r.get("metadata", {})
        print(f"    score={r['score']:.3f} role={meta.get('role')} topic={meta.get('topic')}")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    import traceback; traceback.print_exc()

print("\n" + "="*60)
print("STEP 4 — Gemini API")
print("="*60)
async def test_gemini():
    try:
        from app.services.career_rag.llm_client import _call_gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        print(f"  GEMINI_API_KEY present: {'YES (' + gemini_key[:8] + '...)' if gemini_key else 'NO'}")
        result = await _call_gemini("Say only: Hello, HireNexus!", max_tokens=50)
        print(f"  Response: {repr(result)}")
        if result:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL: Empty response from Gemini")
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        import traceback; traceback.print_exc()

asyncio.run(test_gemini())

print("\n" + "="*60)
print("STEP 5 — Full query_career_guide() pipeline")
print("="*60)
async def test_full():
    try:
        from app.services.career_rag.query_engine import query_career_guide
        result = await query_career_guide(
            user_query="What skills should a fresher backend engineer learn first?",
            user_level="fresher",
            target_role="backend-engineer",
        )
        print(f"  intent: {result.get('intent')}")
        print(f"  confidence: {result.get('confidence')}")
        print(f"  sources count: {len(result.get('sources', []))}")
        resp = result.get("response", "")
        print(f"  response (first 200 chars): {resp[:200]}")
        if resp and resp != "I'm sorry, I couldn't generate a response right now. Please try again in a moment.":
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL: No meaningful response generated")
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        import traceback; traceback.print_exc()

asyncio.run(test_full())
