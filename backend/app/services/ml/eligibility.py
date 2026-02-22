"""Eligibility computation for job matching.

This module calculates how well a resume matches job requirements
using multiple scoring methods.
"""

from __future__ import annotations

from functools import lru_cache
import os
from typing import TYPE_CHECKING, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
    SentenceTransformer = None


@lru_cache(maxsize=1)
def get_embedder(model_name: str) -> SentenceTransformer | None:
    """Get or create sentence transformer model.

    Args:
        model_name: Name of the model to load

    Returns:
        SentenceTransformer instance or None if unavailable

    Raises:
        ModelLoadError: If model loading fails critically
    """
    if not model_name:
        return None

    if os.getenv("USE_SENTENCE_TRANSFORMERS", "true").strip().lower() in {"0", "false", "no"}:
        return None

    if not SentenceTransformer:
        return None

    try:
        return SentenceTransformer(model_name)
    except Exception as exc:
        # Log warning but don't raise - we have TF-IDF fallback
        raise ModelLoadError(
            f"Failed to load embedding model: {exc}",
            {"model": model_name}
        ) from exc


def clear_embedder_cache() -> None:
    """Clear cached embedder model to free memory."""
    get_embedder.cache_clear()


def _normalize_skills(skills: list[str]) -> list[str]:
    """Normalize skill names using canonical forms.

    Args:
        skills: List of skill names

    Returns:
        Sorted list of normalized skills
    """
    normalized = set()

    for skill in skills:
        if not skill or not skill.strip():
            continue

        skill_lower = skill.strip().lower()
        canonical = SKILL_SYNONYMS.get(skill_lower, skill_lower)
        normalized.add(canonical)

    return sorted(normalized)


def _skill_match(
    resume_skills: list[str],
    required_skills: list[str]
) -> tuple[float, list[str]]:
    """Calculate skill match percentage and missing skills.

    Args:
        resume_skills: Skills from resume
        required_skills: Required skills for job

    Returns:
        Tuple of (match_percentage, missing_skills)
    """
    if not required_skills:
        return 100.0, []

    resume_set = set(_normalize_skills(resume_skills))
    required_set = set(_normalize_skills(required_skills))

    # Calculate overlap
    overlap = resume_set.intersection(required_set)
    missing = sorted(required_set - resume_set)

    # Calculate percentage
    match_pct = (len(overlap) / len(required_set)) * 100 if required_set else 100.0

    return round(match_pct, 2), missing


def _experience_match(candidate_years: float, min_years: float) -> float:
    """Calculate experience match percentage.

    Args:
        candidate_years: Candidate's years of experience
        min_years: Minimum required years

    Returns:
        Match percentage (0-100)
    """
    # Validate inputs
    candidate_years = validate_numeric_range(
        candidate_years,
        min_value=0.0,
        field_name="candidate_years"
    )

    min_years = validate_numeric_range(
        min_years,
        min_value=0.0,
        field_name="min_years"
    )

    if min_years <= 0:
        return 100.0

    # Cap at 100% even if candidate exceeds requirements
    ratio = min(candidate_years / min_years, 1.0)
    return round(ratio * 100, 2)


def _education_match(resume_level: str | None, requirement: str | None) -> float:
    """Calculate education match percentage.

    Args:
        resume_level: Education level from resume
        requirement: Required education level

    Returns:
        Match percentage (0-100)
    """
    if not requirement:
        return 100.0

    requirement_lower = requirement.lower()

    # No education detected in resume
    if not resume_level:
        return 50.0

    # Define education hierarchy
    hierarchy = {
        EducationLevel.PHD.value: 4,
        EducationLevel.MASTERS.value: 3,
        EducationLevel.BACHELORS.value: 2,
        EducationLevel.ASSOCIATES.value: 1,
        EducationLevel.HIGH_SCHOOL.value: 0,
    }

    resume_rank = hierarchy.get(resume_level, 0)

    # Determine required level and score
    if "phd" in requirement_lower or "doctorate" in requirement_lower:
        required_rank = hierarchy[EducationLevel.PHD.value]
        return 100.0 if resume_rank >= required_rank else 60.0

    if "master" in requirement_lower:
        required_rank = hierarchy[EducationLevel.MASTERS.value]
        return 100.0 if resume_rank >= required_rank else 70.0

    if any(k in requirement_lower for k in ["bachelor", "b.tech", "bs", "b.sc"]):
        required_rank = hierarchy[EducationLevel.BACHELORS.value]
        return 100.0 if resume_rank >= required_rank else 60.0

    # Default for unspecified requirements
    return 75.0


def _tfidf_similarity(resume_text: str, job_text: str, logger: Logger) -> float:
    """Calculate TF-IDF cosine similarity between texts.

    Args:
        resume_text: Resume text
        job_text: Job description text
        logger: Logger instance

    Returns:
        Similarity score (0-1)
    """
    texts = [resume_text or "", job_text or ""]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=APISettings.TFIDF_MAX_FEATURES
        )
        matrix = vectorizer.fit_transform(texts)

        # Compute cosine similarity
        similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return float(similarity)

    except Exception as exc:
        logger.warning("tfidf_similarity_failed", error=str(exc))
        return 0.0


def _semantic_similarity(
    resume_text: str,
    job_text: str,
    model_name: str,
    logger: Logger
) -> float:
    """Calculate semantic similarity using embeddings.

    Args:
        resume_text: Resume text
        job_text: Job description text
        model_name: Name of embedding model
        logger: Logger instance

    Returns:
        Similarity score as percentage (0-100)
    """
    # Validate inputs
    resume_text = validate_text_input(resume_text, field_name="resume_text")
    job_text = validate_text_input(job_text, field_name="job_text")

    # Try to use sentence transformers
    try:
        model = get_embedder(model_name)

        if model:
            embeddings = model.encode(
                [resume_text, job_text],
                normalize_embeddings=True
            )

            # Compute dot product of normalized embeddings
            similarity = float(np.dot(embeddings[0], embeddings[1]))

            # Ensure value is in [0, 1] range
            similarity = max(0.0, min(similarity, 1.0))

            return round(similarity * 100, 2)

    except ModelLoadError:
        logger.info("embedder_unavailable_using_tfidf_fallback")
    except Exception as exc:
        logger.warning("embedding_similarity_failed", error=str(exc))

    # Fallback to TF-IDF
    tfidf_sim = _tfidf_similarity(resume_text, job_text, logger)
    return round(tfidf_sim * 100, 2)


def _keyword_overlap(resume_text: str, job_text: str, logger: Logger) -> float:
    """Calculate keyword overlap percentage.

    Args:
        resume_text: Resume text
        job_text: Job description text
        logger: Logger instance

    Returns:
        Overlap score as percentage (0-100)
    """
    # Use TF-IDF as proxy for keyword overlap
    tfidf_sim = _tfidf_similarity(resume_text, job_text, logger)
    return round(tfidf_sim * 100, 2)


def _generate_suggestions(missing_skills: list[str]) -> list[str]:
    """Generate suggestions for improving resume.

    Args:
        missing_skills: List of missing skills

    Returns:
        List of actionable suggestions
    """
    suggestions: list[str] = []

    # Add skill-specific suggestions
    for skill in missing_skills[:ContentLimits.MAX_MISSING_SKILLS_SUGGESTIONS]:
        suggestions.append(f"Add a project demonstrating {skill}")
        suggestions.append(f"Quantify impact and results achieved using {skill}")
        suggestions.append(f"Include '{skill}' keyword in your experience descriptions")

    # Add general suggestions
    suggestions.append("Add metrics and measurable outcomes to recent work")
    suggestions.append("Highlight specific technologies and tools used")

    return suggestions[:ContentLimits.MAX_SUGGESTIONS]


def extract_required_skills(
    description: str,
    explicit_required_skills: list[str],
    logger: Logger
) -> list[str]:
    """Extract and combine required skills from job description.

    Args:
        description: Job description text
        explicit_required_skills: Explicitly listed required skills
        logger: Logger instance

    Returns:
        Combined list of normalized required skills
    """
    from .resume_parser import _extract_skills, _split_sections

    # Validate input
    description = validate_text_input(
        description,
        field_name="job_description"
    )

    # Extract skills from description
    sections = _split_sections(description)
    extracted = _extract_skills(description, sections, logger)

    # Combine and normalize
    combined = _normalize_skills([*explicit_required_skills, *extracted])

    return combined


def compute_eligibility(
    resume_data: dict[str, Any],
    job_data: dict[str, Any],
    embedding_model_name: str,
    logger: Logger
) -> EligibilityResult:
    """Compute eligibility score for job matching.

    Args:
        resume_data: Dictionary with resume information
        job_data: Dictionary with job requirements
        embedding_model_name: Name of embedding model to use
        logger: Logger instance

    Returns:
        EligibilityResult with detailed scoring

    Raises:
        ValidationError: If input data is invalid
    """
    from .models import EligibilityResult

    # Extract resume data
    resume_text = str(resume_data.get("raw_text", ""))
    resume_skills = list(resume_data.get("skills", []))
    resume_years = float(resume_data.get("estimated_experience_years", 0.0) or 0.0)
    resume_education = resume_data.get("education_level")

    # Extract job data
    description = str(job_data.get("description", ""))
    explicit_required_skills = list(job_data.get("required_skills", []))
    min_years = float(job_data.get("minimum_experience_years", 0.0) or 0.0)
    education_requirement = job_data.get("education_requirement")

    # Extract all required skills
    required_skills = extract_required_skills(
        description,
        explicit_required_skills,
        logger
    )

    # Calculate component scores
    skill_match_pct, missing_skills = _skill_match(resume_skills, required_skills)
    experience_match_pct = _experience_match(resume_years, min_years)
    education_match_pct = _education_match(resume_education, education_requirement)

    # Calculate overall eligibility using weighted formula
    eligibility_pct = (
        (skill_match_pct * ScoringWeights.ELIGIBILITY_SKILL) +
        (experience_match_pct * ScoringWeights.ELIGIBILITY_EXPERIENCE) +
        (education_match_pct * ScoringWeights.ELIGIBILITY_EDUCATION)
    )
    eligibility_pct = round(eligibility_pct, 2)

    # Calculate semantic similarity
    semantic_similarity = _semantic_similarity(
        resume_text,
        description,
        embedding_model_name,
        logger
    )

    # Calculate keyword overlap
    keyword_overlap = _keyword_overlap(resume_text, description, logger)

    # Generate suggestions
    suggestions = _generate_suggestions(missing_skills)

    return EligibilityResult(
        skill_match_percentage=skill_match_pct,
        experience_match_percentage=experience_match_pct,
        education_match_percentage=education_match_pct,
        eligibility_percentage=eligibility_pct,
        semantic_similarity=semantic_similarity,
        keyword_overlap=keyword_overlap,
        missing_skills=tuple(missing_skills),
        suggestions=tuple(suggestions),
        required_skills=tuple(required_skills),
    )
