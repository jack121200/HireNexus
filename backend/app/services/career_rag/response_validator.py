"""
Response Validator — safety and quality checks on RAG-generated responses.
"""
from __future__ import annotations

import re
from typing import Any

HARMFUL_PATTERNS = [
    r"lie on.*resume",
    r"fake.*experience",
    r"plagiari",
    r"cheat",
    r"forge.*certificate",
    r"misrepresent",
]


def contains_harmful_advice(text: str) -> bool:
    """Return True if the response contains potentially harmful career advice."""
    lower = text.lower()
    return any(re.search(pat, lower) for pat in HARMFUL_PATTERNS)


def is_relevant_response(text: str, query: str) -> bool:
    """
    Basic relevance check — ensures response addresses the query topic.
    Uses keyword overlap as a simple heuristic.
    """
    stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "with",
                  "how", "what", "where", "when", "why", "should", "can", "do",
                  "does", "is", "are", "i", "my", "me", "you", "your"}
    query_words = {w for w in query.lower().split() if w not in stop_words and len(w) > 3}
    response_lower = text.lower()
    overlap = sum(1 for w in query_words if w in response_lower)
    return overlap >= max(1, len(query_words) * 0.3)


def validate_response(response_text: str, query: str, context_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Full validation pipeline. Returns:
    {
        "valid": bool,
        "warnings": list[str],
        "quality_score": float (0-1)
    }
    """
    warnings = []

    # 1. Harmful content check
    if contains_harmful_advice(response_text):
        warnings.append("Response may contain potentially harmful career advice.")

    # 2. Relevance check
    if not is_relevant_response(response_text, query):
        warnings.append("Response may not fully address the query.")

    # 3. Length check
    if len(response_text) < 50:
        warnings.append("Response is very short — may be incomplete.")

    # 4. Grounding check — is the response grounded in the context?
    context_text = " ".join(doc.get("content", "")[:400] for doc in context_docs)
    context_words = set(context_text.lower().split())
    response_words = set(response_text.lower().split())
    grounding = len(response_words & context_words) / max(len(response_words), 1)

    quality_score = round(min(1.0, grounding * 2.0 + (0.3 if not warnings else 0.0)), 3)

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "quality_score": quality_score,
        "grounding_score": round(grounding, 3),
    }
