"""Configuration module for interview system.

This module contains all configuration constants, enums, and type definitions
used throughout the application.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Final


@unique
class LLMProvider(str, Enum):
    """Supported LLM providers for question generation."""

    GEMINI = "gemini"
    GROQ = "groq"
    LOCAL = "local"
    TEMPLATE = "template"


@unique
class QuestionDifficulty(str, Enum):
    """Question difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@unique
class QuestionCategory(str, Enum):
    """Question categories."""

    FUNDAMENTALS = "fundamentals"
    SCENARIO = "scenario"
    PROJECT = "project"
    DEBUGGING = "debugging"
    SYSTEM_DESIGN = "system_design"
    GENERAL = "general"


@unique
class EducationLevel(str, Enum):
    """Education levels."""

    PHD = "phd"
    MASTERS = "masters"
    BACHELORS = "bachelors"
    ASSOCIATES = "associates"
    HIGH_SCHOOL = "high_school"
    NONE = "none"


@unique
class SectionType(str, Enum):
    """Resume section types."""

    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    SUMMARY = "summary"


# Skills lexicon for resume parsing
SKILL_LEXICON: Final[frozenset[str]] = frozenset({
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "vue",
    "angular",
    "node",
    "fastapi",
    "django",
    "flask",
    "express",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "redis",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "machine learning",
    "ml",
    "nlp",
    "spacy",
    "tailwind",
    "three.js",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "ci/cd",
    "git",
    "linux",
    "rest",
    "api",
    "microservices",
    "system design",
    "algorithms",
    "data structures",
})

# Skill synonyms for normalization
SKILL_SYNONYMS: Final[dict[str, str]] = {
    "js": "javascript",
    "ts": "typescript",
    "ml": "machine learning",
    "threejs": "three.js",
    "k8s": "kubernetes",
    "psql": "postgresql",
    "mongo": "mongodb",
}

# Section heading mappings
SECTION_HEADINGS: Final[dict[str, frozenset[str]]] = {
    SectionType.SKILLS.value: frozenset({"skills", "technical skills", "key skills", "core competencies"}),
    SectionType.EXPERIENCE.value: frozenset({"experience", "work experience", "professional experience", "employment", "work history"}),
    SectionType.EDUCATION.value: frozenset({"education", "academic", "academics", "qualifications"}),
    SectionType.PROJECTS.value: frozenset({"projects", "personal projects", "key projects", "portfolio"}),
    SectionType.SUMMARY.value: frozenset({"summary", "profile", "about", "objective"}),
}

# NLP constants
ACTION_VERBS: Final[frozenset[str]] = frozenset({
    "built", "designed", "led", "implemented", "optimized", "improved", "delivered",
    "developed", "created", "architected", "managed", "deployed", "automated",
    "scaled", "reduced", "increased", "migrated", "refactored",
})

FILLER_WORDS: Final[frozenset[str]] = frozenset({
    "um", "uh", "like", "you", "know", "actually", "basically", "literally",
    "sort", "kind", "somewhat", "rather",
})

POSITIVE_WORDS: Final[frozenset[str]] = frozenset({
    "improved", "optimized", "increased", "delivered", "achieved", "reduced",
    "enhanced", "streamlined", "accelerated", "strengthened", "maximized",
})

NEGATIVE_WORDS: Final[frozenset[str]] = frozenset({
    "failed", "stuck", "issue", "problem", "difficult", "blocked", "struggled",
    "challenged", "hindered", "delayed",
})

RUBRIC_STOPWORDS: Final[frozenset[str]] = frozenset({
    "explain", "core", "concepts", "describe", "trade", "offs", "tradeoffs",
    "best", "practices", "reference", "real", "experience", "applying", "context",
    "discuss", "and", "of", "for", "to", "in", "the", "a", "an",
})

# Education keyword mappings
EDUCATION_KEYWORDS: Final[list[tuple[str, str]]] = [
    ("phd", EducationLevel.PHD.value),
    ("ph.d", EducationLevel.PHD.value),
    ("doctorate", EducationLevel.PHD.value),
    ("doctoral", EducationLevel.PHD.value),
    ("master", EducationLevel.MASTERS.value),
    ("masters", EducationLevel.MASTERS.value),
    ("msc", EducationLevel.MASTERS.value),
    ("m.sc", EducationLevel.MASTERS.value),
    ("mba", EducationLevel.MASTERS.value),
    ("bachelor", EducationLevel.BACHELORS.value),
    ("bachelors", EducationLevel.BACHELORS.value),
    ("b.sc", EducationLevel.BACHELORS.value),
    ("bsc", EducationLevel.BACHELORS.value),
    ("bs", EducationLevel.BACHELORS.value),
    ("b.tech", EducationLevel.BACHELORS.value),
    ("btech", EducationLevel.BACHELORS.value),
    ("b.e", EducationLevel.BACHELORS.value),
]

# Scoring constants
class ScoringWeights:
    """Weights for scoring calculations."""

    # Eligibility calculation weights
    ELIGIBILITY_SKILL: Final[float] = 0.5
    ELIGIBILITY_EXPERIENCE: Final[float] = 0.3
    ELIGIBILITY_EDUCATION: Final[float] = 0.2

    # Answer scoring weights
    ANSWER_SEMANTIC: Final[float] = 0.35
    ANSWER_COVERAGE: Final[float] = 0.40
    ANSWER_COHERENCE: Final[float] = 0.25

    # Confidence scoring weights
    CONFIDENCE_BASE: Final[float] = 0.45
    CONFIDENCE_COHERENCE: Final[float] = 0.35
    CONFIDENCE_SENTIMENT: Final[float] = 0.10
    CONFIDENCE_COVERAGE: Final[float] = 0.10


# Thresholds
class Thresholds:
    """Threshold values for scoring and evaluation."""

    MIN_ANSWER_WORDS: Final[int] = 20
    WEAK_ANSWER_SCORE: Final[float] = 35.0
    POOR_COVERAGE_THRESHOLD: Final[float] = 15.0
    POOR_SEMANTIC_THRESHOLD: Final[float] = 15.0
    LOW_COVERAGE_SCORE_CAP: Final[float] = 40.0
    STRONG_ANSWER_THRESHOLD: Final[float] = 75.0
    WEAK_ANSWER_THRESHOLD: Final[float] = 60.0
    OPTIMAL_WORD_COUNT: Final[int] = 140
    OPTIMAL_SENTENCES: Final[int] = 4
    MAX_HESITATION_PENALTY: Final[float] = 0.3
    HESITATION_PENALTY_DIVISOR: Final[float] = 80.0


# API and timeout settings
class APISettings:
    """API-related settings."""

    MAX_RETRY_ATTEMPTS: Final[int] = 3
    DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
    MAX_JSON_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10MB
    TFIDF_MAX_FEATURES: Final[int] = 4000


# Content limits
class ContentLimits:
    """Limits for content processing."""

    MAX_RESUME_KEYWORDS: Final[int] = 120
    MAX_HIGHLIGHTS: Final[int] = 10
    MAX_PROJECTS: Final[int] = 10
    MAX_SKILLS_CONTEXT: Final[int] = 20
    MAX_PROJECTS_CONTEXT: Final[int] = 5
    MAX_HIGHLIGHTS_CONTEXT: Final[int] = 5
    MAX_RESPONSIBILITIES_CONTEXT: Final[int] = 5
    MAX_JD_LENGTH: Final[int] = 1500
    MAX_ANSWER_LENGTH: Final[int] = 1200
    MAX_TRANSCRIPT_TAIL: Final[int] = 2000
    MAX_SUGGESTIONS: Final[int] = 12
    MAX_MISSING_SKILLS_SUGGESTIONS: Final[int] = 6
    MAX_STRENGTHS: Final[int] = 5
    MAX_WEAKNESSES: Final[int] = 5
    MAX_IMPROVEMENTS: Final[int] = 6
    MAX_SKILL_GAPS: Final[int] = 6


# LLM temperature settings
class LLMTemperature:
    """Temperature settings for LLM generation."""

    QUESTION_GENERATION: Final[float] = 0.2
    SINGLE_QUESTION: Final[float] = 0.45
    FOLLOWUP: Final[float] = 0.3
    REPLY: Final[float] = 0.4
    GREETING: Final[float] = 0.4
    SCORING: Final[float] = 0.2
