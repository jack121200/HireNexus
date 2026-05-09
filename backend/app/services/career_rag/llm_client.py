"""
Multi-LLM Client — Groq (primary, free, fast) + Gemini (fallback).
Groq uses LLaMA 3.3-70B. Gemini is fallback in case Groq is unavailable.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Groq (Primary — free, high limits, LLaMA 3.3-70B) ───────────────────────

async def _call_groq(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Optional[str]:
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not groq_key:
        logger.warning("groq_api_key_missing")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {groq_key}"},
            )
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        logger.info("llm_used", provider="groq", model="llama-3.3-70b-versatile")
        return text
    except Exception as e:
        logger.error("groq_call_failed", error=str(e))
        return None


# ── Gemini (Fallback) ─────────────────────────────────────────────────────────

async def _call_gemini(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("gemini_api_key_missing")
        return None

    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    url = f"{base_url}/{model}:generateContent?key={api_key}"

    contents = []
    if system_instruction:
        contents.append({"role": "user", "parts": [{"text": system_instruction}]})
        contents.append({"role": "model", "parts": [{"text": "Understood."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    try:
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code == 429:
                wait = (attempt + 1) * 3
                logger.warning("gemini_rate_limited", attempt=attempt + 1, wait_secs=wait)
                await asyncio.sleep(wait)
                continue

            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            logger.info("llm_used", provider="gemini", model=model)
            return parts[0].get("text", "") if parts else None

        logger.error("gemini_rate_limit_exhausted")
        return None
    except Exception as e:
        logger.error("gemini_call_failed", error=str(e))
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def generate(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """
    Generate response — tries Groq (LLaMA) first, then Gemini as fallback.
    Returns a non-empty string always.
    """
    # Try Groq first (primary — free, high rate limits)
    result = await _call_groq(prompt, system_instruction, temperature, max_tokens)
    if result and result.strip():
        return result

    # Fallback to Gemini
    logger.warning("groq_failed_trying_gemini")
    result = await _call_gemini(prompt, system_instruction, temperature, max_tokens)
    if result and result.strip():
        return result

    logger.error("all_llm_providers_failed")
    return "I'm sorry, I couldn't generate a response right now. Please check the API keys and try again."
