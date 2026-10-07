import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import (
    NotFoundError,
    RequestError,
    ServiceUnavailableError,
)
from app.core.identity import get_current_admin
from app.models import (
    ContentTemplate,
    User,
)
from app.schemas.admin import (
    ContentTemplateUpdateRequest,
)
from app.schemas.response import success
from app.services.admin import add_audit
from app.services.content_templates import (
    get_template_catalog,
    template_data,
    validate_template_config,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/content-templates")
async def list_admin_content_templates(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    try:
        return success(await get_template_catalog(db))
    except RuntimeError as exc:
        raise ServiceUnavailableError("内容模板服务暂时不可用") from exc


@router.get("/content-templates/{key}")
async def get_admin_content_template(
    key: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    template = await db.get(ContentTemplate, key)
    if not template:
        raise NotFoundError("内容模板不存在")
    return success(template_data(template))


@router.put("/content-templates/{key}")
async def update_admin_content_template(
    key: str,
    payload: ContentTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    template = await db.scalar(
        select(ContentTemplate).where(ContentTemplate.key == key).with_for_update()
    )
    if not template:
        raise NotFoundError("内容模板不存在")
    try:
        config = validate_template_config(key, payload.config, enabled=payload.enabled)
    except ValueError as exc:
        raise RequestError(str(exc)) from exc
    before = template_data(template)
    template.enabled = payload.enabled
    template.config = config
    template.version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="update_content_template",
        target_type="content_template",
        target_id=template.key,
        reason=payload.reason,
        before=before,
        after=template_data(template),
    )
    await db.commit()
    await db.refresh(template)
    return success(template_data(template))
