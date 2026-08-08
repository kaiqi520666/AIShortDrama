import copy
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.routes import admin_reference_assets
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_admin
from app.main import app
from app.models import (
    AdminAuditLog,
    CreditLedger,
    GenerationTask,
    ModelAdminSetting,
    RechargeOrder,
    RechargeTier,
    User,
    Workspace,
)
from app.services.recharge import calculate_recharge
from app.services.media_upload import StoredMedia


async def create_admin() -> User:
    admin_id = uuid.uuid4()
    async with SessionLocal() as db:
        admin = User(
            id=admin_id,
            username=f"config-admin-{admin_id.hex[:8]}",
            email=f"config-admin-{admin_id.hex[:8]}@example.com",
            password_hash="test",
            role="admin",
            is_system=False,
        )
        db.add(admin)
        await db.commit()
        return admin


def admin_client(admin: User):
    app.dependency_overrides[get_current_admin] = lambda: admin
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_billing_policy_update_changes_new_quotes_and_is_audited():
    admin = await create_admin()
    try:
        async with admin_client(admin) as client:
            before = await client.get("/api/admin/billing-policy")
            assert before.status_code == 200
            policy = before.json()["data"]
            response = await client.put(
                "/api/admin/billing-policy",
                json={
                    "recharge_min_cents": policy["recharge_min_cents"],
                    "recharge_max_cents": policy["recharge_max_cents"],
                    "unit_amount_cents": 7000,
                    "unit_credits": 1000,
                    "reason": "验证动态兑换比例",
                },
            )
        assert response.status_code == 200
        assert response.json()["data"]["version"] == policy["version"] + 1

        async with SessionLocal() as db:
            quote = await calculate_recharge(db, 3500)
            audit = await db.scalar(
                select(AdminAuditLog).where(AdminAuditLog.action == "update_billing_policy")
            )
            assert quote.base_credits == 500
            assert audit and audit.after_snapshot["unit_amount_cents"] == 7000
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_model_settings_enforce_default_and_capabilities_only_return_enabled(
    override_business_user,
):
    admin = await create_admin()
    try:
        async with SessionLocal() as db:
            image_settings = list(
                await db.scalars(
                    select(ModelAdminSetting).where(ModelAdminSetting.media_type == "image")
                )
            )
            current_default = next(item for item in image_settings if item.is_default)
            alternative = next(item for item in image_settings if item.id != current_default.id)

        async with admin_client(admin) as client:
            switched = await client.put(
                f"/api/admin/models/image/{alternative.model_id}",
                json={
                    "label": "测试默认图片模型",
                    "enabled": True,
                    "is_default": True,
                    "reason": "切换默认模型",
                },
            )
            assert switched.status_code == 200
            assert switched.json()["data"]["is_default"] is True

            disabled = await client.put(
                f"/api/admin/models/image/{current_default.model_id}",
                json={
                    "label": current_default.label,
                    "enabled": False,
                    "is_default": False,
                    "reason": "停用测试模型",
                },
            )
            assert disabled.status_code == 200

            rejected = await client.put(
                f"/api/admin/models/image/{alternative.model_id}",
                json={
                    "label": "测试默认图片模型",
                    "enabled": False,
                    "is_default": True,
                    "reason": "尝试停用默认模型",
                },
            )
            assert rejected.status_code == 422

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            capabilities = await client.get("/api/generations/capabilities")
        image_models = {item["id"] for item in capabilities.json()["data"]["image"]["models"]}
        assert alternative.model_id in image_models
        assert current_default.model_id not in image_models
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
async def test_content_template_version_is_validated_and_published(override_business_user):
    admin = await create_admin()
    try:
        async with admin_client(admin) as client:
            catalog = await client.get("/api/admin/content-templates")
            assert catalog.status_code == 200
            assert [(item["key"], item["status"]) for item in catalog.json()["data"]] == [
                ("product_visual", "active"),
                ("apparel_visual", "active"),
                ("product_storyboard", "active"),
                ("commerce_drama", "active"),
                ("apparel_showcase", "active"),
            ]
            fetched = await client.get("/api/admin/content-templates/product_visual")
            assert fetched.status_code == 200
            template = fetched.json()["data"]
            config = copy.deepcopy(template["config"])
            config["groups"][0]["label"] = "测试基础展示"
            updated = await client.put(
                "/api/admin/content-templates/product_visual",
                json={"enabled": True, "config": config, "reason": "调整图种分组名称"},
            )
            assert updated.status_code == 200
            assert updated.json()["data"]["version"] == template["version"] + 1

            invalid = copy.deepcopy(config)
            invalid["groups"][0]["items"][0]["id"] = "changed-id"
            rejected = await client.put(
                "/api/admin/content-templates/product_visual",
                json={"enabled": True, "config": invalid, "reason": "非法修改图种 ID"},
            )
            assert rejected.status_code == 422

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            published = await client.get("/api/content-templates/product")
        assert published.status_code == 200
        visual_config = published.json()["data"]["product_visual"]["config"]
        assert visual_config["groups"][0]["label"] == "测试基础展示"
        assert visual_config["schema_version"] == 2
        assert visual_config["output_protocol_id"] == "product-visual-v1"
        assert "provider_instruction" not in visual_config
        assert "prompt_blocks" not in visual_config
        assert "business_instruction" not in visual_config
        assert "prompt_blocks" not in published.json()["data"]["product_storyboard"]["config"]
        assert published.json()["data"]["commerce_drama"]["config"]["output_protocol_id"] == "commerce-drama-v1"
        assert "prompt_blocks" not in published.json()["data"]["commerce_drama"]["config"]
        assert published.json()["data"]["apparel_visual"]["config"]["output_protocol_id"] == "apparel-visual-v1"
        assert "prompt_blocks" not in published.json()["data"]["apparel_visual"]["config"]
        assert published.json()["data"]["apparel_showcase"]["config"]["durations"] == [15, 30, 45, 60]
        assert "prompt_blocks" not in published.json()["data"]["apparel_showcase"]["config"]
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [1, 7, 30])
async def test_admin_dashboard_returns_period_metrics(days, override_business_user):
    admin = await create_admin()
    task_id = uuid.uuid4()
    order_id = uuid.uuid4()
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        tier = await db.scalar(select(RechargeTier).where(RechargeTier.enabled.is_(True)))
        db.add(
            GenerationTask(
                id=task_id,
                user_id=override_business_user,
                workspace_id=workspace.id,
                node_id=f"dashboard-{days}-{task_id.hex[:8]}",
                task_type="image",
                provider="test",
                model="gpt-image-2",
                status="succeeded",
                finished_at=datetime.now(UTC),
            )
        )
        await db.flush()
        db.add(
            RechargeOrder(
                id=order_id,
                user_id=override_business_user,
                tier_id=tier.id,
                out_trade_no=f"dashboard-{order_id.hex[:20]}",
                amount_cents=3500,
                base_credits=1000,
                bonus_credits=0,
                total_credits=1000,
                status="paid",
                paid_at=datetime.now(UTC),
            )
        )
        db.add(
            CreditLedger(
                user_id=override_business_user,
                task_id=task_id,
                entry_type="consume",
                amount=42,
                balance_after=999_958,
                frozen_after=0,
                idempotency_key=f"dashboard-consume-{task_id}",
            )
        )
        await db.commit()
    try:
        async with admin_client(admin) as client:
            response = await client.get("/api/admin/dashboard", params={"days": days})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["days"] == days
        assert data["recharge_amount_cents"] == 3500
        assert data["consumed_credits"] == 42
        assert data["succeeded_count"] == 1
        assert data["success_rate"] == 1.0
        assert data["queue_depth"] is None or isinstance(data["queue_depth"], int)
        assert data["model_calls"] == [{"model": "gpt-image-2", "count": 1}]
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


class FakeStorage:
    async def delete_object(self, _object_key):
        return None


class FakeMediaUploadService:
    async def store(self, _file, _media_type, _prefix):
        return StoredMedia(
            object_key="library/system/test.png",
            url="https://example.com/system-model.png",
            content_type="image/png",
            byte_size=3,
            width=12,
            height=24,
            storage=FakeStorage(),
        )


@pytest.mark.asyncio
async def test_system_reference_asset_hides_copyright_and_respects_active_state(
    monkeypatch, override_business_user,
):
    admin = await create_admin()
    monkeypatch.setattr(
        admin_reference_assets,
        "get_media_upload_service",
        lambda: FakeMediaUploadService(),
    )
    try:
        async with admin_client(admin) as client:
            created = await client.post(
                "/api/admin/reference-assets",
                data={
                    "resource_type": "model",
                    "name": "系统模特测试",
                    "sort_order": "3",
                    "tags": "女性,生活方式",
                    "copyright_note": "内部版权备注",
                    "reason": "测试系统素材上传",
                },
                files={"file": ("model.png", b"png", "image/png")},
            )
            assert created.status_code == 200
            asset = created.json()["data"]
            assert asset["library"]["copyright_note"] == "内部版权备注"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            public_list = await client.get("/api/outfit-models")
        public_asset = next(item for item in public_list.json()["data"] if item["id"] == asset["id"])
        assert public_asset["metadata"]["library"] == {"tags": ["女性", "生活方式"]}

        async with admin_client(admin) as client:
            disabled = await client.put(
                f"/api/admin/reference-assets/model/{asset['id']}",
                json={
                    "name": asset["name"],
                    "sort_order": 3,
                    "active": False,
                    "tags": ["女性"],
                    "copyright_note": "内部版权备注",
                    "reason": "测试下架系统素材",
                },
            )
        assert disabled.status_code == 200
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            public_list = await client.get("/api/outfit-models")
        assert asset["id"] not in {item["id"] for item in public_list.json()["data"]}
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
