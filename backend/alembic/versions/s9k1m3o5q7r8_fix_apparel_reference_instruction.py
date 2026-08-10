"""fix apparel reference instruction

Revision ID: s9k1m3o5q7r8
Revises: r8j0k2m4n6p7
"""

from copy import deepcopy
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s9k1m3o5q7r8"
down_revision: Union[str, Sequence[str], None] = "r8j0k2m4n6p7"
branch_labels = None
depends_on = None

OLD_PREFIXES = (
    "图片1是服饰参考图；图片2如存在则为模特参考图，图片3如存在则为场景参考图。",
    "图片1是服饰参考图，图片2是模特参考图。",
)
TASK_INSTRUCTION = (
    "请根据下方明确列出的参考图角色生成一条中文图片提示词，"
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
    current = blocks.get("task_instruction")
    if not isinstance(current, str) or not any(prefix in current for prefix in OLD_PREFIXES):
        return
    blocks["task_instruction"] = TASK_INSTRUCTION
    config["prompt_blocks"] = blocks
    connection.execute(
        templates.update().where(templates.c.key == "apparel_visual").values(
            version=row["version"] + 1,
            config=config,
        )
    )


def downgrade() -> None:
    pass
