"""migrate product visual prompt

Revision ID: n5f7h9j1l3m4
Revises: m4e6g8i0k2l3
Create Date: 2026-08-08
"""

from copy import deepcopy
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "n5f7h9j1l3m4"
down_revision: Union[str, Sequence[str], None] = "m4e6g8i0k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDER_INSTRUCTION = (
    "你是专业的中文电商视觉策划师。严格按用户指定的 JSON 数组输出，不解释，不使用 Markdown。"
)
PROMPT_BLOCKS = {
    "task_instruction": (
        "请根据参考商品图片和商品资料，为以下图种分别生成一条中文图片提示词：{types}。"
        "统一画面规格：{aspect_ratio}，{resolution}。"
    ),
    "output_protocol": (
        '严格输出 JSON 数组，格式为 [{"type":"图种ID","prompt":"提示词"}]。'
        "每个图种必须且只能出现一次，顺序与请求一致。每条提示词不超过 100 个中文字符，只描述该图种"
        "特有的构图、场景、光线、视角与文案布局，不重复商品资料，不虚构图片和资料中没有的商品事实，"
        "不解释，不使用 Markdown。"
    ),
}


def merge_product_visual_config(existing: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(existing)
    result["schema_version"] = 2
    result.setdefault("provider_instruction", PROVIDER_INSTRUCTION)
    result.setdefault("output_protocol_id", "product-visual-v1")
    blocks = result.setdefault("prompt_blocks", {})
    for key, value in PROMPT_BLOCKS.items():
        blocks.setdefault(key, value)
    return result


def upgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    row = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(
            templates.c.key == "product_visual"
        )
    ).mappings().first()
    if row:
        connection.execute(
            templates.update()
            .where(templates.c.key == "product_visual")
            .values(
                version=row["version"] + 1,
                config=merge_product_visual_config(row["config"]),
            )
        )


def downgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    row = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(
            templates.c.key == "product_visual"
        )
    ).mappings().first()
    if not row:
        return
    config = deepcopy(row["config"])
    for key in (
        "schema_version",
        "provider_instruction",
        "output_protocol_id",
        "prompt_blocks",
    ):
        config.pop(key, None)
    connection.execute(
        templates.update()
        .where(templates.c.key == "product_visual")
        .values(version=max(1, row["version"] - 1), config=config)
    )
