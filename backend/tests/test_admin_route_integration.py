import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import ACCESS_COOKIE, create_token
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import AdminAuditLog, GenerationTask, RechargeOrder, User, Workspace


READ_CASES = [
    ("/dashboard", "object", {"days", "task_count", "recharge_amount_cents", "success_rate", "model_calls"}),
    ("/models", "list", {"media_type", "model_id", "label", "enabled", "is_default"}),
    ("/content-templates", "list", {"key", "version", "enabled", "config"}),
    ("/content-templates/product_visual", "object", {"key", "version", "enabled", "config"}),
    ("/users", "page", {"id", "username", "email", "role", "status", "credit_balance"}),
    ("/audits", "page", {"id", "admin", "action", "target_type", "reason", "created_at"}),
    ("/pricing", "list", {"id", "provider", "media_type", "model", "enabled", "billing_unit"}),
    ("/billing-policy", "object", {"version", "recharge_min_cents", "unit_amount_cents", "unit_credits"}),
    ("/credit-policy", "object", {"version", "registration_bonus_enabled", "daily_refill_enabled"}),
    ("/recharge/tiers", "list", {"id", "currency", "min_amount_cents", "bonus_rate_bps", "enabled"}),
    ("/recharge/orders", "page", {"id", "user", "out_trade_no", "amount_cents", "provider", "status"}),
    ("/recharge/orders/{order_id}", "object", {"id", "out_trade_no", "status", "callback_payload", "tier_snapshot"}),
    ("/tasks", "page", {"id", "user", "task_type", "provider", "model", "status", "credit_status"}),
    ("/tasks/{task_id}", "object", {"id", "user", "workspace_id", "request_snapshot", "pricing_snapshot", "result"}),
]


async def seed_route_contract_data():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        users = []
        for role in ("user", "admin"):
            identifier = uuid.uuid4()
            user = User(
                id=identifier,
                username=f"route-{role}-{identifier.hex[:8]}",
                email=f"{identifier.hex}@example.com",
                password_hash="test-unused-hash",
                role=role,
                status="active",
                is_system=False,
                auth_version=0,
            )
            db.add(user)
            users.append(user)
        regular, admin = users
        await db.flush()
        task = GenerationTask(
            user_id=regular.id,
            workspace_id=workspace.id,
            node_id="admin-route-contract",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
            status="queued",
            request_snapshot={"prompt": "contract test"},
        )
        order = RechargeOrder(
            user_id=regular.id,
            out_trade_no=f"contract{uuid.uuid4().hex[:24]}",
            provider="zpay",
            amount_cents=100,
            amount_minor=100,
            currency="CNY",
            base_credits=1,
            bonus_credits=0,
            total_credits=1,
            status="pending",
            tier_snapshot={},
        )
        audit = AdminAuditLog(
            admin_id=admin.id,
            action="contract_test",
            target_type="user",
            target_id=str(regular.id),
            reason="后台路由响应回归",
        )
        db.add_all([task, order, audit])
        await db.commit()
        tokens = [
            create_token(user.id, user.auth_version, "access", timedelta(minutes=5))[0]
            for user in users
        ]
        return tokens, task.id, order.id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,shape,required_fields", READ_CASES, ids=[case[0] for case in READ_CASES]
)
async def test_admin_read_routes_keep_permissions_and_response_contract(
    path, shape, required_fields
):
    (user_token, admin_token), task_id, order_id = await seed_route_contract_data()
    url = "/api/admin" + path.format(task_id=task_id, order_id=order_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unauthenticated = await client.get(url)
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["error_key"] == "unauthorized"

        client.cookies.set(ACCESS_COOKIE, user_token)
        forbidden = await client.get(url)
        assert forbidden.status_code == 403
        assert forbidden.json()["error_key"] == "forbidden"

        client.cookies.set(ACCESS_COOKIE, admin_token)
        response = await client.get(url)
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["message"] == "ok"
    data = payload["data"]
    if shape == "page":
        assert {"items", "page", "page_size", "total"} <= data.keys()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] >= 1
        items = data["items"]
    elif shape == "list":
        assert isinstance(data, list)
        items = data
    else:
        assert isinstance(data, dict)
        items = [data]
    assert items
    for item in items:
        assert required_fields <= item.keys()
    if path == "/tasks":
        assert all("request_snapshot" not in item and "result" not in item for item in items)
