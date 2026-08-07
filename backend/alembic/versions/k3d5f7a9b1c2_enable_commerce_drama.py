"""enable commerce drama template

Revision ID: k3d5f7a9b1c2
Revises: j2c4e6f8a0b1
Create Date: 2026-08-07
"""

from copy import deepcopy
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k3d5f7a9b1c2"
down_revision: Union[str, Sequence[str], None] = "j2c4e6f8a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDER_INSTRUCTION = (
    "你是专业的中文电商短剧分镜策划师。请严格执行用户提示词，根据商品资料、角色参考和剧情要求，"
    "生成可直接用于生图和视频生成的短剧分镜方案。商品必须自然参与剧情推进，不得脱离人物动机强行植入；"
    "人物身份、外观、关系、商品状态和场景连续性必须保持稳定。严格按照指定 JSON 输出协议返回一个合法 "
    "JSON 对象，不解释，不使用 Markdown，不添加代码块或额外文本。prompt 和 videoPrompt 必须是完整可执行的"
    "生成提示词，不得省略镜头，不得进行二次概括。"
)
PROMPT_BLOCKS = {
    "creative_direction": (
        "围绕一个明确的生活困境、人物误会或需求冲突展开短剧情。开头3秒内出现人物目标或冲突，商品必须作为"
        "推动剧情、解决问题或证明结果的关键道具自然进入故事，不能脱离剧情单独口播。整体节奏紧凑、人物动机"
        "明确、转折合理，结尾完成冲突解决、商品价值验证和自然转化，不使用生硬广告腔。"
    ),
    "story_structure": (
        "全片共{segment_count}个15秒剧情段落，每段固定6个镜头。第一段建立人物、场景和核心冲突；中间段通过"
        "行动、误会、失败或对比升级矛盾，并让商品逐步参与解决问题；最后一段完成结果验证、情绪回收和自然转化。"
        "每段必须包含明确的开头状态、剧情目标和结尾状态，后一段必须能承接前一段的动作、人物关系和未解决问题。"
    ),
    "character_rules": (
        "本次共有{character_count}个指定角色，每个角色只能对应自己的参考图，不得新增主要人物。角色的脸部、"
        "发型、服装、年龄感、体型和身份在所有分段中保持一致。每个角色必须有明确的关系、目标和行为动机，不能"
        "为了介绍商品突然改变性格。没有角色参考图时不得生成可识别的特定人物。"
    ),
    "dialogue_rules": (
        "对白必须服务于人物关系、冲突推进或商品体验，使用自然中文口语和短句，禁止连续背诵卖点。每句对白必须"
        "标明说话角色，并与当前镜头动作对应；可使用的格式示例：{speaker_examples}。每15秒安排4至6句有效对白，"
        "允许停顿、反问和情绪变化。画外音只用于补充无法通过动作和对白表达的信息，不得代替主要剧情。"
    ),
    "product_placement_rules": (
        "商品必须在第一段前两个镜头内自然出现，并通过拿取、使用、试吃、展示、对比或结果反馈参与剧情。商品外观、"
        "颜色、材质、包装结构和尺寸必须以参考图及商品资料为准，不得虚构功能、价格、优惠、认证或效果。卖点应通过"
        "人物行为和结果表现，不安排角色面向镜头逐条念卖点。商品不得突然出现、无理由消失或在镜头间改变规格。"
    ),
    "image_rules": (
        "生图prompt要求：生成一张{columns}列×{rows}行的六格短剧分镜板，按从左到右、从上到下对应镜头1至"
        "镜头6，每格保持{ratio}视频画幅。明确描述人物位置、动作、表情、商品状态、场景、构图、景别和光线。"
        "相邻镜头必须保持角色、服装、商品、道具和场景连续。分镜板只允许出现“镜头1”至“镜头6”标签，不生成"
        "字幕、价格、二维码、水印或额外Logo；包装文字无法准确复现时避免正面特写。生图prompt禁止写对白和音效。"
    ),
    "video_rules": (
        "生视频prompt要求：严格引用图片1分镜图并按照六格镜头顺序生成视频，明确写出{ratio}画幅、参考图关系、"
        "人物动作、对白、景别、运镜、光线和现场声音。每个镜头只完成一个清晰动作，人物身份、服装、商品状态和"
        "空间位置必须与参考图及前后镜头一致。对白优先清晰可辨，背景音乐不得遮盖对白。禁止无原因跳轴、人物瞬移、"
        "商品变形、动作倒放和镜头内容错位。视频提示词中所有图片编号必须与实际参考顺序一致。"
    ),
    "continuity_rules": (
        "第一段固定使用cut，作为独立剧情开场。后续分段使用extend时，必须承接上一段结尾的人物位置、动作、"
        "表情、商品状态、场景、光影和声音；使用cut时允许切换时间或地点，但必须通过对白、动作或画面建立清晰的"
        "剧情关系。不得把extend写成无关联的新场景，也不得在cut后假装动作连续。"
    ),
    "forbidden_rules": (
        "禁止无铺垫反转、强行煽情、人物动机突变、无关角色抢戏和商品硬插入。禁止虚构疗效、绝对化承诺、价格"
        "优惠、销量、认证和用户评价。禁止血腥暴力、危险模仿、歧视、低俗暗示和违法内容。禁止人物脸部漂移、"
        "服装变化、商品变形、包装乱码、字幕、水印、二维码及额外Logo。禁止使用快速蒙太奇掩盖剧情不连续。"
    ),
}
CONTINUITY = {
    "cut": {"label": "独立新段", "description": "不引用上一段视频"},
    "extend": {"label": "延续上段", "description": "引用上一段视频保持连续性"},
}


def merge_commerce_drama_config(existing: dict[str, Any] | None) -> dict[str, Any]:
    result = deepcopy(existing or {})
    result["schema_version"] = 2
    result["implementation_status"] = "ready"
    result.setdefault("label", "短剧带货")
    result.setdefault("description", "通过剧情内容完成商品植入与转化")
    if not result.get("durations"):
        result["durations"] = [30, 45, 60]
    if not str(result.get("provider_instruction", "")).strip():
        result["provider_instruction"] = PROVIDER_INSTRUCTION
    result["output_protocol_id"] = "commerce-drama-v1"
    existing_blocks = result.get("prompt_blocks") or {}
    result["prompt_blocks"] = {
        key: value if str(value := existing_blocks.get(key, "")).strip() else default
        for key, default in PROMPT_BLOCKS.items()
    }
    result.setdefault("continuity", deepcopy(CONTINUITY))
    return result


def upgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    row = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(
            templates.c.key == "commerce_drama"
        )
    ).mappings().first()
    if row:
        connection.execute(
            templates.update()
            .where(templates.c.key == "commerce_drama")
            .values(
                config=merge_commerce_drama_config(row["config"]),
                enabled=True,
                version=row["version"] + 1,
            )
        )
    else:
        connection.execute(
            templates.insert().values(
                key="commerce_drama",
                version=1,
                enabled=True,
                config=merge_commerce_drama_config(None),
            )
        )


def downgrade() -> None:
    templates = sa.table(
        "content_templates",
        sa.column("key", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("config", postgresql.JSONB()),
    )
    connection = op.get_bind()
    row = connection.execute(
        sa.select(templates.c.config).where(templates.c.key == "commerce_drama")
    ).mappings().first()
    if not row:
        return
    config = deepcopy(row["config"])
    config["implementation_status"] = "draft"
    connection.execute(
        templates.update()
        .where(templates.c.key == "commerce_drama")
        .values(enabled=False, config=config)
    )
