#!/usr/bin/env bash
set -e

echo "Running database migrations..."
python -c "import os, sys; cwd=os.getcwd(); sys.path=[p for p in sys.path if p not in ('', cwd)]; from alembic.config import main; sys.path.insert(0, cwd); main(argv=['upgrade', 'head'])"

echo "Starting ACCESS2 backend..."
python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
