import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.database import get_db
from app.core.errors import (
    NotFoundError,
    RequestError,
    ServiceUnavailableError,
)
from app.core.identity import get_current_admin
from app.core.model_capabilities import get_model_capability
from app.models import (
    AdminAuditLog,
    CreditLedger,
    ContentTemplate,
    GenerationTask,
    ModelAdminSetting,
    ModelPriceRule,
    RechargeOrder,
    RechargeTier,
    User,
)
from app.providers.toapis import ToApisProvider
from app.schemas.admin import (
    AdminResetPasswordRequest,
    BillingPolicyUpdateRequest,
    ContentTemplateUpdateRequest,
    CreditAdjustmentRequest,
    CreditPolicyUpdateRequest,
    ModelAdminSettingUpdateRequest,
    PriceRuleUpdateRequest,
    RechargeTierMutationRequest,
    UserRoleRequest,
    UserStatusRequest,
)
from app.schemas.response import success
from app.services.admin import active_admin_count, add_audit, adjust_credits, price_snapshot, user_snapshot
from app.services.admin_configuration import (
    credit_policy_data,
    get_billing_policy,
    get_credit_policy,
    get_model_settings,
    model_settings_payload,
    policy_data,
)
from app.services.content_templates import (
    get_template_catalog,
    template_data,
    validate_template_config,
)
from app.services.recharge import RechargeError, admin_order_data, order_data, sync_cahaya_order, tier_data, validate_tiers

router = APIRouter()
logger = logging.getLogger(__name__)


def page_data(page: int, page_size: int, total: int, items: list[dict]) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def user_data(user: User) -> dict:
    return {"id": str(user.id), **user_snapshot(user), "created_at": user.created_at.isoformat()}


def rule_data(rule: ModelPriceRule) -> dict:
    return {"id": str(rule.id), **price_snapshot(rule), "created_at": rule.created_at.isoformat(), "updated_at": rule.updated_at.isoformat()}


def task_summary_data(task: GenerationTask, user: User) -> dict:
    return {
        "id": str(task.id),
        "user": {"id": str(user.id), "username": user.username, "email": user.email},
        "task_type": task.task_type,
        "provider": task.provider,
        "model": task.model,
        "status": task.status,
        "progress": task.progress,
        "provider_task_id": task.provider_task_id,
        "frozen_credits": task.frozen_credits,
        "charged_credits": task.charged_credits,
        "credit_status": task.credit_status,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def task_detail_data(task: GenerationTask, user: User) -> dict:
    return {
        **task_summary_data(task, user),
        "workspace_id": str(task.workspace_id),
        "node_id": task.node_id,
        "diagnostic_snapshot": task.diagnostic_snapshot,
        "request_snapshot": task.request_snapshot,
        "pricing_snapshot": task.pricing_snapshot,
        "result": task.result,
        "retry_count": task.retry_count,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "updated_at": task.updated_at.isoformat(),
    }


@router.get("/dashboard")
async def get_admin_dashboard(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    if days not in {1, 7, 30}:
        raise RequestError("统计周期仅支持 1、7 或 30 天")
    start_at = datetime.now(UTC) - timedelta(days=days)
    recharge_amount = int(
        await db.scalar(
            select(func.coalesce(func.sum(RechargeOrder.amount_cents), 0)).where(
                RechargeOrder.status == "paid", RechargeOrder.created_at >= start_at
            )
        )
        or 0
    )
    recharge_orders = int(
        await db.scalar(
            select(func.count()).select_from(RechargeOrder).where(
                RechargeOrder.status == "paid", RechargeOrder.created_at >= start_at
            )
        )
        or 0
    )
    consumed_credits = int(
        await db.scalar(
            select(func.coalesce(func.sum(CreditLedger.amount), 0)).where(
                CreditLedger.entry_type == "consume", CreditLedger.created_at >= start_at
            )
        )
        or 0
    )
    status_rows = (await db.execute(
        select(GenerationTask.status, func.count())
        .where(GenerationTask.created_at >= start_at)
        .group_by(GenerationTask.status)
    )).all()
    status_counts = {status: int(count) for status, count in status_rows}
    model_rows = (await db.execute(
        select(GenerationTask.model, func.count())
        .where(GenerationTask.created_at >= start_at)
        .group_by(GenerationTask.model)
        .order_by(func.count().desc(), GenerationTask.model)
    )).all()
    terminal = sum(status_counts.get(status, 0) for status in ("succeeded", "failed", "timeout", "cancelled"))
    succeeded = status_counts.get("succeeded", 0)
    queued_tasks = int(
        await db.scalar(
            select(func.count()).select_from(GenerationTask).where(
                GenerationTask.status == "queued"
            )
        )
        or 0
    )
    queue_depth = None
    try:
        from app.core.config import get_settings

        queue_depth = int(await request.app.state.redis.zcard(get_settings().redis_queue_name))
    except Exception:
        queue_depth = None
    return success(
        {
            "days": days,
            "recharge_amount_cents": recharge_amount,
            "recharge_order_count": recharge_orders,
            "consumed_credits": consumed_credits,
            "task_count": sum(status_counts.values()),
            "succeeded_count": succeeded,
            "failed_count": status_counts.get("failed", 0),
            "timeout_count": status_counts.get("timeout", 0),
            "success_rate": round(succeeded / terminal, 4) if terminal else None,
            "queued_task_count": queued_tasks,
            "queue_depth": queue_depth,
            "model_calls": [
                {"model": model, "count": int(count)} for model, count in model_rows
            ],
        }
    )


@router.get("/users")
async def list_users(
    q: str = "",
    status: str = Query("all", pattern="^(all|active|disabled)$"),
    role: str = Query("all", pattern="^(all|user|admin)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = [User.is_system.is_(False)]
    if q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(User.username.ilike(term), User.email.ilike(term)))
    if status != "all":
        filters.append(User.status == status)
    if role != "all":
        filters.append(User.role == role)
    total = int(await db.scalar(select(func.count()).select_from(User).where(*filters)) or 0)
    users = list(await db.scalars(select(User).where(*filters).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return success(page_data(page, page_size, total, [user_data(user) for user in users]))


async def target_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(select(User).where(User.id == user_id, User.is_system.is_(False)).with_for_update())
    if not user:
        raise NotFoundError("用户不存在")
    return user


@router.post("/users/{user_id}/credits")
async def update_user_credits(
    user_id: uuid.UUID,
    payload: CreditAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        user = await adjust_credits(db, admin=admin, user_id=user_id, amount=payload.amount, reason=payload.reason)
    except ValueError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    return success(user_data(user))


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await target_user(db, user_id)
    if user.id == admin.id and payload.role != "admin":
        raise RequestError("不能降低自己的管理员角色")
    if user.role == "admin" and payload.role != "admin" and user.status == "active" and await active_admin_count(db) <= 1:
        raise RequestError("至少需要保留一名启用的管理员")
    before = user_snapshot(user)
    if user.role != payload.role:
        user.role = payload.role
        user.auth_version += 1
    add_audit(db, admin_id=admin.id, action="change_role", target_type="user", target_id=user.id, reason=payload.reason, before=before, after=user_snapshot(user))
    await db.commit()
    await db.refresh(user)
    return success(user_data(user))


@router.post("/users/{user_id}/status")
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await target_user(db, user_id)
    if user.id == admin.id and payload.status != "active":
        raise RequestError("不能停用自己的账号")
    if user.role == "admin" and user.status == "active" and payload.status != "active" and await active_admin_count(db) <= 1:
        raise RequestError("至少需要保留一名启用的管理员")
    before = user_snapshot(user)
    if user.status != payload.status:
        user.status = payload.status
        user.auth_version += 1
    add_audit(db, admin_id=admin.id, action="change_status", target_type="user", target_id=user.id, reason=payload.reason, before=before, after=user_snapshot(user))
    await db.commit()
    await db.refresh(user)
    return success(user_data(user))


@router.post("/users/{user_id}/password")
async def reset_user_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await target_user(db, user_id)
    before = user_snapshot(user)
    user.password_hash = await asyncio.to_thread(hash_password, payload.new_password)
    user.auth_version += 1
    add_audit(db, admin_id=admin.id, action="reset_password", target_type="user", target_id=user.id, reason=payload.reason, before=before, after=user_snapshot(user))
    await db.commit()
    return success(user_data(user))


@router.get("/pricing")
async def list_price_rules(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rules = list(await db.scalars(select(ModelPriceRule).order_by(ModelPriceRule.media_type, ModelPriceRule.model, ModelPriceRule.specification)))
    return success([rule_data(rule) for rule in rules])


@router.put("/pricing/{rule_id}")
async def update_price_rule(
    rule_id: uuid.UUID,
    payload: PriceRuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rule = await db.scalar(select(ModelPriceRule).where(ModelPriceRule.id == rule_id).with_for_update())
    if not rule:
        raise NotFoundError("计费规则不存在")
    before = price_snapshot(rule)
    for field, value in payload.model_dump(exclude={"reason"}).items():
        setattr(rule, field, value)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise RequestError("模型、类型和规格组合已存在") from exc
    add_audit(db, admin_id=admin.id, action="update_pricing", target_type="price_rule", target_id=rule.id, reason=payload.reason, before=before, after=price_snapshot(rule))
    await db.commit()
    await db.refresh(rule)
    return success(rule_data(rule))


@router.get("/billing-policy")
async def get_billing_policy_data(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return success(policy_data(await get_billing_policy(db)))


@router.put("/billing-policy")
async def update_billing_policy(
    payload: BillingPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    policy = await get_billing_policy(db, lock=True)
    tiers = list(await db.scalars(select(RechargeTier).with_for_update()))
    before = policy_data(policy)
    for field, value in payload.model_dump(exclude={"reason"}, exclude_none=True).items():
        setattr(policy, field, value)
    try:
        validate_tiers(tiers, policy)
    except RechargeError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    policy.version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="update_billing_policy",
        target_type="billing_policy",
        target_id=policy.key,
        reason=payload.reason,
        before=before,
        after=policy_data(policy),
    )
    await db.commit()
    await db.refresh(policy)
    return success(policy_data(policy))


@router.get("/credit-policy")
async def get_credit_policy_data(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return success(credit_policy_data(await get_credit_policy(db)))


@router.put("/credit-policy")
async def update_credit_policy(
    payload: CreditPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    policy = await get_credit_policy(db, lock=True)
    before = credit_policy_data(policy)
    for field, value in payload.model_dump(exclude={"reason"}).items():
        setattr(policy, field, value)
    policy.version += 1
    after = credit_policy_data(policy)
    add_audit(
        db,
        admin_id=admin.id,
        action="update_credit_policy",
        target_type="credit_policy",
        target_id=policy.key,
        reason=payload.reason,
        before=before,
        after=after,
    )
    await db.commit()
    await db.refresh(policy)
    return success(credit_policy_data(policy))


@router.get("/models")
async def list_admin_models(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return success(model_settings_payload(await get_model_settings(db)))


@router.put("/models/{media_type}/{model_id}")
async def update_admin_model(
    media_type: str,
    model_id: str,
    payload: ModelAdminSettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        get_model_capability(media_type, model_id)
    except ValueError as exc:
        raise NotFoundError("模型不存在") from exc
    # Re-query the media group under one lock to keep its single default invariant.
    settings = list(
        await db.scalars(
            select(ModelAdminSetting)
            .where(ModelAdminSetting.media_type == media_type)
            .with_for_update()
        )
    )
    setting = next((item for item in settings if item.model_id == model_id), None)
    if not setting:
        raise NotFoundError("模型设置不存在")
    before = {
        "label": setting.label,
        "enabled": setting.enabled,
        "is_default": setting.is_default,
    }
    if setting.is_default and not payload.is_default:
        raise RequestError("请先设置其他启用模型为默认模型")
    if setting.is_default and not payload.enabled:
        raise RequestError("请先设置其他启用模型为默认模型")
    if payload.is_default and not payload.enabled:
        raise RequestError("默认模型必须启用")
    setting.label = payload.label
    setting.enabled = payload.enabled
    if payload.is_default:
        for item in settings:
            item.is_default = item.id == setting.id
    if not any(item.enabled and item.is_default for item in settings):
        raise RequestError("每种媒体必须保留一个启用的默认模型")
    after = {
        "label": setting.label,
        "enabled": setting.enabled,
        "is_default": setting.is_default,
    }
    add_audit(
        db,
        admin_id=admin.id,
        action="update_model_setting",
        target_type="model_admin_setting",
        target_id=setting.id,
        reason=payload.reason,
        before=before,
        after=after,
    )
    await db.commit()
    return success(next(item for item in model_settings_payload(settings) if item["model_id"] == model_id))


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


@router.get("/tasks")
async def list_tasks(
    q: str = "",
    media_type: str = Query("all", pattern="^(all|text|image|video|audio)$"),
    model: str = "",
    status: str = "",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = []
    if q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(User.username.ilike(term), User.email.ilike(term)))
    if media_type != "all":
        filters.append(GenerationTask.task_type.in_([media_type, f"{media_type}_reverse"]))
    if model.strip():
        filters.append(GenerationTask.model == model.strip())
    if status.strip():
        filters.append(GenerationTask.status == status.strip())
    if start_at:
        filters.append(GenerationTask.created_at >= start_at)
    if end_at:
        filters.append(GenerationTask.created_at < end_at)
    statement = select(GenerationTask, User).join(User, User.id == GenerationTask.user_id).where(*filters)
    total = int(await db.scalar(select(func.count()).select_from(GenerationTask).join(User).where(*filters)) or 0)
    rows = (await db.execute(statement.order_by(GenerationTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = [task_summary_data(task, user) for task, user in rows]
    return success(page_data(page, page_size, total, items))


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    row = (
        await db.execute(
            select(GenerationTask, User)
            .join(User, User.id == GenerationTask.user_id)
            .where(GenerationTask.id == task_id)
        )
    ).one_or_none()
    if not row:
        raise NotFoundError("生成任务不存在")
    return success(task_detail_data(*row))


@router.post("/tasks/{task_id}/provider-status")
async def get_task_provider_status(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise NotFoundError("生成任务不存在")
    if not task.provider_task_id:
        raise RequestError("该任务没有 Provider 任务 ID，无法查询上游状态")
    if task.provider != "toapis" or task.task_type not in {"image", "video"}:
        raise RequestError("该任务暂不支持查询上游状态")

    try:
        async with ToApisProvider() as provider:
            fetch = (
                provider.get_image_task
                if task.task_type == "image"
                else provider.get_video_task
            )
            state = await fetch(task.provider_task_id)
    except Exception as exc:
        logger.exception(
            "Admin provider status query failed",
            extra={"task_id": str(task.id)},
        )
        raise ServiceUnavailableError("上游状态查询失败，请稍后重试") from exc

    error = state.get("error") or {}
    error_message = error.get("message") if isinstance(error, dict) else str(error)
    safe_message = str(error_message) if error_message else None
    return success(
        {
            "provider_task_id": task.provider_task_id,
            "status": state.get("status") or "unknown",
            "progress": max(0, min(100, int(state.get("progress") or 0))),
            "error_message": safe_message,
            "checked_at": datetime.now(UTC).isoformat(),
        }
    )


@router.get("/audits")
async def list_audits(
    admin_id: uuid.UUID | None = None,
    action: str = "",
    target_type: str = "",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = []
    if admin_id:
        filters.append(AdminAuditLog.admin_id == admin_id)
    if action.strip():
        filters.append(AdminAuditLog.action == action.strip())
    if target_type.strip():
        filters.append(AdminAuditLog.target_type == target_type.strip())
    if start_at:
        filters.append(AdminAuditLog.created_at >= start_at)
    if end_at:
        filters.append(AdminAuditLog.created_at < end_at)
    statement = select(AdminAuditLog, User).join(User, User.id == AdminAuditLog.admin_id).where(*filters)
    total = int(await db.scalar(select(func.count()).select_from(AdminAuditLog).where(*filters)) or 0)
    rows = (await db.execute(statement.order_by(AdminAuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = [{
        "id": str(audit.id), "admin": {"id": str(admin.id), "username": admin.username}, "action": audit.action,
        "target_type": audit.target_type, "target_id": audit.target_id, "reason": audit.reason,
        "before_snapshot": audit.before_snapshot, "after_snapshot": audit.after_snapshot, "created_at": audit.created_at.isoformat(),
    } for audit, admin in rows]
    return success(page_data(page, page_size, total, items))


@router.get("/recharge/tiers")
async def list_recharge_tiers(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    tiers = list(
        await db.scalars(select(RechargeTier).order_by(RechargeTier.currency, RechargeTier.min_amount_cents))
    )
    return success([tier_data(tier) for tier in tiers])


@router.post("/recharge/tiers")
async def create_recharge_tier(
    payload: RechargeTierMutationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    tiers = list(await db.scalars(select(RechargeTier).with_for_update()))
    if any(tier.currency == payload.currency and tier.min_amount_cents == payload.min_amount_cents for tier in tiers):
        raise RequestError("该充值金额阶梯已存在")
    tier = RechargeTier(**payload.model_dump(exclude={"reason"}))
    try:
        validate_tiers([*tiers, tier], await get_billing_policy(db))
    except RechargeError as exc:
        raise RequestError(str(exc)) from exc
    db.add(tier)
    await db.flush()
    add_audit(
        db,
        admin_id=admin.id,
        action="create_recharge_tier",
        target_type="recharge_tier",
        target_id=tier.id,
        reason=payload.reason,
        before={},
        after=tier_data(tier),
    )
    await db.commit()
    await db.refresh(tier)
    return success(tier_data(tier))


@router.put("/recharge/tiers/{tier_id}")
async def update_recharge_tier(
    tier_id: uuid.UUID,
    payload: RechargeTierMutationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    tiers = list(await db.scalars(select(RechargeTier).with_for_update()))
    tier = next((item for item in tiers if item.id == tier_id), None)
    if not tier:
        raise NotFoundError("充值阶梯不存在")
    if any(
        item.id != tier_id and item.currency == payload.currency and item.min_amount_cents == payload.min_amount_cents
        for item in tiers
    ):
        raise RequestError("该充值金额阶梯已存在")
    before = tier_data(tier)
    tier.currency = payload.currency
    tier.min_amount_cents = payload.min_amount_cents
    tier.bonus_rate_bps = payload.bonus_rate_bps
    tier.enabled = payload.enabled
    try:
        validate_tiers(tiers, await get_billing_policy(db))
    except RechargeError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    add_audit(
        db,
        admin_id=admin.id,
        action="update_recharge_tier",
        target_type="recharge_tier",
        target_id=tier.id,
        reason=payload.reason,
        before=before,
        after=tier_data(tier),
    )
    await db.commit()
    await db.refresh(tier)
    return success(tier_data(tier))


@router.get("/recharge/orders")
async def list_recharge_orders(
    q: str = "",
    status: str = Query("all", pattern="^(all|pending|paid|failed)$"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = []
    if q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                User.username.ilike(term),
                User.email.ilike(term),
                RechargeOrder.out_trade_no.ilike(term),
                RechargeOrder.provider_trade_no.ilike(term),
            )
        )
    if status != "all":
        filters.append(RechargeOrder.status == status)
    if start_at:
        filters.append(RechargeOrder.created_at >= start_at)
    if end_at:
        filters.append(RechargeOrder.created_at < end_at)
    statement = select(RechargeOrder, User).join(User, User.id == RechargeOrder.user_id).where(*filters)
    total = int(
        await db.scalar(
            select(func.count()).select_from(RechargeOrder).join(User).where(*filters)
        )
        or 0
    )
    rows = (
        await db.execute(
            statement.order_by(RechargeOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        {
            **order_data(order),
            "user": {"id": str(user.id), "username": user.username, "email": user.email},
        }
        for order, user in rows
    ]
    return success(page_data(page, page_size, total, items))


@router.get("/recharge/orders/{order_id}")
async def get_admin_recharge_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    order = await db.get(RechargeOrder, order_id)
    if not order:
        raise NotFoundError("充值订单不存在")
    return success(admin_order_data(order))


@router.post("/recharge/orders/{order_id}/query")
async def query_admin_recharge_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    order = await db.get(RechargeOrder, order_id)
    if not order:
        raise NotFoundError("充值订单不存在")
    try:
        if order.provider == "cahaya":
            order = await sync_cahaya_order(db, order)
    except RechargeError as exc:
        error_type = ServiceUnavailableError if exc.status_code == 503 else RequestError
        raise error_type(str(exc)) from exc
    return success(admin_order_data(order))
    ModelAdminSettingUpdateRequest,
