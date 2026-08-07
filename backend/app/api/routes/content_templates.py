import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ServiceUnavailableError
from app.core.identity import get_current_user_id
from app.schemas.response import success
from app.services.content_templates import get_product_templates


router = APIRouter()


@router.get("/product")
async def get_product_content_templates(
    db: AsyncSession = Depends(get_db),
    _user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return success(await get_product_templates(db))
    except RuntimeError as exc:
        raise ServiceUnavailableError("商品模板服务暂时不可用") from exc
