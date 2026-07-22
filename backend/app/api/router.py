from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.assets import router as assets_router
from app.api.routes.generations import router as generations_router
from app.api.routes.health import router as health_router
from app.api.routes.reversals import router as reversals_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(generations_router, prefix="/generations", tags=["generations"])
api_router.include_router(reversals_router, prefix="/reversals", tags=["reversals"])
api_router.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])
