"""
Intent Detector — classify user career queries into action categories.
Used to route retrieval to right ChromaDB categories.
"""
from __future__ import annotations

import re
from typing import Optional


INTENT_PATTERNS: dict[str, list[str]] = {
    "resume": [
        r"resume", r"\bcv\b", r"cover letter", r"ats", r"applicant track",
        r"curriculum vitae", r"portfolio",
    ],
    "interview": [
        r"interview", r"behavioral", r"technical interview", r"star method",
        r"hiring process", r"job offer", r"preparation",
    ],
    "salary": [
        r"salary", r"negotiat", r"compensation", r"pay raise", r"ctc",
        r"hike", r"offer letter", r"package",
    ],
    "career_path": [
        r"career change", r"switch career", r"career transition", r"pivot",
        r"roadmap", r"career path", r"new field",
    ],
    "skills": [
        r"learn", r"upskill", r"certification", r"course", r"skill", r"technology",
        r"programming", r"language",
    ],
    "job_search": [
        r"find job", r"job hunt", r"apply", r"job board", r"where to look",
        r"job search", r"placement",
    ],
    "networking": [
        r"network", r"linkedin", r"connect", r"reach out", r"referral",
    ],
}

INTENT_TO_CATEGORY: dict[str, Optional[str]] = {
    "resume": "resume",
    "interview": "interview",
    "salary": "salary",
    "career_path": "career_path",
    "skills": "skills",
    "job_search": "job_search",
    "networking": "networking",
    "general": None,
}

# Maps intent → chunk `topic` metadata (see rag/chunker.py TOPIC_MAP). None = no topic filter.
INTENT_TO_TOPIC: dict[str, Optional[str]] = {
    "resume": None,
    "interview": "interview-prep",
    "salary": "salary-and-market",
    "career_path": "career-progression",
    "skills": "skill-roadmap",
    "job_search": "learning-path",
    "networking": None,
    "general": None,
}


def detect_intent(query: str) -> str:
    """Return intent string for the given user query."""
    q = query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, q):
                return intent
    return "general"


def intent_to_category_filter(intent: str) -> Optional[str]:
    """Legacy: intent → coarse category label (fallback JSON / analytics)."""
    return INTENT_TO_CATEGORY.get(intent)


def intent_to_topic_filter(intent: str) -> Optional[str]:
    """Map intent → ChromaDB `topic` metadata (chunker TOPIC_MAP values)."""
    return INTENT_TO_TOPIC.get(intent)
