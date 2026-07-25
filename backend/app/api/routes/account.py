import uuid
from datetime import UTC, datetime, time, timedelta, timezone
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import CreditLedger, GenerationTask, User, Workspace
from app.schemas.response import fail, success

router = APIRouter()
BEIJING = timezone(timedelta(hours=8))
LEDGER_TYPES = {
    "consume": "consume",
    "refund": "refund",
    "adjustment": "system",
    "recharge": "recharge",
}
TASK_TYPES = {
    "image": ("image", "图片生成"),
    "video": ("video", "视频生成"),
    "audio": ("audio", "音频生成"),
    "image_reverse": ("text", "图片反推"),
    "video_reverse": ("text", "视频反推"),
}
PROCESSING_STATUSES = {"queued", "running"}
FAILED_STATUSES = {"failed", "timeout", "cancelled"}


def _reference_count(snapshot: dict[str, Any], *keys: str) -> int:
    return sum(len(snapshot.get(key) or []) for key in keys)


def _task_specs(task: GenerationTask) -> list[dict[str, str]]:
    snapshot = task.request_snapshot or {}
    specs: list[tuple[str, Any]] = []
    if task.task_type == "image":
        metadata = snapshot.get("metadata") or {}
        specs = [
            ("比例", snapshot.get("size")),
            ("分辨率", snapshot.get("resolution") or metadata.get("resolution")),
            ("参考图片", _reference_count(snapshot, "reference_images", "image_urls")),
        ]
    elif task.task_type == "video":
        specs = [
            ("时长", f"{snapshot.get('duration')} 秒" if snapshot.get("duration") else None),
            ("分辨率", snapshot.get("resolution")),
            ("比例", snapshot.get("aspect_ratio")),
            ("生成音频", "是" if snapshot.get("generate_audio") else "否"),
            ("参考图片", _reference_count(snapshot, "reference_images", "image_with_roles")),
            ("参考视频", _reference_count(snapshot, "video_with_roles")),
            ("参考音频", _reference_count(snapshot, "audio_with_roles")),
        ]
    elif task.task_type == "audio":
        config = snapshot.get("audio_config") or {}
        references = snapshot.get("references") or []
        image_count = sum(bool(item.get("image_url")) for item in references if isinstance(item, dict))
        audio_count = sum(bool(item.get("audio_url")) for item in references if isinstance(item, dict))
        specs = [
            ("格式", config.get("format")),
            ("采样率", f"{config.get('sample_rate')} Hz" if config.get("sample_rate") else None),
            ("语速", config.get("speech_rate")),
            ("音量", config.get("loudness_rate")),
            ("音调", config.get("pitch_rate")),
            ("参考图片", image_count),
            ("参考音频", audio_count),
        ]
    elif task.task_type in {"image_reverse", "video_reverse"}:
        specs = [("来源类型", "图片" if task.task_type == "image_reverse" else "视频")]
    return [{"label": label, "value": str(value)} for label, value in specs if value is not None]


def _safe_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not result:
        return None
    if result.get("type") == "text":
        return {"type": "text", "content": str(result.get("content") or "")}
    first = next((item for item in result.get("data") or [] if isinstance(item, dict)), None)
    if not first:
        return None
    url = str(first.get("url") or "")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return {
        "type": result.get("type"),
        "url": url,
        **({"duration": first["duration"]} if first.get("duration") is not None else {}),
        **({"mime_type": first["mime_type"]} if first.get("mime_type") else {}),
    }


def _task_item(
    task: GenerationTask,
    workspace_name: str | None,
    detail: bool = False,
) -> dict[str, Any]:
    media_type, type_label = TASK_TYPES.get(task.task_type, (task.task_type, task.task_type))
    item = {
        "id": str(task.id),
        "workspace": {
            "id": str(task.workspace_id),
            "name": workspace_name or "工作台已删除",
            "available": workspace_name is not None,
        },
        "media_type": media_type,
        "type_label": type_label,
        "model": task.model,
        "status": task.status,
        "charged_credits": task.charged_credits,
        "created_at": task.created_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }
    if detail:
        item.update(
            {
                "prompt": task.prompt or "",
                "specs": _task_specs(task),
                "error_message": task.error_message if task.status in FAILED_STATUSES else None,
                "result": _safe_result(task.result),
            }
        )
    return item


@router.get("")
async def get_account(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    user = await db.get(User, user_id)
    today = datetime.combine(datetime.now(BEIJING).date(), time.min, BEIJING).astimezone(UTC)
    consumed_total, consumed_today = (
        await db.execute(
            select(
                func.coalesce(func.sum(CreditLedger.amount), 0),
                func.coalesce(
                    func.sum(CreditLedger.amount).filter(CreditLedger.created_at >= today),
                    0,
                ),
            ).where(
                CreditLedger.user_id == user_id,
                CreditLedger.entry_type == "consume",
            )
        )
    ).one()
    return success(
        {
            "user": {
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            },
            "credits": {
                "available": user.credit_balance,
                "frozen": user.credit_frozen,
                "consumed_total": int(consumed_total),
                "consumed_today": int(consumed_today),
            },
        }
    )


@router.get("/credits")
async def list_credit_ledger(
    entry_type: Literal["all", "recharge", "consume", "refund", "system"] = Query(
        "all", alias="type"
    ),
    media_type: Literal["all", "text", "image", "video", "audio"] = "all",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    conditions = [
        CreditLedger.user_id == user_id,
        CreditLedger.entry_type.in_(LEDGER_TYPES),
    ]
    if entry_type != "all":
        stored_type = "adjustment" if entry_type == "system" else entry_type
        conditions.append(CreditLedger.entry_type == stored_type)
    if media_type != "all":
        conditions.append(CreditLedger.media_type == media_type)
    if start_at:
        conditions.append(CreditLedger.created_at >= start_at)
    if end_at:
        conditions.append(CreditLedger.created_at < end_at)

    total = await db.scalar(
        select(func.count()).select_from(CreditLedger).where(*conditions)
    )
    rows = list(
        await db.scalars(
            select(CreditLedger)
            .where(*conditions)
            .order_by(CreditLedger.created_at.desc(), CreditLedger.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    items = []
    for entry in rows:
        public_type = LEDGER_TYPES[entry.entry_type]
        delta = -abs(entry.amount) if public_type == "consume" else entry.amount
        items.append(
            {
                "id": str(entry.id),
                "type": public_type,
                "delta": delta,
                "balance_after": entry.balance_after,
                "media_type": entry.media_type,
                "model": entry.model,
                "note": entry.note,
                "created_at": entry.created_at.isoformat(),
            }
        )
    return success(
        {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }
    )


@router.get("/generations")
async def list_generations(
    media_type: Literal["all", "text", "image", "video", "audio"] = "all",
    status: Literal["all", "processing", "succeeded", "failed"] = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    conditions = [GenerationTask.user_id == user_id]
    if media_type == "text":
        conditions.append(GenerationTask.task_type.in_({"image_reverse", "video_reverse"}))
    elif media_type != "all":
        conditions.append(GenerationTask.task_type == media_type)
    if status == "processing":
        conditions.append(GenerationTask.status.in_(PROCESSING_STATUSES))
    elif status == "failed":
        conditions.append(GenerationTask.status.in_(FAILED_STATUSES))
    elif status != "all":
        conditions.append(GenerationTask.status == status)

    total = await db.scalar(
        select(func.count()).select_from(GenerationTask).where(*conditions)
    )
    rows = (
        await db.execute(
            select(GenerationTask, Workspace.name)
            .outerjoin(
                Workspace,
                and_(
                    Workspace.id == GenerationTask.workspace_id,
                    Workspace.deleted_at.is_(None),
                ),
            )
            .where(*conditions)
            .order_by(GenerationTask.created_at.desc(), GenerationTask.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return success(
        {
            "items": [_task_item(task, workspace_name) for task, workspace_name in rows],
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }
    )


@router.get("/generations/{task_id}")
async def get_generation(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    row = (
        await db.execute(
            select(GenerationTask, Workspace.name)
            .outerjoin(
                Workspace,
                and_(
                    Workspace.id == GenerationTask.workspace_id,
                    Workspace.deleted_at.is_(None),
                ),
            )
            .where(GenerationTask.id == task_id, GenerationTask.user_id == user_id)
        )
    ).one_or_none()
    if not row:
        return JSONResponse(status_code=404, content=fail("任务不存在"))
    return success(_task_item(row[0], row[1], detail=True))
