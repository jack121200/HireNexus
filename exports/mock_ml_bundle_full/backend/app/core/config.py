# file name is config.py
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from sqlalchemy.engine import make_url
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HireNexus"
    environment: str = "development"

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")

    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_alg: str = Field(default="HS256", alias="JWT_ALG")
    jwt_expires_min: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRES_MIN")

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"], alias="CORS_ORIGINS")

    upload_dir: Path = BASE_DIR / "uploads"
    upload_max_mb: int = 10
    upload_allowed_extensions: set[str] = {".pdf", ".docx", ".txt"}

    qgen_provider: str = Field(default="local", alias="QGEN_PROVIDER")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_api_base: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_API_BASE")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_api_base: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/models",
        alias="GEMINI_API_BASE",
    )
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    qgen_timeout_seconds: float = Field(default=12.0, alias="QGEN_TIMEOUT_SECONDS")
    qgen_retry_attempts: int = Field(default=1, alias="QGEN_RETRY_ATTEMPTS")
    local_llm_base_url: str = Field(default="http://localhost:11434/v1", alias="LOCAL_LLM_BASE_URL")
    local_llm_model: str = Field(default="llama3.1", alias="LOCAL_LLM_MODEL")
    local_llm_api_key: str | None = Field(default=None, alias="LOCAL_LLM_API_KEY")
    local_llm_timeout_seconds: float = Field(default=15.0, alias="LOCAL_LLM_TIMEOUT_SECONDS")

    assemblyai_api_key: str | None = Field(default=None, alias="ASSEMBLYAI_API_KEY")
    assemblyai_realtime_base: str = Field(
        default="wss://streaming.assemblyai.com/v3/ws",
        alias="ASSEMBLYAI_REALTIME_BASE",
    )
    assemblyai_sample_rate: int = Field(default=16000, alias="ASSEMBLYAI_SAMPLE_RATE")

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    polly_voice_id: str = Field(default="Kajal", alias="POLLY_VOICE_ID")
    polly_engine: str = Field(default="neural", alias="POLLY_ENGINE")
    polly_language_code: str = Field(default="en-IN", alias="POLLY_LANGUAGE_CODE")

    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_NAME",
    )
    use_sentence_transformers: bool = Field(default=True, alias="USE_SENTENCE_TRANSFORMERS")

    spacy_model: str = Field(default="en_core_web_sm", alias="SPACY_MODEL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: Any) -> list[str] | Any:
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            items = [item.strip() for item in raw.split(",")]
            return [item for item in items if item]
        return value

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        url = make_url(value)
        if not url.drivername.startswith("mysql"):
            raise ValueError("DATABASE_URL must use a MySQL driver (mysql+pymysql)")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()
