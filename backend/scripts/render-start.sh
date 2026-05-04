#!/usr/bin/env bash
set -e

echo "Running database migrations..."
python -c "from alembic.config import main; main(argv=['upgrade', 'head'])"

echo "Starting ACCESS2 backend..."
python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"