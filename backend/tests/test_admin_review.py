import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_admin
from app.main import app
from app.models import AdminAuditLog, CreditLedger, User, Workspace
from app.schemas.generation import VideoGenerationRequest
from app.services.generation_tasks import create_video_task


class FakeRedis:
    def __init__(self):
        self.calls = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return object()


async def create_review_task():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        admin = await db.get(User, workspace.user_id)
        admin.role = "admin"
        task = await create_video_task(
            db, FakeRedis(),
            VideoGenerationRequest(
                workspace_id=workspace.id,
                node_id="admin-review-test",
                model="seedance-2-mini",
                prompt="review",
                duration=5,
                resolution="480p",
                aspect_ratio="16:9",
            ),
            admin.id,
        )
        task.status = "needs_review"
        task.submission_started_at = datetime.now(UTC)
        task.provider_request_id = "provider-review-request"
        await db.commit()
        return task.id, admin, task.frozen_credits, task.submission_started_at


@pytest.mark.asyncio
@pytest.mark.parametrize("action,expected_status", [("fail", "failed"), ("cancel", "cancelled")])
async def test_review_failure_refunds_once_and_records_admin_audit(action, expected_status):
    task_id, admin, frozen_credits, _ = await create_review_task()
    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/admin/tasks/{task_id}/resolve-review",
                json={"action": action, "reason": "人工确认任务已失败"},
            )
            repeated = await client.post(
                f"/api/admin/tasks/{task_id}/resolve-review",
                json={"action": action, "reason": "重复处理"},
            )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == expected_status
        assert response.json()["data"]["credit_status"] == "refunded"
        assert repeated.status_code == 409
        async with SessionLocal() as db:
            refunds = list(await db.scalars(select(CreditLedger).where(
                CreditLedger.task_id == task_id, CreditLedger.entry_type == "refund"
            )))
            assert len(refunds) == 1
            assert refunds[0].amount == frozen_credits
            audits = list(await db.scalars(select(AdminAuditLog).where(
                AdminAuditLog.action == f"resolve_task_review_{action}"
            )))
            assert len(audits) == 1
            assert audits[0].reason == "人工确认任务已失败"
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_review_resume_keeps_submission_mark_and_requeues_once(monkeypatch):
    task_id, admin, _, submitted_at = await create_review_task()
    redis = FakeRedis()
    monkeypatch.setattr(app.state, "redis", redis, raising=False)
    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/admin/tasks/{task_id}/resolve-review",
                json={
                    "action": "resume", "reason": "上游任务已确认",
                    "provider_task_id": "provider-confirmed-task",
                },
            )
            repeated = await client.post(
                f"/api/admin/tasks/{task_id}/resolve-review",
                json={"action": "resume", "reason": "重复恢复"},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "queued"
        assert data["credit_status"] == "frozen"
        assert data["provider_task_id"] == "provider-confirmed-task"
        assert data["provider_request_id"] == "provider-review-request"
        assert data["client_request_id"]
        assert data["submission_started_at"] == submitted_at.isoformat()
        assert repeated.status_code == 409
        assert len(redis.calls) == 1
        assert redis.calls[0][0] == ("generate_video", str(task_id))
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_review_endpoint_requires_admin_and_a_reason():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/admin/tasks/{uuid.uuid4()}/resolve-review",
            json={"action": "fail", "reason": "越权操作"},
        )
    assert response.status_code in {401, 403}
    task_id, admin, _, _ = await create_review_task()
    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/admin/tasks/{task_id}/resolve-review",
                json={"action": "fail", "reason": " "},
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
