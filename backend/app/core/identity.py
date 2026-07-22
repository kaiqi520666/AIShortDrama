import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ACCESS_COOKIE, decode_token
from app.core.database import get_db
from app.models import User

LOCAL_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        claims = decode_token(token, "access")
        user_id = uuid.UUID(claims["sub"])
        auth_version = int(claims["ver"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="登录状态已失效") from exc
    user = await db.get(User, user_id)
    if not user or user.is_system:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    if user.auth_version != auth_version:
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return user


async def get_current_user_id(user: User = Depends(get_current_user)) -> uuid.UUID:
    return user.id
