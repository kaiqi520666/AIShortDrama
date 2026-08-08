"""simplify apparel try-on

Revision ID: q7h9j1l3n5o6
Revises: p6g8i0k2m4n5
Create Date: 2026-08-09
"""

from copy import deepcopy
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "q7h9j1l3n5o6"
down_revision: Union[str, Sequence[str], None] = "p6g8i0k2m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDER_INSTRUCTION = (
    "你是专业的中文服饰试穿视觉策划师。严格保持参考服饰和模特身份一致，并按用户指定的 JSON 对象输出，"
    "不解释，不使用 Markdown。"
)
OLD_BUSINESS_INSTRUCTION = "生成同一模特、同一服饰的六视角试穿素材，优先保证服饰与人物一致性。"
BUSINESS_INSTRUCTION = "生成一张可确认服饰与模特一致性的正面全身试穿定妆图，供后续分镜和视频使用。"
TASK_INSTRUCTION = (
    "图片1是服饰参考图，图片2是模特参考图。请生成一条中文图片提示词，将图片1中的完整服饰准确穿到"
    "图片2的模特身上，输出一张正面全身试穿定妆图。统一画面规格：{aspect_ratio}，{resolution}。"
)
FIDELITY_RULES = (
    "保持模特的脸部、发型、体型、肤色和身份一致；严格保持服饰类别、颜色、图案、Logo、面料、版型、"
    "长度、开合方式和工艺细节，不新增或删除单品，不改变真实穿着层级。模特自然站立，手臂不遮挡服饰，"
    "人物从头到脚完整可见，背景简洁，光线自然，适合作为后续服饰分镜和视频的一致性参考。"
)
OLD_FIDELITY_RULES = (
    "所有视角必须保持同一模特的脸部、发型、体型和肤色一致；严格保持服饰类别、颜色、图案、Logo、"
    "面料、版型、长度、开合方式和工艺细节，不新增或删除单品，不改变真实穿着层级。"
)
OUTPUT_PROTOCOL = (
    '严格输出 JSON 对象，格式为 {"prompt":"图片提示词"}。提示词必须明确引用图片1服饰和图片2模特，'
    "完整描述人物、服饰、姿态、构图、背景和光线，不生成六宫格、多视角拼图、文字、字幕或水印，"
    "不解释，不使用 Markdown。"
)
OLD_VIEWS = [
    {"id": "front", "label": "正面全身", "default_enabled": True},
    {"id": "three-quarter", "label": "45°侧面", "default_enabled": True},
    {"id": "back", "label": "背面展示", "default_enabled": True},
    {"id": "turn", "label": "动态转身", "default_enabled": True},
    {"id": "fabric", "label": "面料细节", "default_enabled": True},
    {"id": "lifestyle", "label": "场景试穿", "default_enabled": True},
]


def simplify_apparel_visual_config(config: dict) -> dict:
    blocks = config.get("prompt_blocks") or {}
    business_instruction = config.get("business_instruction")
    fidelity_rules = blocks.get("fidelity_rules")
    return {
        "schema_version": 2,
        "business_instruction": (
            BUSINESS_INSTRUCTION
            if not business_instruction or business_instruction == OLD_BUSINESS_INSTRUCTION
            else business_instruction
        ),
        "provider_instruction": PROVIDER_INSTRUCTION,
        "output_protocol_id": "apparel-visual-v2",
        "prompt_blocks": {
            "task_instruction": TASK_INSTRUCTION,
            "fidelity_rules": (
                FIDELITY_RULES
                if not fidelity_rules or fidelity_rules == OLD_FIDELITY_RULES
                else fidelity_rules
            ),
            "output_protocol": OUTPUT_PROTOCOL,
        },
    }


def _replace_showcase_copy(config: dict, reverse: bool = False) -> dict:
    result = deepcopy(config)
    replacements = (
        (("基于试穿定妆图", "基于模特试穿总览"), ("试穿定妆图", "六格试穿总览"))
        if reverse
        else (
            ("基于模特试穿总览", "基于试穿定妆图"),
            ("服饰试穿总览", "试穿定妆图"),
            ("六格试穿总览", "试穿定妆图"),
        )
    )
    for source, target in replacements:
        for key in ("description", "provider_instruction"):
            if isinstance(result.get(key), str):
                result[key] = result[key].replace(source, target)
        blocks = result.get("prompt_blocks") or {}
        for key, value in blocks.items():
            if isinstance(value, str):
                blocks[key] = value.replace(source, target)
    return result


def upgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    apparel = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(templates.c.key == "apparel_visual")
    ).mappings().first()
    if apparel:
        old = apparel["config"] or {}
        connection.execute(
            templates.update().where(templates.c.key == "apparel_visual").values(
                version=apparel["version"] + 1,
                config=simplify_apparel_visual_config(old),
            )
        )

    showcase = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(templates.c.key == "apparel_showcase")
    ).mappings().first()
    if showcase:
        connection.execute(
            templates.update().where(templates.c.key == "apparel_showcase").values(
                version=showcase["version"] + 1,
                config=_replace_showcase_copy(showcase["config"] or {}),
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
    apparel = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(templates.c.key == "apparel_visual")
    ).mappings().first()
    if apparel:
        current = apparel["config"] or {}
        current_blocks = current.get("prompt_blocks") or {}
        business_instruction = current.get("business_instruction")
        fidelity_rules = current_blocks.get("fidelity_rules")
        connection.execute(
            templates.update().where(templates.c.key == "apparel_visual").values(
                version=max(1, apparel["version"] - 1),
                config={
                    "schema_version": 1,
                    "groups": [{"id": "views", "label": "六视角试穿", "items": OLD_VIEWS}],
                    "business_instruction": (
                        OLD_BUSINESS_INSTRUCTION
                        if business_instruction == BUSINESS_INSTRUCTION
                        else business_instruction or ""
                    ),
                    "provider_instruction": (
                        "你是专业的中文服饰试穿视觉策划师。严格保持参考服饰和模特身份一致，并按用户指定的 "
                        "JSON 数组输出，不解释，不使用 Markdown。"
                    ),
                    "output_protocol_id": "apparel-visual-v1",
                    "prompt_blocks": {
                        "task_instruction": (
                            "图片1是服饰参考图，图片2是模特参考图。请为以下试穿视角分别生成一条中文图片提示词："
                            "{views}。统一画面规格：{aspect_ratio}，{resolution}。"
                        ),
                        "fidelity_rules": (
                            OLD_FIDELITY_RULES
                            if fidelity_rules == FIDELITY_RULES
                            else fidelity_rules or OLD_FIDELITY_RULES
                        ),
                        "output_protocol": (
                            '严格输出 JSON 数组，格式为 [{"id":"视角ID","prompt":"提示词"}]。'
                            "每个视角必须且只能出现一次，顺序与请求一致。"
                        ),
                    },
                },
            )
        )
    showcase = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(templates.c.key == "apparel_showcase")
    ).mappings().first()
    if showcase:
        connection.execute(
            templates.update().where(templates.c.key == "apparel_showcase").values(
                version=max(1, showcase["version"] - 1),
                config=_replace_showcase_copy(showcase["config"] or {}, reverse=True),
            )
        )
