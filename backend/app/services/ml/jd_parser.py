"""JD (Job Description) Structured Parser using Groq.

Parses raw job description text into structured JSON using
llama-3.1-8b-instant via the existing Groq HTTP client.
Falls back gracefully if Groq is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_GROQ_BASE = "https://api.groq.com/openai/v1"
_PARSE_MODEL = os.getenv("GROQ_MODEL_PARSING", "llama-3.1-8b-instant")

_JD_SCHEMA = """Extract job requirements from the description.
Return ONLY valid JSON — no explanation, no markdown, no code fences.

{
  "job_title": "string",
  "seniority_level": "junior | mid | senior | lead | not_specified",
  "required_skills": ["MUST-HAVE skills explicitly stated"],
  "preferred_skills": ["GOOD-TO-HAVE or nice-to-have skills"],
  "required_experience_years": 0,
  "max_experience_years": null,
  "education_required": "string or not_specified",
  "tech_stack": ["main technologies mentioned"],
  "responsibilities": ["key responsibilities (max 5)"],
  "soft_skills_required": ["communication, teamwork etc"],
  "certifications_preferred": [],
  "work_mode": "remote | hybrid | onsite | not_specified"
}"""


def _normalize_skills(raw: list) -> list[str]:
    """Lowercase-deduplicate and clean a skill list."""
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            continue
        clean = item.strip()
        key = clean.lower()
        if key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def parse_jd_with_groq(jd_text: str) -> dict:
    """
    Parse a job description with Groq llama-3.1-8b-instant.
    Returns a structured dict with required_skills, preferred_skills, etc.
    Falls back to a basic dict if Groq is unavailable.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        logger.warning("jd_parser: GROQ_API_KEY not set, returning basic JD parse")
        return _fallback_parse(jd_text)

    try:
        import httpx

        payload = {
            "model": _PARSE_MODEL,
            "temperature": 0.1,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _JD_SCHEMA},
                {"role": "user", "content": f"Parse this job description:\n\n{jd_text[:5000]}"},
            ],
        }
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                f"{_GROQ_BASE}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)

        # Normalize skill lists
        data["required_skills"] = _normalize_skills(data.get("required_skills", []))
        data["preferred_skills"] = _normalize_skills(data.get("preferred_skills", []))
        data["tech_stack"] = _normalize_skills(data.get("tech_stack", []))

        logger.info(
            "jd_parser: groq_parse_success",
            extra={
                "required_skills": len(data["required_skills"]),
                "preferred_skills": len(data["preferred_skills"]),
            },
        )
        return data

    except Exception as exc:
        logger.warning("jd_parser: groq_parse_failed, using fallback", extra={"error": str(exc)})
        return _fallback_parse(jd_text)


def _fallback_parse(jd_text: str) -> dict:
    """Basic regex-based fallback when Groq is unavailable."""
    text_lower = jd_text.lower()

    # Extract years of experience
    exp_match = re.search(r"(\d+)\+?\s+years?", text_lower)
    req_years = int(exp_match.group(1)) if exp_match else 0

    # Detect seniority
    seniority = "not_specified"
    if any(w in text_lower for w in ["senior", "lead", "principal", "staff"]):
        seniority = "senior"
    elif any(w in text_lower for w in ["junior", "fresher", "entry"]):
        seniority = "junior"
    elif any(w in text_lower for w in ["mid", "intermediate"]):
        seniority = "mid"

    # Detect work mode
    work_mode = "not_specified"
    if "remote" in text_lower:
        work_mode = "remote"
    elif "hybrid" in text_lower:
        work_mode = "hybrid"
    elif "onsite" in text_lower or "on-site" in text_lower or "in-office" in text_lower:
        work_mode = "onsite"

    return {
        "job_title": "",
        "seniority_level": seniority,
        "required_skills": [],
        "preferred_skills": [],
        "required_experience_years": req_years,
        "max_experience_years": None,
        "education_required": "not_specified",
        "tech_stack": [],
        "responsibilities": [],
        "soft_skills_required": [],
        "certifications_preferred": [],
        "work_mode": work_mode,
    }
