"""
Career RAG Query Engine
───────────────────────
Pipeline: Intent Detection → ChromaDB Hybrid Retrieval → Prompt → LLM → Response
All retrieval is done from ChromaDB. No in-memory caching.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from app.core.logging import get_logger

from .intent_detector import detect_intent, intent_to_category_filter, intent_to_topic_filter
from .llm_client import generate

logger = get_logger(__name__)


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """\
You are an ELITE Career Architect & Senior Tech Mentor for HireNexus (a premium platform in India).
You provide DANGEROUSLY deep, hyper-specific, exhaustive, and actionable career roadmaps and advice. 

Rules:
- Give EXTREMELY DETAILED, 1500+ word responses if the user asks for a roadmap or deep guidance.
- Break everything down into micro-steps: Month 1, Month 2, what exact YouTube channels/books, which exact frameworks.
- NEVER be generic. Do not say "Learn a backend language". Say "Learn Node.js using Express, starting with the Net Ninja YouTube playlist".
- Provide actual Indian bracket salary estimates (e.g., "TCS ninja gives 3.3 LPA, but a good product startup gives 12-18 LPA, target X by doing Y").
- Use the provided context as an anchor, but if the context is thin or missing details, AGGRESSIVELY supplement it with your own vast world knowledge of tech in 2025.
- Format beautifully: Use bolding, bullet points, Markdown tables, and distinct sections.
- Speak like a hardcore, no-nonsense senior engineer who desperately wants the user to succeed and dominate the market.
"""


RAG_PROMPT_TEMPLATE = """\
CONTEXT (retrieved from internal database):
{context}

---
USER PROFILE:
{user_profile}

CONVERSATION HISTORY:
{history}

USER QUESTION:
{question}

---
INSTRUCTIONS:
- You are writing a masterclass response.
- Use the context above, but EXPAND ON IT massively using your own knowledge if needed.
- If it's a roadmap, provide month-by-month breakdown with specific courses, tools, and project ideas.
- Provide salary expectations and reality checks.
- Build the most detailed, beautiful, and "dangerous" (powerful) response possible. Stop at nothing.
- DO NOT artificially limit your response length. Go as deep as required.

ANSWER:"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_role_slug(value: Optional[str]) -> Optional[str]:
    """Convert UI role name to ChromaDB slug e.g. 'Backend Engineer' → 'backend-engineer'."""
    if not value or not str(value).strip():
        return None
    s = str(value).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-") or None


def _level_to_audience(user_level: Optional[str]) -> Optional[str]:
    """Map experience level to ChromaDB audience metadata field."""
    if not user_level:
        return None
    x = str(user_level).strip().lower()
    if x in ("fresher", "junior", "intern", "entry", "graduate", "0", "0-1"):
        return "fresher"
    if x in ("mid", "middle", "experienced", "senior", "lead", "principal", "staff"):
        return "experienced"
    return None


def _build_context(results: list[dict]) -> str:
    if not results:
        return "No relevant context found in knowledge base."
    pieces = []
    for i, res in enumerate(results, 1):
        meta = res.get("metadata", {})
        role = meta.get("role_display") or meta.get("role", "")
        topic = meta.get("topic", "")
        title = f"{role} — {topic.replace('-', ' ').title()}" if role and topic else (role or topic or "Career Guide")
        source = meta.get("source_file", "HireNexus Knowledge Base")
        score = res.get("score", 0.0)
        text = res.get("content", "")
        pieces.append(
            f"[{i}] {title} (relevance: {score:.2f})\n"
            f"Source: {source}\n"
            f"{text}\n"
            f"---"
        )
    return "\n".join(pieces)


def _build_profile(
    user_skills: Optional[list[str]],
    user_goal: Optional[str],
    user_level: Optional[str],
    current_role: Optional[str],
    target_role: Optional[str],
    industry: Optional[str],
) -> str:
    lines = []
    if user_level:
        lines.append(f"- Experience Level: {user_level}")
    if current_role:
        lines.append(f"- Current Role: {current_role}")
    if target_role:
        lines.append(f"- Target Role: {target_role}")
    if industry:
        lines.append(f"- Industry: {industry}")
    if user_goal:
        lines.append(f"- Career Goal: {user_goal}")
    if user_skills:
        lines.append(f"- Skills: {', '.join(user_skills)}")
    return "\n".join(lines) if lines else "Not provided"


def _build_history(chat_history: Optional[list[dict[str, str]]]) -> str:
    if not chat_history:
        return "None"
    recent = chat_history[-4:]
    lines = []
    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content', '')[:200]}")
    return "\n".join(lines)


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def query_career_guide(
    user_query: str,
    user_skills: Optional[list[str]] = None,
    user_goal: Optional[str] = None,
    user_level: Optional[str] = None,
    current_role: Optional[str] = None,
    target_role: Optional[str] = None,
    industry: Optional[str] = None,
    chat_history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """
    Full RAG pipeline:
    1. Detect intent → map to ChromaDB topic filter
    2. Normalize role + level → ChromaDB metadata filters
    3. Hybrid search (ChromaDB vector + BM25)
    4. Build prompt: context + profile + history + question
    5. LLM generation via Gemini
    6. Return structured response
    """
    # 1. Intent detection
    intent = detect_intent(user_query)
    topic_filter = intent_to_topic_filter(intent)
    role_slug = _normalize_role_slug(target_role)
    audience_filter = _level_to_audience(user_level)

    logger.info(
        "rag_query_start",
        intent=intent,
        topic_filter=topic_filter,
        role_slug=role_slug,
        audience=audience_filter,
        query_preview=user_query[:80],
    )

    # 2. Hybrid retrieval from ChromaDB
    results: list[dict[str, Any]] = []
    try:
        from .hybrid_search import hybrid_search
        from .vector_store import count

        db_count = count()
        if db_count == 0:
            logger.error("chromadb_empty", msg="No documents in ChromaDB — run ingestor first")
        else:
            results = hybrid_search(
                user_query,
                top_k=5,
                role=role_slug,
                audience=audience_filter,
                topic=topic_filter,
            )
            logger.info("retrieval_done", results_count=len(results), db_count=db_count)
    except Exception as e:
        logger.error("retrieval_failed", error=str(e))

    # 3. Build prompt
    context_text = _build_context(results)
    profile_text = _build_profile(user_skills, user_goal, user_level, current_role, target_role, industry)
    history_text = _build_history(chat_history)

    prompt = RAG_PROMPT_TEMPLATE.format(
        context=context_text,
        user_profile=profile_text,
        history=history_text,
        question=user_query,
    )

    # 4. LLM generation
    response_text = await generate(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # 5. Build sources list for frontend
    sources = []
    for res in results:
        meta = res.get("metadata", {})
        role_d = meta.get("role_display") or meta.get("role", "")
        topic_d = meta.get("topic", "")
        title = f"{role_d} — {topic_d.replace('-', ' ').title()}" if role_d and topic_d else (role_d or topic_d or "Career Guide")
        sources.append({
            "title": title,
            "source": meta.get("source_file", "HireNexus Knowledge Base"),
            "score": round(res.get("score", 0.0), 3),
            "role": meta.get("role", ""),
            "topic": meta.get("topic", ""),
            "text": res.get("text", "")
        })

    # 6. Compute simple confidence from top result score
    confidence = round(results[0].get("score", 0.0), 3) if results else 0.0

    return {
        "response": response_text,
        "sources": sources,
        "query": user_query,
        "intent": intent,
        "confidence": confidence,
    }
