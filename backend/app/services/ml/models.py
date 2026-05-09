"""Data models for the interview system.

This module contains all dataclass definitions used throughout the application.
All models include validation, serialization, and comprehensive documentation.

Improvements over v1:
- ParsedResume: NaN/inf guard on experience years; deep-copy sections in to_dict;
  MappingProxyType wrapper to prevent silent in-place mutation of sections dict.
- EligibilityResult: out-of-range clamp now logs a warning instead of silently
  corrupting data; to_dict formula string updated to reflect cap-based scoring.
- QuestionItem: invalid difficulty/category replacement now logged as a warning.
- ScoreResult: per_question entries validated for required keys on construction.
- All models: consistent behaviour when None is passed for optional numeric fields.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .config import EducationLevel, QuestionCategory, QuestionDifficulty

_log = logging.getLogger(__name__)

# Required keys every per-question score dict must contain.
_PER_QUESTION_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"question_id", "score", "feedback"}
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert *value* to float, replacing None / NaN / ±inf with *default*."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    return f


def _clamp_pct(value: float, field_name: str) -> float:
    """Clamp *value* to [0, 100] and warn if a correction was needed."""
    if not 0.0 <= value <= 100.0:
        clamped = max(0.0, min(100.0, value))
        _log.warning(
            "percentage_out_of_range",
            extra={"field": field_name, "original": value, "clamped": clamped},
        )
        return clamped
    return value


# ---------------------------------------------------------------------------
# ParsedResume
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class ParsedResume:
    """Represents a parsed resume with extracted information.

    Attributes:
        raw_text: Normalised text content of the resume.
        skills: Identified technical skills (normalised, deduplicated).
        keywords: Extracted keywords and key phrases.
        estimated_experience_years: Estimated years of professional experience.
        education_level: Highest education level detected (EducationLevel value or None).
        sections: Mapping of section type → content. Exposed as a MappingProxyType
                  to prevent accidental in-place mutation of the frozen dataclass.
        projects: Identified project descriptions.
        highlights: Key accomplishments and highlights.
    """

    raw_text: str
    skills: tuple[str, ...]
    keywords: tuple[str, ...]
    estimated_experience_years: float
    education_level: str | None
    # field() with default_factory is required for mutable defaults in dataclasses;
    # we wrap in MappingProxyType inside __post_init__ to block external mutation.
    sections: dict[str, str] = field(default_factory=dict)
    projects: tuple[str, ...] = field(default_factory=tuple)
    highlights: tuple[str, ...] = field(default_factory=tuple)
    groq_structured: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate and sanitise resume data after initialisation."""
        # Guard against negative, NaN, or infinite experience years.
        safe_years = _safe_float(self.estimated_experience_years, default=0.0)
        if safe_years < 0.0:
            safe_years = 0.0
        if safe_years != self.estimated_experience_years:
            object.__setattr__(self, "estimated_experience_years", safe_years)

        # Wrap sections dict in a read-only proxy so callers cannot mutate it
        # even though the underlying dict is technically accessible.
        # NOTE: We store the proxy under the same attribute name.
        # This is an intentional design choice: the dataclass is frozen (no
        # reassignment of the attribute itself) AND the value is read-only.
        if not isinstance(self.sections, MappingProxyType):
            object.__setattr__(self, "sections", MappingProxyType(self.sections))

    def to_dict(self) -> dict[str, Any]:
        """Convert to a fully independent dictionary representation.

        Returns:
            Dictionary containing all resume data. ``sections`` is deep-copied
            so mutations to the returned dict cannot affect the model.
        """
        parsed_dict = {
            "raw_text": self.raw_text,
            "skills": list(self.skills),
            "keywords": list(self.keywords),
            "estimated_experience_years": self.estimated_experience_years,
            "education_level": self.education_level,
            # MappingProxyType doesn't have .copy() — convert to plain dict first.
            "sections": dict(self.sections),
            "projects": list(self.projects),
            "highlights": list(self.highlights),
        }
        
        if self.groq_structured:
            parsed_dict["groq_structured"] = dict(self.groq_structured)
            
        return parsed_dict


# ---------------------------------------------------------------------------
# EligibilityResult
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class EligibilityResult:
    """Results from eligibility computation.

    All percentage fields are clamped to [0, 100] with a logged warning if
    an out-of-range value is supplied (helps catch upstream scoring bugs).

    Attributes:
        skill_match_percentage: Percentage of required skills matched (with fuzzy).
        experience_match_percentage: Experience requirement match (smooth curve).
        education_match_percentage: Education requirement match percentage.
        eligibility_percentage: Overall eligibility — requirement-aware weighted
                                 score with strict caps (may be below the plain
                                 weighted average when caps fire).
        semantic_similarity: Semantic similarity between resume and JD (0–100).
        keyword_overlap: Jaccard keyword overlap percentage (0–100).
        missing_skills: Required skills absent from the resume.
        suggestions: Actionable, deduplicated improvement suggestions.
        required_skills: All required skills extracted/combined from the JD.
    """

    skill_match_percentage: float
    experience_match_percentage: float
    education_match_percentage: float
    eligibility_percentage: float
    semantic_similarity: float
    keyword_overlap: float
    missing_skills: tuple[str, ...]
    suggestions: tuple[str, ...]
    required_skills: tuple[str, ...]

    def __post_init__(self) -> None:
        """Clamp all percentage fields to [0, 100] with logged warnings."""
        pct_fields = (
            "skill_match_percentage",
            "experience_match_percentage",
            "education_match_percentage",
            "eligibility_percentage",
            "semantic_similarity",
            "keyword_overlap",
        )
        for fname in pct_fields:
            raw = _safe_float(getattr(self, fname), default=0.0)
            clamped = _clamp_pct(raw, fname)
            if clamped != getattr(self, fname):
                object.__setattr__(self, fname, clamped)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing all eligibility data, including a human-readable
            description of the scoring formula used.
        """
        return {
            "skill_match_percentage": round(self.skill_match_percentage, 2),
            "experience_match_percentage": round(self.experience_match_percentage, 2),
            "education_match_percentage": round(self.education_match_percentage, 2),
            "eligibility_percentage": round(self.eligibility_percentage, 2),
            "semantic_similarity": round(self.semantic_similarity, 2),
            "keyword_overlap": round(self.keyword_overlap, 2),
            "missing_skills": list(self.missing_skills),
            "suggestions": list(self.suggestions),
            "required_skills": list(self.required_skills),
            # Reflects actual behaviour: weighted base (skill 0.5 / exp 0.3 / edu 0.2)
            # then capped downward based on individual dimension weakness.
            "formula": (
                "requirement-aware weighted base (skill×0.5, experience×0.3, education×0.2) "
                "with strict downward caps per dimension and text-alignment guard"
            ),
        }


# ---------------------------------------------------------------------------
# QuestionContext
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class QuestionContext:
    """Context information for question generation.

    Attributes:
        role: Job role / title.
        years_experience: Years of experience from resume.
        resume_skills: Skills extracted from resume.
        resume_projects: Projects from resume.
        resume_highlights: Key highlights from resume.
        job_required_skills: Required skills from job description.
        job_responsibilities: Key responsibilities from job description.
        job_description: Full job description text.
    """

    role: str
    years_experience: float
    resume_skills: tuple[str, ...]
    resume_projects: tuple[str, ...]
    resume_highlights: tuple[str, ...]
    job_required_skills: tuple[str, ...]
    job_responsibilities: tuple[str, ...]
    job_description: str

    def __post_init__(self) -> None:
        """Validate and normalise context data."""
        safe_years = _safe_float(self.years_experience, default=0.0)
        if safe_years < 0.0:
            safe_years = 0.0
        if safe_years != self.years_experience:
            object.__setattr__(self, "years_experience", safe_years)

        if not self.role or not self.role.strip():
            object.__setattr__(self, "role", "Unknown Role")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "role": self.role,
            "years_experience": self.years_experience,
            "resume_skills": list(self.resume_skills),
            "resume_projects": list(self.resume_projects),
            "resume_highlights": list(self.resume_highlights),
            "job_required_skills": list(self.job_required_skills),
            "job_responsibilities": list(self.job_responsibilities),
            "job_description": self.job_description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestionContext:
        """Create QuestionContext from a plain dictionary.

        Args:
            data: Dictionary containing context data.

        Returns:
            QuestionContext instance.
        """
        return cls(
            role=str(data.get("role", "Unknown Role")),
            years_experience=_safe_float(data.get("years_experience", 0.0)),
            resume_skills=tuple(data.get("resume_skills", [])),
            resume_projects=tuple(data.get("resume_projects", [])),
            resume_highlights=tuple(data.get("resume_highlights", [])),
            job_required_skills=tuple(data.get("job_required_skills", [])),
            job_responsibilities=tuple(data.get("job_responsibilities", [])),
            job_description=str(data.get("job_description", "")),
        )


# ---------------------------------------------------------------------------
# QuestionItem
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class QuestionItem:
    """Represents a single interview question.

    Attributes:
        id: Unique identifier for the question.
        question: The question text.
        difficulty: Difficulty level (must be a valid QuestionDifficulty value).
        category: Question category (must be a valid QuestionCategory value).
        rubric_points: Evaluation criteria for scoring the answer.
    """

    id: str
    question: str
    difficulty: str
    category: str
    rubric_points: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate question data, logging warnings for corrected fields."""
        # Ensure rubric_points is never empty.
        if not self.rubric_points:
            object.__setattr__(
                self,
                "rubric_points",
                ("Clear explanation", "Practical application", "Technical accuracy"),
            )

        # Validate difficulty — log a warning so bad LLM output is traceable.
        try:
            QuestionDifficulty(self.difficulty)
        except ValueError:
            _log.warning(
                "invalid_question_difficulty",
                extra={"received": self.difficulty, "fallback": QuestionDifficulty.MEDIUM.value},
            )
            object.__setattr__(self, "difficulty", QuestionDifficulty.MEDIUM.value)

        # Validate category.
        try:
            QuestionCategory(self.category)
        except ValueError:
            _log.warning(
                "invalid_question_category",
                extra={"received": self.category, "fallback": QuestionCategory.GENERAL.value},
            )
            object.__setattr__(self, "category", QuestionCategory.GENERAL.value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "question": self.question,
            "difficulty": self.difficulty,
            "category": self.category,
            "rubric_points": list(self.rubric_points),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestionItem:
        """Create QuestionItem from a plain dictionary.

        Args:
            data: Dictionary containing question data.

        Returns:
            QuestionItem instance.
        """
        return cls(
            id=str(data.get("id", "q1")),
            question=str(data.get("question", "")),
            difficulty=str(data.get("difficulty", QuestionDifficulty.MEDIUM.value)),
            category=str(data.get("category", QuestionCategory.GENERAL.value)),
            rubric_points=tuple(data.get("rubric_points", [])),
        )


# ---------------------------------------------------------------------------
# ScoreResult
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class ScoreResult:
    """Results from interview scoring.

    Attributes:
        per_question: Detailed scoring for each question. Each dict must contain
                      at least: ``question_id`` (str), ``score`` (float 0–100),
                      ``feedback`` (str). Extra keys are permitted.
        overall_score: Overall interview score (0–100).
        confidence_score: Confidence / presentation score (0–100).
        feedback_summary: Human-readable summary feedback.
        strengths: Identified strengths.
        weaknesses: Identified weaknesses.
        improvements: Suggested improvements.
        skill_gaps: Identified skill gaps.
    """

    per_question: tuple[dict[str, Any], ...]
    overall_score: float
    confidence_score: float
    feedback_summary: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    improvements: tuple[str, ...]
    skill_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate score data, clamping and logging where needed."""
        # Clamp top-level scores.
        for fname in ("overall_score", "confidence_score"):
            raw = _safe_float(getattr(self, fname), default=0.0)
            clamped = _clamp_pct(raw, fname)
            if clamped != getattr(self, fname):
                object.__setattr__(self, fname, clamped)

        # Validate per_question structure — warn on missing keys, don't crash.
        sanitised: list[dict[str, Any]] = []
        for idx, entry in enumerate(self.per_question):
            if not isinstance(entry, dict):
                _log.warning(
                    "per_question_entry_not_a_dict",
                    extra={"index": idx, "type": type(entry).__name__},
                )
                sanitised.append(
                    {"question_id": f"q{idx+1}", "score": 0.0, "feedback": ""}
                )
                continue

            missing_keys = _PER_QUESTION_REQUIRED_KEYS - entry.keys()
            if missing_keys:
                _log.warning(
                    "per_question_entry_missing_keys",
                    extra={"index": idx, "missing": sorted(missing_keys)},
                )
                # Patch with safe defaults rather than crashing downstream.
                patched = {
                    "question_id": entry.get("question_id", f"q{idx+1}"),
                    "score": _safe_float(entry.get("score", 0.0)),
                    "feedback": entry.get("feedback", ""),
                    **{k: v for k, v in entry.items() if k not in {"question_id", "score", "feedback"}},
                }
                sanitised.append(patched)
            else:
                # Clamp the individual score too.
                patched = dict(entry)
                patched["score"] = _clamp_pct(_safe_float(entry["score"]), f"per_question[{idx}].score")
                sanitised.append(patched)

        object.__setattr__(self, "per_question", tuple(sanitised))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "per_question": list(self.per_question),
            "overall_score": round(self.overall_score, 2),
            "confidence_score": round(self.confidence_score, 2),
            "feedback_summary": self.feedback_summary,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "improvements": list(self.improvements),
            "skill_gaps": list(self.skill_gaps),
        }


# ---------------------------------------------------------------------------
# InterviewReply
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class InterviewReply:
    """Response from the interview system after a candidate answer.

    Attributes:
        reply: Interviewer's acknowledgment or bridging response.
        followup: Optional follow-up question (None when not needed).
        move_on: Whether to advance to the next question.
    """

    reply: str
    followup: str | None
    move_on: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "reply": self.reply,
            "followup": self.followup,
            "move_on": self.move_on,
        }
