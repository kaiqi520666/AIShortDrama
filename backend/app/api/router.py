from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.account import router as account_router
from app.api.routes.admin import router as admin_router
from app.api.routes.credits import router as credits_router
from app.api.routes.assets import router as assets_router
from app.api.routes.generations import router as generations_router
from app.api.routes.health import router as health_router
from app.api.routes.reversals import router as reversals_router
from app.api.routes.recharge import router as recharge_router
from app.api.routes.reference_library import router as reference_library_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.workspaces import router as workspaces_router
from app.api.routes.content_templates import router as content_templates_router
from app.api.routes.admin_reference_assets import router as admin_reference_assets_router
from app.api.routes.admin_models import router as admin_models_router
from app.api.routes.admin_tasks import router as admin_tasks_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.admin_billing import router as admin_billing_router
from app.api.routes.admin_templates import router as admin_templates_router
from app.api.routes.admin_audits import router as admin_audits_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(account_router, prefix="/account", tags=["account"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(credits_router, prefix="/credits", tags=["credits"])
api_router.include_router(generations_router, prefix="/generations", tags=["generations"])
api_router.include_router(reversals_router, prefix="/reversals", tags=["reversals"])
api_router.include_router(recharge_router, prefix="/recharge", tags=["recharge"])
api_router.include_router(reference_library_router, tags=["reference-library"])
api_router.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])
api_router.include_router(content_templates_router, prefix="/content-templates", tags=["content-templates"])
api_router.include_router(admin_reference_assets_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_models_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_tasks_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_users_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_billing_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_templates_router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_audits_router, prefix="/admin", tags=["admin"])
