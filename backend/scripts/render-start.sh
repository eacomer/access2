#!/usr/bin/env bash
set -e

echo "Railway runtime diagnostics..."
pwd
which python
python --version
python -m pip --version

echo "Installing backend runtime dependencies..."
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install alembic uvicorn

echo "Checking Alembic install..."
python -m pip show alembic

echo "Running database migrations..."
python -c "import os, sys; cwd=os.getcwd(); sys.path=[p for p in sys.path if p not in ('', cwd)]; from alembic.config import main; sys.path.insert(0, cwd); main(argv=['upgrade', 'head'])"

echo "Starting ACCESS2 backend..."
python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
