"""Career Guide API — RAG-based career guidance chatbot (upgraded)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.career_rag.query_engine import query_career_guide

logger = get_logger(__name__)

router = APIRouter(prefix="/api/career-guide", tags=["career-guide"])


class CareerQueryRequest(BaseModel):
    query: str
    skills: list[str] | None = None
    goal: str | None = None
    level: str | None = None          # fresher, mid, senior
    current_role: str | None = None
    target_role: str | None = None
    industry: str | None = None
    chat_history: list[dict[str, str]] | None = None


class CareerQueryResponse(BaseModel):
    response: str
    sources: list[dict] = []
    query: str
    intent: str = "general"
    confidence: float = 0.0


@router.post("/ask", response_model=CareerQueryResponse)
async def ask_career_guide(req: CareerQueryRequest):
    """
    Ask the career guidance AI.
    Accepts full user profile for personalized, accurate advice.
    """
    logger.info(
        "career_guide_query",
        query=req.query[:100],
        intent_hint=req.goal,
        has_skills=bool(req.skills),
    )

    result = await query_career_guide(
        user_query=req.query,
        user_skills=req.skills,
        user_goal=req.goal,
        user_level=req.level,
        current_role=req.current_role,
        target_role=req.target_role,
        industry=req.industry,
        chat_history=req.chat_history,
    )

    return CareerQueryResponse(**result)


@router.get("/health")
def career_guide_health():
    """Check if the career guide service is ready."""
    from app.services.career_rag.vector_store import count
    doc_count = count()
    return {
        "status": "ok",
        "service": "career-guide-rag",
        "chromadb_docs": doc_count,
        "mode": "chromadb" if doc_count >= 10 else "in-memory-fallback",
    }
