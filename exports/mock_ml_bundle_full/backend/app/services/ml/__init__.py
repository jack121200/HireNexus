# file name is __init__.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

from .eligibility import clear_embedder_cache, compute_eligibility as _compute_eligibility, extract_required_skills as _extract_required_skills
from .models import EligibilityResult, ParsedResume, QuestionContext, QuestionItem, ScoreResult
from .question_generator import (
    generate_dynamic_question,
    generate_greeting_reply,
    generate_interview_reply,
    generate_questions,
)
from .resume_parser import clear_caches as _clear_resume_caches, parse_resume as _parse_resume
from .scoring import score_interview


logger = get_logger(__name__)


def parse_resume(*, file_path: Path, file_type: str) -> ParsedResume:
    return _parse_resume(file_path=file_path, file_type=file_type, logger=logger)


def compute_eligibility(*, resume_like: dict[str, Any], job_like: dict[str, Any]) -> EligibilityResult:
    settings = get_settings()
    embedding_model_name = settings.embedding_model_name if settings.use_sentence_transformers else ""
    return _compute_eligibility(
        resume_data=resume_like,
        job_data=job_like,
        embedding_model_name=embedding_model_name,
        logger=logger,
    )


def extract_required_skills(*, description: str, explicit_required_skills: list[str]) -> list[str]:
    return _extract_required_skills(description=description, explicit_required_skills=explicit_required_skills, logger=logger)


def clear_ml_caches() -> None:
    _clear_resume_caches()
    clear_embedder_cache()


__all__ = [
    "EligibilityResult",
    "ParsedResume",
    "QuestionContext",
    "QuestionItem",
    "ScoreResult",
    "compute_eligibility",
    "extract_required_skills",
    "generate_questions",
    "generate_dynamic_question",
    "generate_interview_reply",
    "generate_greeting_reply",
    "parse_resume",
    "score_interview",
    "clear_ml_caches",
]
