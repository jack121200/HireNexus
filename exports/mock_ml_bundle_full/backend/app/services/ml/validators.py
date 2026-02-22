"""Input validation utilities.

This module provides functions for validating and sanitizing inputs
throughout the application.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import APISettings
from .exceptions import ValidationError


def validate_file_path(file_path: Path, allowed_extensions: set[str] | None = None) -> Path:
    """Validate that a file path is safe and accessible.

    Args:
        file_path: Path to validate
        allowed_extensions: Optional set of allowed file extensions

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid or unsafe
    """
    if not isinstance(file_path, Path):
        raise ValidationError(
            "Invalid file path type",
            {"type": type(file_path).__name__}
        )

    # Check if file exists
    if not file_path.exists():
        raise ValidationError(
            "File does not exist",
            {"path": str(file_path)}
        )

    # Check if it's a file (not directory)
    if not file_path.is_file():
        raise ValidationError(
            "Path is not a file",
            {"path": str(file_path)}
        )

    # Check file extension if restrictions apply
    if allowed_extensions:
        if file_path.suffix.lower() not in allowed_extensions:
            raise ValidationError(
                "File extension not allowed",
                {
                    "path": str(file_path),
                    "extension": file_path.suffix,
                    "allowed": list(allowed_extensions)
                }
            )

    # Basic path traversal check
    try:
        file_path.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValidationError(
            "Invalid file path",
            {"path": str(file_path), "error": str(exc)}
        ) from exc

    return file_path


def validate_text_input(text: str, max_length: int | None = None, field_name: str = "text") -> str:
    """Validate and sanitize text input.

    Args:
        text: Text to validate
        max_length: Optional maximum length
        field_name: Name of the field for error messages

    Returns:
        Validated text

    Raises:
        ValidationError: If text is invalid
    """
    if not isinstance(text, str):
        raise ValidationError(
            f"Invalid {field_name} type",
            {"type": type(text).__name__}
        )

    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    if max_length and len(text) > max_length:
        raise ValidationError(
            f"{field_name} exceeds maximum length",
            {"length": len(text), "max_length": max_length}
        )

    return text


def validate_numeric_range(
    value: float | int,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    field_name: str = "value"
) -> float:
    """Validate that a numeric value is within acceptable range.

    Args:
        value: Value to validate
        min_value: Optional minimum value
        max_value: Optional maximum value
        field_name: Name of the field for error messages

    Returns:
        Validated value as float

    Raises:
        ValidationError: If value is out of range
    """
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"Invalid {field_name} type",
            {"value": str(value)}
        ) from exc

    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{field_name} below minimum",
            {"value": value, "min": min_value}
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{field_name} above maximum",
            {"value": value, "max": max_value}
        )

    return value


def validate_json_size(data: dict[str, Any]) -> dict[str, Any]:
    """Validate that JSON data is within size limits.

    Args:
        data: Dictionary to validate

    Returns:
        Validated dictionary

    Raises:
        ValidationError: If data exceeds size limits
    """
    import json

    try:
        json_str = json.dumps(data)
        size_bytes = len(json_str.encode('utf-8'))

        if size_bytes > APISettings.MAX_JSON_SIZE_BYTES:
            raise ValidationError(
                "JSON data exceeds size limit",
                {
                    "size_bytes": size_bytes,
                    "max_bytes": APISettings.MAX_JSON_SIZE_BYTES
                }
            )
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Invalid JSON data",
            {"error": str(exc)}
        ) from exc

    return data


def sanitize_llm_input(text: str, max_length: int = 10000) -> str:
    """Sanitize text before sending to LLM.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    # Validate and truncate
    text = validate_text_input(text, max_length=max_length, field_name="LLM input")

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove potential prompt injection patterns
    # This is a basic implementation - enhance based on specific needs
    text = re.sub(r'(?i)(ignore\s+previous|forget\s+instructions|system\s*:)', '', text)

    return text


def validate_url(url: str) -> str:
    """Validate URL format.

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    if not isinstance(url, str):
        raise ValidationError("Invalid URL type", {"type": type(url).__name__})

    # Basic URL pattern validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    if not url_pattern.match(url):
        raise ValidationError("Invalid URL format", {"url": url})

    return url


def validate_api_key(api_key: str) -> str:
    """Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        Validated API key

    Raises:
        ValidationError: If API key is invalid
    """
    if not isinstance(api_key, str):
        raise ValidationError("Invalid API key type")

    if not api_key.strip():
        raise ValidationError("API key cannot be empty")

    if len(api_key) < 10:
        raise ValidationError("API key too short")

    if len(api_key) > 500:
        raise ValidationError("API key too long")

    # Remove any whitespace
    api_key = api_key.strip()

    return api_key


def validate_list_input(
    items: list[Any],
    min_items: int | None = None,
    max_items: int | None = None,
    field_name: str = "list"
) -> list[Any]:
    """Validate list input.

    Args:
        items: List to validate
        min_items: Minimum number of items
        max_items: Maximum number of items
        field_name: Field name for error messages

    Returns:
        Validated list

    Raises:
        ValidationError: If list is invalid
    """
    if not isinstance(items, list):
        raise ValidationError(
            f"Invalid {field_name} type",
            {"type": type(items).__name__}
        )

    if min_items is not None and len(items) < min_items:
        raise ValidationError(
            f"{field_name} has too few items",
            {"count": len(items), "min": min_items}
        )

    if max_items is not None and len(items) > max_items:
        raise ValidationError(
            f"{field_name} has too many items",
            {"count": len(items), "max": max_items}
        )

    return items
