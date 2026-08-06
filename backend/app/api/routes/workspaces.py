import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.identity import get_current_user_id
from app.models import Workspace
from app.schemas.response import success
from app.schemas.workspace import CanvasUpdate, WorkspaceCreate, WorkspaceUpdate, empty_canvas

router = APIRouter()


def workspace_payload(workspace: Workspace, include_canvas: bool = False) -> dict[str, Any]:
    payload = {
        "id": str(workspace.id),
        "name": workspace.name,
        "workspace_type": workspace.workspace_type,
        "version": workspace.version,
        "thumbnail_url": workspace.thumbnail_url,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
    }
    if include_canvas:
        payload["canvas"] = workspace.canvas
    return payload


async def owned_workspace(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> Workspace | None:
    return await db.scalar(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )


@router.get("")
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    workspaces = (
        await db.scalars(
            select(Workspace)
            .where(Workspace.user_id == user_id, Workspace.deleted_at.is_(None))
            .order_by(Workspace.updated_at.desc())
        )
    ).all()
    return success([workspace_payload(item) for item in workspaces])


@router.post("")
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    workspace = Workspace(
        user_id=user_id,
        name=payload.name.strip(),
        workspace_type=payload.workspace_type,
        canvas=empty_canvas(),
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return success(workspace_payload(workspace, include_canvas=True))


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    workspace = await owned_workspace(db, workspace_id, user_id)
    if not workspace:
        raise NotFoundError("工作台不存在")
    return success(workspace_payload(workspace, include_canvas=True))


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    workspace = await owned_workspace(db, workspace_id, user_id)
    if not workspace:
        raise NotFoundError("工作台不存在")
    workspace.name = payload.name.strip()
    await db.commit()
    await db.refresh(workspace)
    return success(workspace_payload(workspace))


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    workspace = await owned_workspace(db, workspace_id, user_id)
    if not workspace:
        raise NotFoundError("工作台不存在")
    workspace.deleted_at = datetime.now(UTC)
    await db.commit()
    return success({"id": str(workspace.id)})


@router.post("/{workspace_id}/duplicate")
async def duplicate_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    source = await owned_workspace(db, workspace_id, user_id)
    if not source:
        raise NotFoundError("工作台不存在")
    workspace = Workspace(
        user_id=user_id,
        name=f"{source.name} 副本"[:100],
        workspace_type=source.workspace_type,
        canvas=source.canvas,
        thumbnail_url=source.thumbnail_url,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return success(workspace_payload(workspace, include_canvas=True))


@router.put("/{workspace_id}/canvas")
async def save_canvas(
    workspace_id: uuid.UUID,
    payload: CanvasUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    workspace = await db.scalar(
        select(Workspace)
        .where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if not workspace:
        raise NotFoundError("工作台不存在")
    if workspace.version != payload.version:
        raise ConflictError("画布已在其他页面更新，请刷新后继续")
    workspace.canvas = payload.model_dump(mode="json", exclude={"version"})
    workspace.version += 1
    await db.commit()
    await db.refresh(workspace)
    return success(workspace_payload(workspace))
