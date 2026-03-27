from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import Redis

from app.api.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)
    app.state.redis = redis_client

    try:
        yield
    finally:
        redis_client.close()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.include_router(api_router)

    return app


app = create_application()