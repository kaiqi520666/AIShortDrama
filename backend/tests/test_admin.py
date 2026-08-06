import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import hash_password
from app.core.database import SessionLocal
from app.core.identity import get_current_admin
from app.main import app
from app.models import AdminAuditLog, User


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
            assert rejected.status_code == 400

            promoted = await client.post(f"/api/admin/users/{target_id}/role", json={"role": "admin", "reason": "授权测试"})
            assert promoted.status_code == 200
            assert promoted.json()["data"]["role"] == "admin"

        async with SessionLocal() as db:
            target = await db.get(User, target_id)
            assert target.auth_version == 1
            audit_actions = list(await db.scalars(select(AdminAuditLog.action).where(AdminAuditLog.admin_id == admin_id)))
            assert audit_actions == ["adjust_credits", "change_role"]
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
            assert (await client.post(f"/api/admin/users/{admin_id}/role", json={"role": "user", "reason": "测试"})).status_code == 400
            assert (await client.post(f"/api/admin/users/{admin_id}/status", json={"status": "disabled", "reason": "测试"})).status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
