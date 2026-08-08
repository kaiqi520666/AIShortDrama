"""add apparel visual and showcase templates

Revision ID: p6g8i0k2m4n5
Revises: n5f7h9j1l3m4
Create Date: 2026-08-08
"""

from copy import deepcopy
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "p6g8i0k2m4n5"
down_revision: Union[str, Sequence[str], None] = "n5f7h9j1l3m4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTINUITY = {
    "cut": {"label": "独立新段", "description": "不引用上一段视频"},
    "extend": {"label": "延续上段", "description": "引用上一段视频保持连续性"},
}
APPAREL_VISUAL_CONFIG = {
    "schema_version": 1,
    "groups": [{
        "id": "views",
        "label": "六视角试穿",
        "items": [
            {"id": "front", "label": "正面全身", "default_enabled": True},
            {"id": "three-quarter", "label": "45°侧面", "default_enabled": True},
            {"id": "back", "label": "背面展示", "default_enabled": True},
            {"id": "turn", "label": "动态转身", "default_enabled": True},
            {"id": "fabric", "label": "面料细节", "default_enabled": True},
            {"id": "lifestyle", "label": "场景试穿", "default_enabled": True},
        ],
    }],
    "business_instruction": "生成同一模特、同一服饰的六视角试穿素材，优先保证服饰与人物一致性。",
    "provider_instruction": (
        "你是专业的中文服饰试穿视觉策划师。严格保持参考服饰和模特身份一致，并按用户指定的 JSON 数组输出，"
        "不解释，不使用 Markdown。"
    ),
    "output_protocol_id": "apparel-visual-v1",
    "prompt_blocks": {
        "task_instruction": (
            "图片1是服饰参考图，图片2是模特参考图。请为以下试穿视角分别生成一条中文图片提示词：{views}。"
            "统一画面规格：{aspect_ratio}，{resolution}。"
        ),
        "fidelity_rules": (
            "所有视角必须保持同一模特的脸部、发型、体型和肤色一致；严格保持服饰类别、颜色、图案、Logo、"
            "面料、版型、长度、开合方式和工艺细节，不新增或删除单品，不改变真实穿着层级。"
        ),
        "output_protocol": (
            '严格输出 JSON 数组，格式为 [{"id":"视角ID","prompt":"提示词"}]。'
            "每个视角必须且只能出现一次，顺序与请求一致。每条提示词必须明确引用图片1服饰和图片2模特，"
            "只描述该视角特有的姿态、构图、场景、光线和服饰展示重点，不解释，不使用 Markdown。"
        ),
    },
}
APPAREL_SHOWCASE_CONFIG = {
    "schema_version": 1,
    "label": "服饰展示",
    "description": "基于模特试穿总览生成多段服饰展示分镜与视频",
    "durations": [15, 30, 45, 60],
    "provider_instruction": (
        "你是专业的中文服饰展示分镜导演。根据服饰试穿总览、服饰原图、模特原图和可选场景参考，生成可直接用于"
        "生图和 Seedance 2 视频生成的服饰展示方案。严格按指定 JSON 输出协议返回合法 JSON 对象，不解释，"
        "不使用 Markdown。"
    ),
    "output_protocol_id": "apparel-showcase-v1",
    "prompt_blocks": {
        "creative_direction": "以服饰本身为视觉核心，通过模特自然站立、转身、行走和局部近景展示整体廓形、正侧背面、动态垂坠感、面料纹理和适用场景。画面专业但自然，不设计剧情对白，不使用夸张广告动作。",
        "segment_structure": "全片共{segment_count}个15秒展示段，每段固定6个镜头。第一段建立完整造型并展示正面、侧面和背面；后续段依次扩展动态行走、转身、面料工艺、搭配比例和生活场景，禁止重复相同构图与动作。",
        "apparel_fidelity_rules": "服饰类别、颜色、图案、Logo、面料、版型、长度、开合方式、层级和工艺必须与参考图一致。不得增加、删除或替换单品，不得改变袖长、领型、腰线、裤型、裙长和真实材质。",
        "model_consistency_rules": "所有分段保持同一模特的脸部、发型、年龄感、肤色、体型和身份一致。姿态可以变化，但身体比例、妆容和基础造型不得漂移。",
        "shot_rules": "每段6个镜头必须包含完整造型、正面或45度展示、侧面或背面展示、自然动态、服饰局部细节和场景定格。每个镜头只完成一个连续动作，景别由全身到中近景合理变化，服饰始终清晰可见。",
        "image_rules": "生图prompt要求：生成一张{columns}列×{rows}行的六格服饰展示分镜板，按从左到右、从上到下对应镜头1至镜头6，每格保持{ratio}视频画幅。图片1是六格试穿总览，图片2为可选场景参考。分镜板只允许出现镜头1至镜头6标签，不生成字幕、水印、价格、二维码或额外Logo，prompt不得包含对白和声音。",
        "video_rules": "生视频prompt要求：图片1是当前段分镜图，严格按六格顺序描述动作、景别、单一运镜、光线和自然衔接，画幅为{ratio}。禁止台词、口播、旁白、字幕和背景音乐，只保留脚步、衣料摩擦和环境声。",
        "continuity_rules": "第一段固定使用cut。后续使用extend时必须承接上一段结尾的模特位置、动作、服饰状态、场景、光影和声音；使用cut时可以切换场景或展示重点，但模特身份和服饰外观必须保持一致。",
        "forbidden_rules": "禁止服饰变色、图案或Logo漂移、材质替换、版型变化、衣物穿插、肢体畸形、模特换脸、无原因换装、快速蒙太奇、对白、口播、旁白、字幕、水印、二维码和额外Logo。",
    },
    "continuity": CONTINUITY,
}


def upgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    for key, config in (
        ("apparel_visual", APPAREL_VISUAL_CONFIG),
        ("apparel_showcase", APPAREL_SHOWCASE_CONFIG),
    ):
        if not connection.scalar(sa.select(templates.c.key).where(templates.c.key == key)):
            connection.execute(
                templates.insert().values(
                    key=key,
                    version=1,
                    enabled=True,
                    config=deepcopy(config),
                )
            )


def downgrade() -> None:
    templates = sa.table("content_templates", sa.column("key", sa.String()))
    op.get_bind().execute(
        templates.delete().where(
            templates.c.key.in_(("apparel_visual", "apparel_showcase"))
        )
    )
