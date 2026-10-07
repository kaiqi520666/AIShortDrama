import ast
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import RequestError
from app.models import ModelPriceRule
from app.schemas.admin import CreditAdjustmentRequest, PriceRuleUpdateRequest, UserRoleRequest, UserStatusRequest
from app.services import admin_billing, admin_users


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service,payload",
    [
        (admin_users.change_user_role, UserRoleRequest(role="user", reason="降级")),
        (admin_users.change_user_status, UserStatusRequest(status="disabled", reason="停用")),
    ],
)
async def test_admin_user_domain_rejects_self_lockout_before_commit(monkeypatch, service, payload):
    admin = SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(admin_users, "get_target_user", AsyncMock(return_value=admin))
    db = SimpleNamespace(commit=AsyncMock())
    with pytest.raises(RequestError):
        await service(db, admin=admin, user_id=admin.id, payload=payload)
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_credit_domain_rolls_back_rejected_adjustment(monkeypatch):
    monkeypatch.setattr(
        admin_users, "adjust_credits",
        AsyncMock(side_effect=ValueError("扣减后可用积分不能小于 0")),
    )
    db = SimpleNamespace(rollback=AsyncMock())
    with pytest.raises(RequestError, match="扣减后可用积分不能小于 0"):
        await admin_users.adjust_user_credits(
            db,
            admin=SimpleNamespace(id=uuid.uuid4()),
            user_id=uuid.uuid4(),
            payload=CreditAdjustmentRequest(amount=-3, reason="测试"),
        )
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_price_domain_does_not_commit_or_audit_on_integrity_failure():
    rule = ModelPriceRule(
        id=uuid.uuid4(), provider="toapis", media_type="image", model="gpt-image-2",
        specification="1k", billing_unit="per_image", multiplier=1, enabled=True,
    )
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=rule),
        flush=AsyncMock(side_effect=IntegrityError(None, None, Exception("duplicate"))),
        rollback=AsyncMock(),
        commit=AsyncMock(),
        add=Mock(),
    )
    with pytest.raises(RequestError, match="模型、类型和规格组合已存在"):
        await admin_billing.update_price_rule(
            db,
            admin=SimpleNamespace(id=uuid.uuid4()),
            rule_id=rule.id,
            payload=PriceRuleUpdateRequest(multiplier=2, enabled=True, reason="调整价格"),
        )
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.add.assert_not_called()


def test_admin_user_and_billing_routes_keep_business_transactions_in_services():
    routes_dir = Path(__file__).resolve().parents[1] / "app" / "api" / "routes"
    for filename in ("admin_users.py", "admin_billing.py"):
        tree = ast.parse((routes_dir / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "db"
                    and node.func.attr in {"add", "commit", "flush", "rollback", "scalar", "scalars", "execute"}
                )
