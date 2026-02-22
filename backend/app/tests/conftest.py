from __future__ import annotations

import os
import time

import pymysql
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

# Keep tests deterministic and local-only by default.
os.environ.setdefault("USE_SENTENCE_TRANSFORMERS", "false")
os.environ.setdefault("QGEN_PROVIDER", "template")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
os.environ.setdefault(
    "DATABASE_URL",
    "mysql+pymysql://hirenexus:hirenexus@mysql:3306/hirenexus_test",
)

from app.core.config import clear_settings_cache
from app.db.session import SessionLocal
from app.services.ml import clear_ml_caches

clear_settings_cache()
clear_ml_caches()


def _reset_test_database() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    host = url.host or "mysql"
    port = url.port or 3306
    database = url.database or "hirenexus_test"

    conn = pymysql.connect(host=host, port=port, user="root", password="root", autocommit=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
            cursor.execute(f"CREATE DATABASE `{database}`")
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def migrate_db() -> None:
    """Reset the test database and run Alembic migrations once per session."""
    cfg = Config("alembic.ini")

    last_error: Exception | None = None
    for _attempt in range(10):
        try:
            clear_settings_cache()
            _reset_test_database()
            command.upgrade(cfg, "head")
            return
        except Exception as exc:  # noqa: BLE001 - retry while services warm up
            last_error = exc
            time.sleep(2)

    if last_error:
        raise last_error


def _truncate_all_tables() -> None:
    tables = [
        "messages",
        "conversations",
        "notifications",
        "interviews",
        "applications",
        "jobs",
        "resumes",
        "users",
        "companies",
    ]
    with SessionLocal() as db:
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in tables:
            db.execute(text(f"TRUNCATE TABLE {table}"))
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.commit()


@pytest.fixture(autouse=True)
def cleanup_db() -> None:
    """Ensure each test starts from a clean database state."""
    _truncate_all_tables()
