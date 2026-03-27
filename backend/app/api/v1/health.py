from fastapi import APIRouter, HTTPException, Request, status
from redis import Redis

from app.core.config import settings
from app.core.database import check_database_connection


router = APIRouter(prefix="/health")


@router.get("/live")
def live() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@router.get("/ready")
def ready(request: Request) -> dict[str, object]:
    db_ok = check_database_connection()

    redis_ok = False
    redis_client: Redis | None = getattr(request.app.state, "redis", None)

    if redis_client is not None:
        try:
            redis_ok = bool(redis_client.ping())
        except Exception:
            redis_ok = False

    checks = {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }

    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "service": settings.app_name,
                "checks": checks,
            },
        )

    return {
        "status": "ok",
        "service": settings.app_name,
        "checks": checks,
    }
