#!/bin/sh
set -e

echo "Running Alembic migrations..."
/app/.venv/bin/alembic upgrade head

echo "Starting Uvicorn..."
exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
