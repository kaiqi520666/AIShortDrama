"""add apparel video flow and scene library

Revision ID: r8j0k2m4n6p7
Revises: q7h9j1l3n5o6
"""

from copy import deepcopy
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "r8j0k2m4n6p7"
down_revision: Union[str, Sequence[str], None] = "q7h9j1l3n5o6"
branch_labels = None
depends_on = None

APPAREL_VIDEO_CONFIG = {
    "schema_version": 3,
    "label": "服饰视频模板",
    "description": "管理服饰定妆图与真实手机实拍视频的默认规则",
    "durations": [15, 30, 45, 60],
    "provider_instruction": "你是专业的中文服饰视频策划师。根据服饰资料、可选模特与可选场景，生成一条可直接用于定妆图和Seedance视频生成的中文提示词。严格按指定JSON输出协议返回合法JSON对象，不解释，不使用Markdown。",
    "output_protocol_id": "apparel-video-v2",
    "prompt_blocks": {
        "look_rules": "服饰原图必须作为唯一服装依据。定妆图只生成一张正面全身图，服饰类别、颜色、图案、Logo、面料、版型、长度、开合方式和工艺细节必须一致，不得增加、删除或替换单品。",
        "model_rules": "优先使用用户确认的模特图片或描述；均未提供时使用默认生活化模特描述：{model_description}。定妆图确认后锁定脸部、发型、年龄感、肤色、体型和基础造型，视频中不得换脸、换体型或过度美颜。",
        "scene_rules": "优先使用用户确认的场景图片或描述；均未提供时使用默认生活化场景：{scene_description}。整条视频固定一个场景，不得在视频中无原因切换场景。",
        "phone_style_rules": "使用iPhone后置1倍主摄的真实手机实拍感：手持拍摄、自然环境光、自动曝光和对焦、轻微自然晃动。不使用棚拍灯光、三脚架、稳定器、电影运镜或电影调色。",
        "action_rules": "人物自然站立、整理衣服、侧身展示、缓慢转圈、轻微走动并展示面料和细节。动作舒缓、连续、像真实穿搭博主，不使用夸张广告摆拍。",
        "video_reference_rules": "视频参考图顺序固定：图片1是确认后的定妆图，决定人物、场景、构图和动作；图片2是服饰原图，仅用于校验服饰细节，不得改变图片1中的人物、场景和穿着效果。",
        "sound_rules": "默认不生成声音；用户开启声音时只保留环境音、脚步声和衣料摩擦声，禁止背景音乐、旁白、对白、字幕和口播。",
        "continuation_rules": "用户选择{duration}秒时，系统自动续接15秒片段。每段承接上一段的模特位置、动作方向、服饰状态、场景、光线和环境音，前端不展示分段或cut/extend。",
        "forbidden_rules": "禁止棚拍、电影调色、三脚架、稳定器、广告式夸张摆拍、换装、换脸、换场景、字幕、水印、价格、二维码和额外Logo。",
    },
}


def upgrade() -> None:
    op.create_table(
        "scenes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("image_url", sa.String(2048), nullable=False),
        sa.Column("object_key", sa.String(512)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("scene_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scenes_user_active_sort", "scenes", ["user_id", "active", "sort_order"])
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("config", postgresql.JSONB()),
    )
    row = op.get_bind().execute(sa.select(templates.c.version, templates.c.config).where(templates.c.key == "apparel_showcase")).mappings().first()
    if row:
        config = deepcopy(APPAREL_VIDEO_CONFIG)
        existing = row["config"] or {}
        config["label"] = existing.get("label") or config["label"]
        config["description"] = existing.get("description") or config["description"]
        op.get_bind().execute(templates.update().where(templates.c.key == "apparel_showcase").values(version=row["version"] + 1, config=config))


def downgrade() -> None:
    op.drop_index("ix_scenes_user_active_sort", table_name="scenes")
    op.drop_table("scenes")
