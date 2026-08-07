"""add admin configuration overlays

Revision ID: h9b2d4e6f8a0
Revises: g8a1c3e5f7b9
Create Date: 2026-08-07
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h9b2d4e6f8a0"
down_revision: Union[str, Sequence[str], None] = "g8a1c3e5f7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_policies",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("recharge_min_cents", sa.Integer(), nullable=False),
        sa.Column("recharge_max_cents", sa.Integer(), nullable=False),
        sa.Column("unit_amount_cents", sa.Integer(), nullable=False),
        sa.Column("unit_credits", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("key = 'default'", name="ck_billing_policies_singleton"),
        sa.CheckConstraint("recharge_min_cents > 0", name="ck_billing_policies_min_positive"),
        sa.CheckConstraint("recharge_max_cents >= recharge_min_cents", name="ck_billing_policies_range"),
        sa.CheckConstraint("unit_amount_cents > 0", name="ck_billing_policies_unit_amount"),
        sa.CheckConstraint("unit_credits > 0", name="ck_billing_policies_unit_credits"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(
        sa.table(
            "billing_policies",
            sa.column("key", sa.String()),
            sa.column("recharge_min_cents", sa.Integer()),
            sa.column("recharge_max_cents", sa.Integer()),
            sa.column("unit_amount_cents", sa.Integer()),
            sa.column("unit_credits", sa.Integer()),
        ),
        [{"key": "default", "recharge_min_cents": 3500, "recharge_max_cents": 350000, "unit_amount_cents": 3500, "unit_credits": 1000}],
    )

    op.create_table(
        "model_admin_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_model_admin_settings_media_model", "model_admin_settings", ["media_type", "model_id"], unique=True)
    models = [
        ("text", "gpt-5.6-sol", "GPT-5.6 Sol", True),
        ("image", "gpt-image-2", "GPT Image 2", True),
        ("image", "doubao-seedream-5-0-pro", "Seedream 5.0 Pro", False),
        ("image", "doubao-seedream-5-0", "Seedream 5.0", False),
        ("image", "gemini-3-pro-image-preview", "Gemini 3 Pro", False),
        ("image", "gemini-3.1-flash-image-preview", "Gemini 3.1 Flash", False),
        ("video", "seedance-2", "Seedance 2", False),
        ("video", "seedance-2-fast", "Seedance 2 Fast", False),
        ("video", "seedance-2-mini", "Seedance 2 Mini", True),
        ("audio", "seed-audio-1.0-multilingual", "Seed Audio 1.0", True),
    ]
    op.bulk_insert(
        sa.table(
            "model_admin_settings",
            sa.column("id", sa.Uuid()),
            sa.column("media_type", sa.String()),
            sa.column("model_id", sa.String()),
            sa.column("label", sa.String()),
            sa.column("enabled", sa.Boolean()),
            sa.column("is_default", sa.Boolean()),
        ),
        [
            {"id": uuid.uuid4(), "media_type": media_type, "model_id": model_id, "label": label, "enabled": True, "is_default": is_default}
            for media_type, model_id, label, is_default in models
        ],
    )

    op.create_table(
        "content_templates",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(
        sa.table(
            "content_templates",
            sa.column("key", sa.String()),
            sa.column("enabled", sa.Boolean()),
            sa.column("config", postgresql.JSONB()),
        ),
        [
            {
                "key": "product_visual",
                "enabled": True,
                "config": {
                    "groups": [
                        {"id": "basic", "label": "基础展示", "items": [{"id": "white-bg", "label": "白底图", "default_enabled": True}, {"id": "first-screen", "label": "首屏主视觉", "default_enabled": True}, {"id": "multi-angle", "label": "多角度", "default_enabled": False}, {"id": "series-show", "label": "系列 SKU", "default_enabled": False}]},
                        {"id": "marketing", "label": "营销卖点", "items": [{"id": "core-selling", "label": "核心卖点", "default_enabled": True}, {"id": "use-scenario", "label": "使用场景", "default_enabled": True}, {"id": "ambient-scene", "label": "氛围场景", "default_enabled": True}, {"id": "contrast-effect", "label": "效果对比", "default_enabled": False}]},
                        {"id": "detail", "label": "详情说明", "items": [{"id": "detail-zoom", "label": "细节图", "default_enabled": True}, {"id": "specs-info", "label": "规格尺寸", "default_enabled": False}, {"id": "tech-specs", "label": "参数表", "default_enabled": False}, {"id": "manufacturing", "label": "工艺", "default_enabled": False}, {"id": "ingredients", "label": "成分", "default_enabled": False}]},
                        {"id": "trust", "label": "信任保障", "items": [{"id": "brand-story", "label": "品牌故事", "default_enabled": False}, {"id": "freebies", "label": "配件 / 赠品", "default_enabled": False}, {"id": "warranty", "label": "售后保障", "default_enabled": False}, {"id": "usage-tips", "label": "使用建议", "default_enabled": False}]},
                    ],
                    "business_instruction": "",
                },
            },
            {
                "key": "product_storyboard",
                "enabled": True,
                "config": {
                    "templates": [{"id": "ugc-seeding", "label": "UGC 种草", "description": "用户视角真实分享体验", "enabled": True}],
                    "durations": [15, 30, 45, 60],
                    "business_instruction": "以真实用户体验分享为主，不设置复杂剧情，不使用广告腔，开头尽快出现商品并通过实际操作和试吃表达感受。",
                },
            },
        ],
    )

    op.drop_constraint("ck_recharge_tiers_min_amount", "recharge_tiers", type_="check")
    op.create_check_constraint("ck_recharge_tiers_min_amount_positive", "recharge_tiers", "min_amount_cents > 0")


def downgrade() -> None:
    op.drop_constraint("ck_recharge_tiers_min_amount_positive", "recharge_tiers", type_="check")
    op.create_check_constraint("ck_recharge_tiers_min_amount", "recharge_tiers", "min_amount_cents >= 3500")
    op.drop_table("content_templates")
    op.drop_index("uq_model_admin_settings_media_model", table_name="model_admin_settings")
    op.drop_table("model_admin_settings")
    op.drop_table("billing_policies")
