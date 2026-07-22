import uuid
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identity import DEFAULT_WORKSPACE_ID, LOCAL_USER_ID
from app.models import Asset, GenerationTask, User, Workspace
from app.schemas.workspace import empty_canvas

REGISTRATION_LOCK_ID = 827_104_221


class RegistrationError(RuntimeError):
    pass


def user_payload(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "status": user.status,
        "created_at": user.created_at.isoformat(),
    }


async def register_user(
    db: AsyncSession,
    *,
    username: str,
    email: str,
    encoded_password: str,
) -> User:
    email = email.casefold()
    await db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": REGISTRATION_LOCK_ID})
    duplicate = await db.scalar(
        select(User.id).where((User.username == username) | (User.email == email)).limit(1)
    )
    if duplicate:
        raise RegistrationError("用户名或邮箱已注册")

    first_user = not bool(
        await db.scalar(select(User.id).where(User.is_system.is_(False)).limit(1))
    )
    user = User(
        username=username,
        email=email,
        password_hash=encoded_password,
        auth_version=0,
        is_system=False,
    )
    db.add(user)
    try:
        await db.flush()
        if first_user:
            await transfer_local_data(db, user.id)
        else:
            db.add(Workspace(user_id=user.id, name="默认工作台", canvas=empty_canvas()))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise RegistrationError("用户名或邮箱已注册") from exc
    except Exception:
        await db.rollback()
        raise
    await db.refresh(user)
    return user


async def transfer_local_data(db: AsyncSession, user_id: uuid.UUID) -> None:
    local_user = await db.get(User, LOCAL_USER_ID, with_for_update=True)
    if local_user:
        await db.execute(
            update(Workspace).where(Workspace.user_id == LOCAL_USER_ID).values(user_id=user_id)
        )
        await db.execute(
            update(GenerationTask)
            .where(GenerationTask.user_id == LOCAL_USER_ID)
            .values(user_id=user_id)
        )
        await db.execute(
            update(Asset).where(Asset.user_id == LOCAL_USER_ID).values(user_id=user_id)
        )
        local_user.status = "disabled"
        local_user.auth_version += 1

    active_workspace = await db.scalar(
        select(Workspace.id)
        .where(Workspace.user_id == user_id, Workspace.deleted_at.is_(None))
        .limit(1)
    )
    if not active_workspace:
        workspace_id = DEFAULT_WORKSPACE_ID if not local_user else uuid.uuid4()
        db.add(
            Workspace(
                id=workspace_id,
                user_id=user_id,
                name="默认工作台",
                canvas=empty_canvas(),
            )
        )
