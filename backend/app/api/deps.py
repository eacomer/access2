from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db as core_get_db


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency wrapper around the core DB generator."""
    yield from core_get_db()
