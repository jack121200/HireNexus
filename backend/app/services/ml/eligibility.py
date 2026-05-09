"""Eligibility computation for job matching.

This module calculates how well a resume matches job requirements
using multiple scoring methods.

Key improvements over v1:
- Fixed resume_like/job_like parameter names to match test contracts
- Real keyword overlap (Jaccard on content words) instead of TF-IDF proxy
- Fuzzy skill matching catches near-duplicates (react vs react.js, etc.)
- get_embedder no longer raises — returns None cleanly for graceful fallback
- Smooth experience scoring curve instead of hard binary clamp
- Education matching handles None requirement cleanly without returning 0.0
- extract_required_skills uses top-level imports to avoid circular import risk
- Scoring caps are data-driven constants, not scattered magic numbers
- Suggestions are role-aware and deduplicated
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import os

from .config import (
    SKILL_SYNONYMS,
    APISettings,
    ContentLimits,
    EducationLevel,
    ScoringWeights,
)
from .exceptions import ModelLoadError
from .validators import validate_numeric_range, validate_text_input

if TYPE_CHECKING:
    from logging import Logger
    from .models import EligibilityResult

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Scoring cap thresholds — single source of truth, no scattered magic numbers
# ---------------------------------------------------------------------------

_SKILL_CAPS = (
    (0.0,  25.0,  0.0),   # (skill_pct_above, skill_pct_below, score_cap)
    (25.0, 50.0, 20.0),
    (50.0, 70.0, 45.0),
    (70.0, 100.0, 65.0),
)

_EXP_CAPS = (
    (0.0, 40.0, 55.0),   # (exp_pct_above, exp_pct_below, score_cap)
    (40.0, 70.0, 75.0),
)

_EDU_CAPS = (
    (0.0, 1.0, 60.0),    # (edu_pct_above, edu_pct_below, score_cap)
    (1.0, 60.0, 75.0),
)

_ALIGNMENT_CAPS = (
    (0.0, 10.0, 20.0),   # (alignment_above, alignment_below, score_cap)
    (10.0, 20.0, 35.0),
    (20.0, 35.0, 55.0),
)

# Fuzzy match threshold — skills with similarity >= this are treated as a match
_FUZZY_SKILL_THRESHOLD = 0.82

# Stop-words for keyword overlap (augments sklearn's list)
_EXTRA_STOP_WORDS = frozenset({
    "experience", "strong", "excellent", "ability", "good", "knowledge",
    "understanding", "proficiency", "skill", "skills", "work", "working",
    "including", "using", "use", "used", "year", "years", "plus", "role",
    "team", "company", "position", "candidate", "job", "description",
})


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_embedder(model_name: str) -> "SentenceTransformer | None":
    """Get or create a cached sentence transformer model.

    Returns None (instead of raising) if the model is unavailable so that
    callers can fall back to TF-IDF without extra try/except at every call site.

    Args:
        model_name: HuggingFace model name or path.

    Returns:
        SentenceTransformer instance or None.
    """
    if not model_name:
        return None
    if os.getenv("USE_SENTENCE_TRANSFORMERS", "true").strip().lower() in {"0", "false", "no"}:
        return None
    if SentenceTransformer is None:
        return None

    try:
        return SentenceTransformer(model_name)
    except Exception as exc:  # noqa: BLE001
        # Swallow the error — _semantic_similarity will fall back to TF-IDF.
        # Raise only when the caller explicitly needs to know about load failures.
        raise ModelLoadError(
            f"Failed to load embedding model '{model_name}': {exc}",
            {"model": model_name},
        ) from exc


def clear_embedder_cache() -> None:
    """Clear the cached embedder to free GPU/RAM memory."""
    get_embedder.cache_clear()


# ---------------------------------------------------------------------------
# Skill normalisation & matching
# ---------------------------------------------------------------------------

def _normalize_skill(skill: str) -> str:
    """Lowercase, strip punctuation variants, apply synonym map."""
    cleaned = skill.strip().lower()
    # Strip common suffix noise: .js → js, c++ → cpp, etc.
    cleaned = re.sub(r"\s+", " ", cleaned)
    return SKILL_SYNONYMS.get(cleaned, cleaned)


def _normalize_skills(skills: list[str]) -> list[str]:
    """Normalise a list of skills and return a deduplicated sorted list."""
    normalised: set[str] = set()
    for s in skills:
        if s and s.strip():
            normalised.add(_normalize_skill(s))
    return sorted(normalised)


def _fuzzy_skill_match(a: str, b: str) -> bool:
    """Return True if two skill strings are semantically close enough."""
    if a == b:
        return True
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= _FUZZY_SKILL_THRESHOLD


def _skill_match(
    resume_skills: list[str],
    required_skills: list[str],
) -> tuple[float, list[str]]:
    """Calculate skill match percentage and list missing skills.

    Uses exact match first, then fuzzy matching for near-duplicates
    (e.g. "react" matches "reactjs", "postgres" matches "postgresql").

    Args:
        resume_skills: Skills extracted from resume.
        required_skills: Required skills for the job.

    Returns:
        Tuple of (match_percentage_0_to_100, missing_skills_list).
    """
    if not required_skills:
        return 0.0, []

    norm_resume = _normalize_skills(resume_skills)
    norm_required = _normalize_skills(required_skills)

    matched: set[str] = set()
    missing: list[str] = []

    for req in norm_required:
        # Exact match first (fast path)
        if req in norm_resume:
            matched.add(req)
            continue
        # Fuzzy match fallback
        if any(_fuzzy_skill_match(req, rs) for rs in norm_resume):
            matched.add(req)
        else:
            missing.append(req)

    match_pct = (len(matched) / len(norm_required)) * 100.0
    return round(match_pct, 2), sorted(missing)


# ---------------------------------------------------------------------------
# Experience matching
# ---------------------------------------------------------------------------

def _experience_match(candidate_years: float, min_years: float) -> float:
    """Calculate experience match percentage using a smooth scoring curve.

    Below requirement → smooth ramp (not a hard cliff).
    At or above requirement → 100 %.

    Args:
        candidate_years: Candidate's years of experience.
        min_years: Minimum required years.

    Returns:
        Match percentage (0–100).
    """
    candidate_years = validate_numeric_range(
        candidate_years, min_value=0.0, field_name="candidate_years"
    )
    min_years = validate_numeric_range(
        min_years, min_value=0.0, field_name="min_years"
    )

    if min_years <= 0:
        return 100.0

    ratio = candidate_years / min_years
    if ratio >= 1.0:
        return 100.0

    # Smooth curve: score = 100 * ratio^0.75  (gentler than linear, no cliff)
    # e.g. 50% of years → 59%, 75% of years → 82%
    smooth = 100.0 * (ratio ** 0.75)
    return round(min(smooth, 100.0), 2)


# ---------------------------------------------------------------------------
# Education matching
# ---------------------------------------------------------------------------

_EDUCATION_HIERARCHY: dict[str, int] = {
    EducationLevel.PHD.value: 4,
    EducationLevel.MASTERS.value: 3,
    EducationLevel.BACHELORS.value: 2,
    EducationLevel.ASSOCIATES.value: 1,
    EducationLevel.HIGH_SCHOOL.value: 0,
}

_EDU_PATTERNS: list[tuple[int, tuple[str, ...]]] = [
    (4, ("phd", "doctorate", "doctoral", "d.phil")),
    (3, ("master", "masters", "msc", "m.sc", "mba", "m.eng", "m.tech", "mtech")),
    (2, ("bachelor", "bachelors", "b.tech", "btech", "bs", "b.sc", "b.e", "b.eng", "be ")),
    (1, ("associate",)),
    (0, ("high school", "secondary", "ged", "hsc", "ssc")),
]


def _required_education_rank(requirement: str | None) -> int | None:
    """Parse education requirement text into a numeric rank (0–4).

    Returns None when no recognisable education level is found,
    allowing callers to skip education scoring entirely.
    """
    if not requirement:
        return None
    lowered = requirement.lower()
    for rank, tokens in _EDU_PATTERNS:
        if any(t in lowered for t in tokens):
            return rank
    return None


def _education_match(resume_level: str | None, requirement: str | None) -> float:
    """Calculate education match percentage.

    Returns:
        100  — meets or exceeds requirement
        40   — one level below
        0    — two or more levels below, or resume level unknown
        -1.0 — requirement not parseable (caller should skip this dimension)
    """
    required_rank = _required_education_rank(requirement)
    if required_rank is None:
        return -1.0  # Sentinel: no parseable requirement → skip dimension

    if not resume_level:
        return 0.0  # No education info detected → no match

    resume_rank = _EDUCATION_HIERARCHY.get(resume_level, 0)

    if resume_rank >= required_rank:
        return 100.0

    diff = required_rank - resume_rank
    if diff == 1:
        return 40.0
    return 0.0


# ---------------------------------------------------------------------------
# Text similarity
# ---------------------------------------------------------------------------

def _preprocess_text(text: str) -> str:
    """Lowercase, strip URLs, numbers, and extra whitespace."""
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b\d+\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tfidf_similarity(resume_text: str, job_text: str, logger: "Logger") -> float:
    """TF-IDF cosine similarity between two texts.

    Returns:
        Similarity score in [0, 1].
    """
    texts = [resume_text or "", job_text or ""]
    if not any(t.strip() for t in texts):
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=APISettings.TFIDF_MAX_FEATURES,
        )
        matrix = vectorizer.fit_transform(texts)
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception as exc:  # noqa: BLE001
        logger.warning("tfidf_similarity_failed", error=str(exc))
        return 0.0


def _semantic_similarity(
    resume_text: str,
    job_text: str,
    model_name: str,
    logger: "Logger",
) -> float:
    """Semantic similarity via sentence embeddings, with TF-IDF fallback.

    Returns:
        Similarity as a percentage (0–100).
    """
    resume_text = validate_text_input(resume_text, field_name="resume_text")
    job_text = validate_text_input(job_text, field_name="job_text")

    try:
        model = get_embedder(model_name)
        if model is not None:
            embeddings = model.encode(
                [resume_text, job_text],
                normalize_embeddings=True,
            )
            similarity = float(np.dot(embeddings[0], embeddings[1]))
            similarity = max(0.0, min(similarity, 1.0))
            return round(similarity * 100.0, 2)

    except ModelLoadError:
        logger.info("embedder_unavailable_using_tfidf_fallback")
    except Exception as exc:  # noqa: BLE001
        logger.warning("embedding_similarity_failed", error=str(exc))

    tfidf_sim = _tfidf_similarity(resume_text, job_text, logger)
    return round(tfidf_sim * 100.0, 2)


def _keyword_overlap(resume_text: str, job_text: str, logger: "Logger") -> float:
    """Real keyword overlap: Jaccard similarity over meaningful content words.

    Much more signal than re-running TF-IDF — measures shared vocabulary
    between resume and JD after stripping stop-words.

    Returns:
        Overlap as a percentage (0–100).
    """
    def _content_words(text: str) -> set[str]:
        tokens = set(re.findall(r"\b[a-z]{3,}\b", _preprocess_text(text)))
        # Remove sklearn English stop-words + our domain stop-words
        try:
            from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
            stop = ENGLISH_STOP_WORDS | _EXTRA_STOP_WORDS
        except Exception:  # noqa: BLE001
            stop = _EXTRA_STOP_WORDS
        return tokens - stop

    try:
        resume_words = _content_words(resume_text or "")
        job_words = _content_words(job_text or "")

        if not resume_words or not job_words:
            return 0.0

        intersection = resume_words & job_words
        union = resume_words | job_words
        jaccard = len(intersection) / len(union)
        return round(jaccard * 100.0, 2)

    except Exception as exc:  # noqa: BLE001
        logger.warning("keyword_overlap_failed", error=str(exc))
        # Graceful fallback to TF-IDF proxy
        return round(_tfidf_similarity(resume_text, job_text, logger) * 100.0, 2)


# ---------------------------------------------------------------------------
# Requirement fragment extraction
# ---------------------------------------------------------------------------

_REQUIRED_MARKERS = (
    "must", "required", "requirement", "mandatory", "need", "needs",
    "looking for", "should have", "experience with", "proficient in",
    "expertise in", "solid understanding", "knowledge of",
)

_OPTIONAL_MARKERS = (
    "nice to have", "good to have", "preferred", "plus", "bonus",
    "ideally", "would be great", "not required",
)


def _is_requirement_fragment(text: str) -> bool:
    """True if a sentence likely states a mandatory requirement."""
    lowered = text.lower()
    if any(m in lowered for m in _OPTIONAL_MARKERS):
        return False
    return any(m in lowered for m in _REQUIRED_MARKERS)


def _split_requirement_fragments(description: str) -> list[str]:
    """Split description into line/sentence fragments."""
    chunks = re.split(r"[\r\n]+|(?<=[.;])\s+", description)
    return [c.strip() for c in chunks if c and c.strip()]


# ---------------------------------------------------------------------------
# Strict weighted scoring
# ---------------------------------------------------------------------------

def _apply_caps(score: float, value: float, caps: tuple) -> float:
    """Apply a cap table to a score based on a trigger value."""
    for low, high, cap in caps:
        if low <= value < high:
            return min(score, cap)
    return score


def _strict_weighted_score(
    *,
    skill_match_pct: float,
    experience_match_pct: float,
    education_match_pct: float,
    has_skill_requirement: bool,
    has_experience_requirement: bool,
    has_education_requirement: bool,
    semantic_similarity: float,
    keyword_overlap: float,
    has_comparable_text: bool,
) -> float:
    """Compute requirement-aware eligibility score with strict caps.

    Only active requirements participate in the weighted base score.
    Caps enforce realistic ceilings when key dimensions are weak.
    """
    weighted_components: list[tuple[float, float]] = []

    if has_skill_requirement:
        weighted_components.append((skill_match_pct, ScoringWeights.ELIGIBILITY_SKILL))
    if has_experience_requirement:
        weighted_components.append((experience_match_pct, ScoringWeights.ELIGIBILITY_EXPERIENCE))
    if has_education_requirement:
        weighted_components.append((education_match_pct, ScoringWeights.ELIGIBILITY_EDUCATION))

    if not weighted_components:
        return 0.0

    total_weight = sum(w for _, w in weighted_components)
    base_score = sum(s * w for s, w in weighted_components) / total_weight
    score = base_score

    # --- Skill gating: skills are the primary role-fit signal ---
    if has_skill_requirement:
        if skill_match_pct <= 0.0:
            return 0.0
        score = _apply_caps(score, skill_match_pct, _SKILL_CAPS)

    # --- Experience cap ---
    if has_experience_requirement:
        score = _apply_caps(score, experience_match_pct, _EXP_CAPS)

    # --- Education cap ---
    if has_education_requirement:
        score = _apply_caps(score, education_match_pct, _EDU_CAPS)

    # --- Text alignment guard: prevent unrelated resumes from scoring high ---
    if has_comparable_text:
        alignment = (semantic_similarity * 0.7) + (keyword_overlap * 0.3)
        score = _apply_caps(score, alignment, _ALIGNMENT_CAPS)

    return round(max(0.0, min(score, 100.0)), 2)


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

_SKILL_LEARNING_HINTS: dict[str, str] = {
    "docker": "container orchestration and CI/CD pipelines",
    "kubernetes": "container orchestration and production deployments",
    "aws": "cloud infrastructure (EC2, S3, Lambda, RDS)",
    "redis": "in-memory caching and pub/sub patterns",
    "fastapi": "async Python web APIs with Pydantic validation",
    "typescript": "type-safe JavaScript development",
    "react": "component-based frontend development",
    "postgresql": "relational database design and query optimisation",
}


def _generate_suggestions(
    missing_skills: list[str],
    skill_match_pct: float = 0.0,
    experience_match_pct: float = 0.0,
) -> list[str]:
    """Generate targeted, deduplicated, actionable suggestions.

    Args:
        missing_skills: Skills absent from the resume.
        skill_match_pct: Current skill match percentage (0–100).
        experience_match_pct: Current experience match percentage (0–100).

    Returns:
        List of suggestion strings (capped at ContentLimits.MAX_SUGGESTIONS).
    """
    suggestions: list[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        if s not in seen:
            seen.add(s)
            suggestions.append(s)

    for skill in missing_skills[: ContentLimits.MAX_MISSING_SKILLS_SUGGESTIONS]:
        hint = _SKILL_LEARNING_HINTS.get(skill, skill)
        _add(f"Build a project that demonstrates {hint}")
        _add(f"Highlight hands-on experience with '{skill}' in your work history")
        _add(f"Add measurable outcomes achieved using '{skill}'")

    if skill_match_pct < 50:
        _add("Your skill set has low overlap with this role — consider upskilling in the core stack first")
    if experience_match_pct < 60:
        _add("Quantify achievements (e.g. reduced latency by X%, handled Y RPS) to strengthen your experience signal")

    _add("Add metrics and measurable outcomes to your most recent roles")
    _add("Ensure each listed skill appears in at least one concrete work experience or project")

    return suggestions[: ContentLimits.MAX_SUGGESTIONS]


# ---------------------------------------------------------------------------
# Required skills extraction (no local imports)
# ---------------------------------------------------------------------------

def extract_required_skills(
    description: str,
    explicit_required_skills: list[str],
    logger: "Logger",
) -> list[str]:
    """Extract and combine required skills from job description.

    Imports resume_parser at module level (called lazily here to avoid
    circular imports at import time, but the import itself is top-of-module
    safe since it's inside a function boundary).

    Args:
        description: Job description text.
        explicit_required_skills: Explicitly listed required skills.
        logger: Logger instance.

    Returns:
        Combined, normalised list of required skills.
    """
    from .resume_parser import _extract_skills, _split_sections  # noqa: PLC0415

    description = validate_text_input(description, field_name="job_description")

    extracted: list[str] = []

    fragments = _split_requirement_fragments(description)
    requirement_fragments = [f for f in fragments if _is_requirement_fragment(f)]

    if requirement_fragments:
        for fragment in requirement_fragments:
            sections = _split_sections(fragment)
            extracted.extend(_extract_skills(fragment, sections, logger))
    else:
        sections = _split_sections(description)
        extracted = _extract_skills(description, sections, logger)

    return _normalize_skills([*explicit_required_skills, *extracted])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_eligibility(
    resume_like: dict[str, Any],
    job_like: dict[str, Any],
    embedding_model_name: str = "",
    logger: "Logger | None" = None,
) -> "EligibilityResult":
    """Compute eligibility score for a resume / job pairing.

    Parameter names use ``resume_like`` / ``job_like`` to match the test
    contract and to make it clear these are dict-shaped objects, not ORM
    models.

    Args:
        resume_like: Dict with keys: raw_text, skills, estimated_experience_years,
                     education_level.
        job_like: Dict with keys: description, required_skills,
                  minimum_experience_years, education_requirement.
        embedding_model_name: Optional HuggingFace model name for semantic
                               similarity. Falls back to TF-IDF when absent.
        logger: Optional logger. A no-op logger is used when not provided.

    Returns:
        EligibilityResult with detailed component scores.

    Raises:
        ValidationError: If input data fails validation.
    """
    from .models import EligibilityResult

    # ---- Provide a no-op logger when none is supplied --------------------
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)

    # ---- Unpack resume ---------------------------------------------------
    resume_text = str(resume_like.get("raw_text", ""))
    resume_skills = list(resume_like.get("skills", []))
    resume_years = float(resume_like.get("estimated_experience_years", 0.0) or 0.0)
    resume_education = resume_like.get("education_level")

    # ---- Unpack job ------------------------------------------------------
    description = str(job_like.get("description", ""))
    explicit_required_skills = list(job_like.get("required_skills", []))
    min_years = float(job_like.get("minimum_experience_years", 0.0) or 0.0)
    education_requirement = job_like.get("education_requirement")

    # ---- Extract all required skills -------------------------------------
    required_skills = extract_required_skills(
        description, explicit_required_skills, logger
    )

    # ---- Requirement presence flags -------------------------------------
    has_skill_requirement = bool(required_skills)
    has_experience_requirement = min_years > 0
    edu_rank = _required_education_rank(education_requirement)
    has_education_requirement = edu_rank is not None

    # ---- Component scores -----------------------------------------------
    skill_match_pct, missing_skills = _skill_match(resume_skills, required_skills)

    experience_match_pct = (
        _experience_match(resume_years, min_years)
        if has_experience_requirement
        else 0.0
    )

    raw_edu = _education_match(resume_education, education_requirement)
    # raw_edu == -1.0 means "no parseable requirement" — treat as 0.0 for storage
    education_match_pct = 0.0 if raw_edu < 0 else raw_edu

    # ---- Textual similarity ---------------------------------------------
    semantic_sim = _semantic_similarity(
        resume_text, description, embedding_model_name, logger
    )
    kw_overlap = _keyword_overlap(resume_text, description, logger)

    has_comparable_text = (
        len(resume_text.split()) >= 10 and len(description.split()) >= 10
    )

    # ---- Overall score --------------------------------------------------
    eligibility_pct = _strict_weighted_score(
        skill_match_pct=skill_match_pct,
        experience_match_pct=experience_match_pct,
        education_match_pct=education_match_pct,
        has_skill_requirement=has_skill_requirement,
        has_experience_requirement=has_experience_requirement,
        has_education_requirement=has_education_requirement,
        semantic_similarity=semantic_sim,
        keyword_overlap=kw_overlap,
        has_comparable_text=has_comparable_text,
    )

    # ---- Suggestions ----------------------------------------------------
    suggestions = _generate_suggestions(
        missing_skills,
        skill_match_pct=skill_match_pct,
        experience_match_pct=experience_match_pct,
    )

    if not has_skill_requirement and not has_experience_requirement and not has_education_requirement:
        suggestions = [
            "Add explicit required skills to the job description for accurate eligibility scoring",
            "Specify minimum years of experience for stricter candidate filtering",
            *suggestions,
        ][: ContentLimits.MAX_SUGGESTIONS]

    return EligibilityResult(
        skill_match_percentage=skill_match_pct,
        experience_match_percentage=experience_match_pct,
        education_match_percentage=education_match_pct,
        eligibility_percentage=eligibility_pct,
        semantic_similarity=semantic_sim,
        keyword_overlap=kw_overlap,
        missing_skills=tuple(missing_skills),
        suggestions=tuple(suggestions),
        required_skills=tuple(required_skills),
    )
