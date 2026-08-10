"""fix apparel optional model copy

Revision ID: t1v3x5z7b9c0
Revises: s9k1m3o5q7r8
"""

from copy import deepcopy
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t1v3x5z7b9c0"
down_revision: Union[str, Sequence[str], None] = "s9k1m3o5q7r8"
branch_labels = None
depends_on = None

OLD_PROVIDER_INSTRUCTION = (
    "你是专业的中文服饰试穿视觉策划师。严格保持参考服饰和模特身份一致，并按用户指定的 JSON 对象输出，"
    "不解释，不使用 Markdown。"
)
PROVIDER_INSTRUCTION = (
    "你是专业的中文服饰试穿视觉策划师。模特参考图是可选输入：未提供时必须依据服饰资料创建自然生活化模特，"
    "不得以缺少图片或无法保持一致为由拒绝生成。严格按用户指定的 JSON 对象输出，不解释，不使用 Markdown。"
)
OLD_TASK_INSTRUCTION = (
    "请根据下方明确列出的参考图角色生成一条中文图片提示词，"
    "输出一张正面全身试穿定妆图。统一画面规格：{aspect_ratio}，{resolution}。"
)
TASK_INSTRUCTION = (
    "请根据下方明确列出的参考图角色生成一条可直接用于生图的中文图片提示词。模特参考图可选：未提供时，"
    "直接依据服饰资料创建自然生活化模特，不得输出缺少图片、无法生成或要求补充参考图的文案。"
    "输出一张正面全身试穿定妆图。统一画面规格：{aspect_ratio}，{resolution}。"
)


def upgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    row = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(templates.c.key == "apparel_visual")
    ).mappings().first()
    if not row:
        return
    config = deepcopy(row["config"] or {})
    blocks = config.get("prompt_blocks") or {}
    changed = False
    if blocks.get("task_instruction") == OLD_TASK_INSTRUCTION:
        blocks["task_instruction"] = TASK_INSTRUCTION
        config["prompt_blocks"] = blocks
        changed = True
    if config.get("provider_instruction") == OLD_PROVIDER_INSTRUCTION:
        config["provider_instruction"] = PROVIDER_INSTRUCTION
        changed = True
    if changed:
        connection.execute(
            templates.update().where(templates.c.key == "apparel_visual").values(
                version=row["version"] + 1,
                config=config,
            )
        )


def downgrade() -> None:
    pass
