from fastapi import APIRouter

from app.api.routes.generations import router as generations_router
from app.api.routes.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(generations_router, prefix="/generations", tags=["generations"])
