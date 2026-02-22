"""LLM provider clients for question generation and scoring.

This module provides secure, well-structured clients for various LLM providers
with proper error handling, retries, and authentication.
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import httpx

from .config import APISettings, LLMProvider, LLMTemperature
from .exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMResponseError,
    LLMTimeoutError,
)
from .validators import sanitize_llm_input, validate_api_key, validate_json_size, validate_url

if TYPE_CHECKING:
    from logging import Logger


class BaseLLMClient(ABC):
    """Base class for LLM provider clients."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout: int,
        logger: Logger,
    ) -> None:
        """Initialize LLM client.

        Args:
            api_key: API key for authentication (None for local/unauthenticated)
            base_url: Base URL for API
            model: Model identifier
            timeout: Request timeout in seconds
            logger: Logger instance
        """
        self.api_key = validate_api_key(api_key) if api_key else None
        self.base_url = validate_url(base_url)
        self.model = model
        self.timeout = timeout
        self.logger = logger

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: dict[str, Any],
        temperature: float = 0.2,
        seed: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate response from LLM.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt data
            temperature: Temperature for generation
            seed: Random seed for reproducibility

        Returns:
            Response dictionary or None on failure
        """
        pass

    def _retry_with_backoff(
        self,
        func: callable,
        max_retries: int = APISettings.MAX_RETRY_ATTEMPTS,
    ) -> Any:
        """Retry function with exponential backoff.

        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func()
            except httpx.TimeoutException as exc:
                last_exception = LLMTimeoutError(
                    f"Request timed out (attempt {attempt + 1}/{max_retries})",
                    {"timeout": self.timeout}
                )
                self.logger.warning(
                    "llm_request_timeout",
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    raise LLMAuthenticationError(
                        "Authentication failed - invalid API key",
                        {"status_code": 401}
                    ) from exc
                last_exception = exc
                self.logger.warning(
                    "llm_request_failed",
                    status_code=exc.response.status_code,
                    attempt=attempt + 1
                )
            except Exception as exc:
                last_exception = exc
                self.logger.warning(
                    "llm_request_error",
                    error=str(exc),
                    attempt=attempt + 1
                )

            # Exponential backoff (skip on last attempt)
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                time.sleep(backoff)

        # All retries failed
        if last_exception:
            raise LLMProviderError(
                f"All retry attempts failed: {last_exception}",
                {"attempts": max_retries}
            ) from last_exception

        return None


class GeminiClient(BaseLLMClient):
    """Google Gemini API client."""

    def _extract_json_from_response(self, response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract JSON from Gemini response.

        Args:
            response_data: Raw response from Gemini

        Returns:
            Extracted JSON or None
        """
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                return None

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            if not parts or not isinstance(parts[0], dict):
                return None

            text = parts[0].get("text", "")
            if not text:
                return None

            # Try to parse as JSON directly
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                match = re.search(r'\{.*\}', text, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(0))

            return None

        except Exception as exc:
            self.logger.warning("gemini_json_extraction_failed", error=str(exc))
            return None

    def generate(
        self,
        system_prompt: str,
        user_prompt: dict[str, Any],
        temperature: float = 0.2,
        seed: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate response from Gemini API.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt data
            temperature: Temperature for generation
            seed: Random seed (not supported by Gemini)

        Returns:
            Response dictionary or None on failure
        """
        # Sanitize inputs
        system_prompt = sanitize_llm_input(system_prompt)
        user_prompt = validate_json_size(user_prompt)

        # Build request URL - API key in query param (Gemini's required method)
        # Note: This is Gemini's official authentication method
        url = f"{self.base_url}/{self.model}:generateContent"

        # Build request payload
        combined_prompt = f"{system_prompt}\n\nInput:\n{json.dumps(user_prompt)}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": combined_prompt}],
                }
            ],
            "generationConfig": {"temperature": temperature},
        }

        def _make_request() -> dict[str, Any] | None:
            """Make HTTP request to Gemini."""
            params = {}
            if self.api_key:
                params["key"] = self.api_key

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, params=params)
                response.raise_for_status()

            return self._extract_json_from_response(response.json())

        try:
            return self._retry_with_backoff(_make_request)
        except LLMProviderError:
            raise
        except Exception as exc:
            self.logger.error("gemini_generation_failed", error=str(exc))
            return None


class GroqClient(BaseLLMClient):
    """Groq API client."""

    def _extract_json_from_response(self, response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract JSON from Groq response.

        Args:
            response_data: Raw response from Groq

        Returns:
            Extracted JSON or None
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                return None

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if not content:
                return None

            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                match = re.search(r'\{.*\}', content, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(0))

            return None

        except Exception as exc:
            self.logger.warning("groq_json_extraction_failed", error=str(exc))
            return None

    def generate(
        self,
        system_prompt: str,
        user_prompt: dict[str, Any],
        temperature: float = 0.2,
        seed: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate response from Groq API.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt data
            temperature: Temperature for generation
            seed: Random seed for reproducibility

        Returns:
            Response dictionary or None on failure
        """
        # Sanitize inputs
        system_prompt = sanitize_llm_input(system_prompt)
        user_prompt = validate_json_size(user_prompt)

        # Build request URL
        url = f"{self.base_url}/chat/completions"

        # Build request payload
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
        }

        if seed is not None:
            payload["seed"] = seed

        def _make_request() -> dict[str, Any] | None:
            """Make HTTP request to Groq."""
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

            return self._extract_json_from_response(response.json())

        try:
            return self._retry_with_backoff(_make_request)
        except LLMProviderError:
            raise
        except Exception as exc:
            self.logger.error("groq_generation_failed", error=str(exc))
            return None


class LocalLLMClient(BaseLLMClient):
    """Local LLM (OpenAI-compatible) client."""

    def _extract_json_from_response(self, response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract JSON from local LLM response.

        Args:
            response_data: Raw response from local LLM

        Returns:
            Extracted JSON or None
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                return None

            # Try message format first
            message = choices[0].get("message", {})
            content = message.get("content")

            # Fallback to text format
            if not content:
                content = choices[0].get("text")

            if not content:
                return None

            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                match = re.search(r'\{.*\}', content, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(0))

            return None

        except Exception as exc:
            self.logger.warning("local_llm_json_extraction_failed", error=str(exc))
            return None

    def generate(
        self,
        system_prompt: str,
        user_prompt: dict[str, Any],
        temperature: float = 0.2,
        seed: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate response from local LLM.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt data
            temperature: Temperature for generation
            seed: Random seed for reproducibility

        Returns:
            Response dictionary or None on failure
        """
        # Sanitize inputs
        system_prompt = sanitize_llm_input(system_prompt)
        user_prompt = validate_json_size(user_prompt)

        # Build request URL
        url = f"{self.base_url}/chat/completions"

        # Build request payload
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
            "stream": False,
        }

        if seed is not None:
            payload["seed"] = seed

        def _make_request() -> dict[str, Any] | None:
            """Make HTTP request to local LLM."""
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

            return self._extract_json_from_response(response.json())

        try:
            return self._retry_with_backoff(_make_request)
        except LLMProviderError:
            raise
        except Exception as exc:
            self.logger.error("local_llm_generation_failed", error=str(exc))
            return None


def create_llm_client(
    provider: str,
    api_key: str | None,
    base_url: str,
    model: str,
    timeout: int,
    logger: Logger,
) -> BaseLLMClient:
    """Factory function to create appropriate LLM client.

    Args:
        provider: Provider name (gemini, groq, local)
        api_key: API key (None for local)
        base_url: Base API URL
        model: Model identifier
        timeout: Request timeout
        logger: Logger instance

    Returns:
        Appropriate LLM client instance

    Raises:
        ValueError: If provider is unknown
    """
    provider_lower = provider.strip().lower()

    if provider_lower == LLMProvider.GEMINI.value:
        return GeminiClient(api_key, base_url, model, timeout, logger)
    elif provider_lower in {LLMProvider.GROQ.value, "grok"}:
        return GroqClient(api_key, base_url, model, timeout, logger)
    elif provider_lower == LLMProvider.LOCAL.value:
        return LocalLLMClient(api_key, base_url, model, timeout, logger)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
