"""
Analytics Logger — SQLite-based usage tracking for the Career Guide RAG.
Logs every query with metadata for quality monitoring and improvement.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parents[4] / "analytics.db"
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _create_tables(_conn)
    return _conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS career_queries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            query           TEXT NOT NULL,
            intent          TEXT,
            confidence      REAL,
            response_length INTEGER,
            sources_count   INTEGER,
            user_level      TEXT,
            current_role    TEXT,
            target_role     TEXT,
            has_skills      INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id    INTEGER REFERENCES career_queries(id),
            timestamp   TEXT NOT NULL,
            rating      INTEGER,
            feedback    TEXT
        )
    """)
    conn.commit()


def log_query(
    query: str,
    intent: str,
    confidence: float,
    response: str,
    sources_count: int,
    user_level: Optional[str] = None,
    current_role: Optional[str] = None,
    target_role: Optional[str] = None,
    has_skills: bool = False,
) -> int:
    """Log a career guide query. Returns the inserted row ID."""
    try:
        conn = _get_conn()
        cur = conn.execute(
            """
            INSERT INTO career_queries
                (timestamp, query, intent, confidence, response_length,
                 sources_count, user_level, current_role, target_role, has_skills)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                query[:500],
                intent,
                confidence,
                len(response),
                sources_count,
                user_level,
                current_role,
                target_role,
                1 if has_skills else 0,
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    except Exception:
        return 0


def log_feedback(query_id: int, rating: int, feedback: str = "") -> None:
    """Save user feedback for a query (rating 1-5)."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO feedback (query_id, timestamp, rating, feedback) VALUES (?, ?, ?, ?)",
            (query_id, datetime.utcnow().isoformat(), rating, feedback),
        )
        conn.commit()
    except Exception:
        pass


def get_stats() -> dict[str, Any]:
    """Return aggregate analytics stats."""
    try:
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) FROM career_queries").fetchone()[0]
        avg_conf = conn.execute("SELECT AVG(confidence) FROM career_queries").fetchone()[0] or 0.0
        top_intents = conn.execute(
            "SELECT intent, COUNT(*) c FROM career_queries GROUP BY intent ORDER BY c DESC LIMIT 5"
        ).fetchall()
        avg_rating = conn.execute("SELECT AVG(rating) FROM feedback").fetchone()[0] or 0.0
        return {
            "total_queries": total,
            "avg_confidence": round(avg_conf, 3),
            "top_intents": {r[0]: r[1] for r in top_intents},
            "avg_rating": round(avg_rating, 2),
        }
    except Exception:
        return {}
