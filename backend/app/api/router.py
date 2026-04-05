from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.patients import router as patients_router
from app.api.v1.users import router as users_router


api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/v1")
api_router.include_router(health_router, prefix="/v1")
api_router.include_router(organizations_router, prefix="/v1")
api_router.include_router(patients_router, prefix="/v1")
api_router.include_router(users_router, prefix="/v1")
