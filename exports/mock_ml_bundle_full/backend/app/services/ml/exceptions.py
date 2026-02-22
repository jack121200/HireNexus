"""Custom exceptions for the interview system.

This module defines all custom exception types used throughout the application
for proper error handling and reporting.
"""

from __future__ import annotations

from typing import Any


class InterviewSystemError(Exception):
    """Base exception for all interview system errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize exception with message and optional details.

        Args:
            message: Error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ResumeParseError(InterviewSystemError):
    """Raised when resume parsing fails."""

    pass


class FileReadError(InterviewSystemError):
    """Raised when file reading fails."""

    pass


class ValidationError(InterviewSystemError):
    """Raised when input validation fails."""

    pass


class LLMProviderError(InterviewSystemError):
    """Base exception for LLM provider errors."""

    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when LLM request times out."""

    pass


class LLMResponseError(LLMProviderError):
    """Raised when LLM response is invalid or cannot be parsed."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when LLM API authentication fails."""

    pass


class QuestionGenerationError(InterviewSystemError):
    """Raised when question generation fails."""

    pass


class ScoringError(InterviewSystemError):
    """Raised when interview scoring fails."""

    pass


class ModelLoadError(InterviewSystemError):
    """Raised when ML model loading fails."""

    pass


class ConfigurationError(InterviewSystemError):
    """Raised when configuration is invalid."""

    pass
