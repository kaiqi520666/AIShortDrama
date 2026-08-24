import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.api.routes.admin as admin_routes
from app.core.auth import hash_password
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_admin
from app.main import app
from app.models import AdminAuditLog, GenerationTask, User, Workspace


@pytest.mark.asyncio
async def test_admin_actions_audit_and_credit_floor():
    admin_id = uuid.uuid4()
    target_id = uuid.uuid4()
    async with SessionLocal() as db:
        admin = User(
            id=admin_id, username=f"admin-{admin_id.hex[:8]}", email=f"admin-{admin_id.hex[:8]}@example.com",
            password_hash=hash_password("password-123"), role="admin", is_system=False,
        )
        target = User(
            id=target_id, username=f"target-{target_id.hex[:8]}", email=f"target-{target_id.hex[:8]}@example.com",
            password_hash=hash_password("password-123"), credit_balance=5, is_system=False,
        )
        db.add_all([admin, target])
        await db.commit()

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            adjusted = await client.post(f"/api/admin/users/{target_id}/credits", json={"amount": -3, "reason": "测试扣减"})
            assert adjusted.status_code == 200
            assert adjusted.json()["data"]["credit_balance"] == 2

            rejected = await client.post(f"/api/admin/users/{target_id}/credits", json={"amount": -3, "reason": "测试下限"})
            assert rejected.status_code == 422

            promoted = await client.post(f"/api/admin/users/{target_id}/role", json={"role": "admin", "reason": "授权测试"})
            assert promoted.status_code == 200
            assert promoted.json()["data"]["role"] == "admin"

        async with SessionLocal() as db:
            target = await db.get(User, target_id)
            assert target.auth_version == 1
            audit_actions = list(await db.scalars(select(AdminAuditLog.action).where(AdminAuditLog.admin_id == admin_id)))
            assert sorted(audit_actions) == ["adjust_credits", "change_role"]
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_admin_cannot_demote_or_disable_self():
    admin_id = uuid.uuid4()
    async with SessionLocal() as db:
        admin = User(
            id=admin_id, username=f"self-{admin_id.hex[:8]}", email=f"self-{admin_id.hex[:8]}@example.com",
            password_hash=hash_password("password-123"), role="admin", is_system=False,
        )
        db.add(admin)
        await db.commit()

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.post(f"/api/admin/users/{admin_id}/role", json={"role": "user", "reason": "测试"})).status_code == 422
            assert (await client.post(f"/api/admin/users/{admin_id}/status", json={"status": "disabled", "reason": "测试"})).status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_admin_task_list_is_lightweight_and_detail_has_diagnostics(monkeypatch):
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        admin = await db.get(User, workspace.user_id)
        admin.role = "admin"
        task = GenerationTask(
            user_id=admin.id,
            workspace_id=workspace.id,
            node_id="admin-task-detail",
            task_type="video",
            provider="toapis",
            model="seedance-2-mini",
            status="failed",
            provider_task_id="provider-task-123",
            request_snapshot={"prompt": "private prompt"},
            pricing_snapshot={"credits": 10},
            result={"type": "video"},
            error_message="视频生成服务暂时不可用",
            diagnostic_snapshot={
                "code": "fail_to_fetch_task",
                "data": None,
                "message": {"error": {"code": "upstream_timeout"}},
            },
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listed = await client.get("/api/admin/tasks")
            assert listed.status_code == 200
            item = next(
                item for item in listed.json()["data"]["items"] if item["id"] == str(task_id)
            )
            assert item["provider_task_id"] == "provider-task-123"
            assert "diagnostic_summary" not in item
            assert "request_snapshot" not in item
            assert "pricing_snapshot" not in item
            assert "result" not in item

            detailed = await client.get(f"/api/admin/tasks/{task_id}")
            assert detailed.status_code == 200
            data = detailed.json()["data"]
            assert data["diagnostic_snapshot"] == {
                "code": "fail_to_fetch_task",
                "data": None,
                "message": {"error": {"code": "upstream_timeout"}},
            }
            assert data["request_snapshot"] == {"prompt": "private prompt"}
            assert data["pricing_snapshot"] == {"credits": 10}
            assert data["result"] == {"type": "video"}

            class FakeProvider:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_):
                    pass

                async def get_video_task(self, provider_task_id):
                    assert provider_task_id == "provider-task-123"
                    return {
                        "status": "failed",
                        "progress": 65,
                        "error": {"message": "内容审核拒绝"},
                    }

            monkeypatch.setattr(admin_routes, "ToApisProvider", FakeProvider)
            refreshed = await client.post(
                f"/api/admin/tasks/{task_id}/provider-status"
            )
            assert refreshed.status_code == 200
            assert refreshed.json()["data"] | {"checked_at": None} == {
                "provider_task_id": "provider-task-123",
                "status": "failed",
                "progress": 65,
                "error_message": "内容审核拒绝",
                "checked_at": None,
            }
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
