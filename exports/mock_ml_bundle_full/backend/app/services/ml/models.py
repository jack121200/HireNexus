# file name is models.py
"""Data models for the interview system.

This module contains all dataclass definitions used throughout the application.
All models include validation, serialization, and comprehensive documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import EducationLevel, QuestionCategory, QuestionDifficulty


@dataclass(slots=True, frozen=True)
class ParsedResume:
    """Represents a parsed resume with extracted information.

    Attributes:
        raw_text: Normalized text content of the resume
        skills: List of identified technical skills
        keywords: Extracted keywords and key phrases
        estimated_experience_years: Estimated years of professional experience
        education_level: Highest education level detected
        sections: Dictionary mapping section types to content
        projects: List of identified project descriptions
        highlights: Key accomplishments and highlights
    """

    raw_text: str
    skills: tuple[str, ...]
    keywords: tuple[str, ...]
    estimated_experience_years: float
    education_level: str | None
    sections: dict[str, str] = field(default_factory=dict)
    projects: tuple[str, ...] = field(default_factory=tuple)
    highlights: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate resume data after initialization."""
        if self.estimated_experience_years < 0:
            object.__setattr__(self, 'estimated_experience_years', 0.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing all resume data
        """
        return {
            "raw_text": self.raw_text,
            "skills": list(self.skills),
            "keywords": list(self.keywords),
            "estimated_experience_years": self.estimated_experience_years,
            "education_level": self.education_level,
            "sections": self.sections.copy(),
            "projects": list(self.projects),
            "highlights": list(self.highlights),
        }


@dataclass(slots=True, frozen=True)
class EligibilityResult:
    """Results from eligibility computation.

    Attributes:
        skill_match_percentage: Percentage of required skills matched
        experience_match_percentage: Experience requirement match percentage
        education_match_percentage: Education requirement match percentage
        eligibility_percentage: Overall eligibility score
        semantic_similarity: Semantic similarity between resume and job description
        keyword_overlap: Keyword overlap percentage
        missing_skills: List of required skills not found in resume
        suggestions: Actionable suggestions for improvement
        required_skills: List of all required skills
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
        """Validate percentage values are within valid ranges."""
        for field_name in [
            'skill_match_percentage', 'experience_match_percentage',
            'education_match_percentage', 'eligibility_percentage',
            'semantic_similarity', 'keyword_overlap'
        ]:
            value = getattr(self, field_name)
            if not 0 <= value <= 100:
                object.__setattr__(self, field_name, max(0.0, min(100.0, value)))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing all eligibility data
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
            "formula": "eligibility = skill*0.5 + experience*0.3 + education*0.2",
        }


@dataclass(slots=True, frozen=True)
class QuestionContext:
    """Context information for question generation.

    Attributes:
        role: Job role/title
        years_experience: Years of experience from resume
        resume_skills: Skills extracted from resume
        resume_projects: Projects from resume
        resume_highlights: Key highlights from resume
        job_required_skills: Required skills from job description
        job_responsibilities: Key responsibilities from job description
        job_description: Full job description text
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
        """Validate context data."""
        if self.years_experience < 0:
            object.__setattr__(self, 'years_experience', 0.0)
        if not self.role:
            object.__setattr__(self, 'role', 'Unknown Role')

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing all context data
        """
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
        """Create QuestionContext from dictionary.

        Args:
            data: Dictionary containing context data

        Returns:
            QuestionContext instance
        """
        return cls(
            role=str(data.get("role", "Unknown Role")),
            years_experience=float(data.get("years_experience", 0.0)),
            resume_skills=tuple(data.get("resume_skills", [])),
            resume_projects=tuple(data.get("resume_projects", [])),
            resume_highlights=tuple(data.get("resume_highlights", [])),
            job_required_skills=tuple(data.get("job_required_skills", [])),
            job_responsibilities=tuple(data.get("job_responsibilities", [])),
            job_description=str(data.get("job_description", "")),
        )


@dataclass(slots=True, frozen=True)
class QuestionItem:
    """Represents a single interview question.

    Attributes:
        id: Unique identifier for the question
        question: The question text
        difficulty: Difficulty level of the question
        category: Question category
        rubric_points: Evaluation criteria for the answer
    """

    id: str
    question: str
    difficulty: str
    category: str
    rubric_points: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate question data."""
        # Ensure rubric points is not empty
        if not self.rubric_points:
            object.__setattr__(
                self,
                'rubric_points',
                ('Clear explanation', 'Practical application', 'Technical accuracy')
            )

        # Validate difficulty
        try:
            QuestionDifficulty(self.difficulty)
        except ValueError:
            object.__setattr__(self, 'difficulty', QuestionDifficulty.MEDIUM.value)

        # Validate category
        try:
            QuestionCategory(self.category)
        except ValueError:
            object.__setattr__(self, 'category', QuestionCategory.GENERAL.value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing all question data
        """
        return {
            "id": self.id,
            "question": self.question,
            "difficulty": self.difficulty,
            "category": self.category,
            "rubric_points": list(self.rubric_points),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestionItem:
        """Create QuestionItem from dictionary.

        Args:
            data: Dictionary containing question data

        Returns:
            QuestionItem instance
        """
        return cls(
            id=str(data.get("id", "q1")),
            question=str(data.get("question", "")),
            difficulty=str(data.get("difficulty", QuestionDifficulty.MEDIUM.value)),
            category=str(data.get("category", QuestionCategory.GENERAL.value)),
            rubric_points=tuple(data.get("rubric_points", [])),
        )


@dataclass(slots=True, frozen=True)
class ScoreResult:
    """Results from interview scoring.

    Attributes:
        per_question: Detailed scoring for each question
        overall_score: Overall interview score (0-100)
        confidence_score: Confidence/presentation score (0-100)
        feedback_summary: Summary feedback text
        strengths: List of identified strengths
        weaknesses: List of identified weaknesses
        improvements: Suggested improvements
        skill_gaps: Identified skill gaps
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
        """Validate score data."""
        # Validate score ranges
        for field_name in ['overall_score', 'confidence_score']:
            value = getattr(self, field_name)
            if not 0 <= value <= 100:
                object.__setattr__(self, field_name, max(0.0, min(100.0, value)))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing all score data
        """
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


@dataclass(slots=True, frozen=True)
class InterviewReply:
    """Response from interview system after candidate answer.

    Attributes:
        reply: Interviewer's acknowledgment/response
        followup: Optional follow-up question
        move_on: Whether to move to the next question
    """

    reply: str
    followup: str | None
    move_on: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary containing reply data
        """
        return {
            "reply": self.reply,
            "followup": self.followup,
            "move_on": self.move_on,
        }
