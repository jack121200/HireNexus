#!/usr/bin/env bash
set -euo pipefail

echo "[backend] Running Alembic migrations..."
alembic upgrade head

echo "[backend] Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload