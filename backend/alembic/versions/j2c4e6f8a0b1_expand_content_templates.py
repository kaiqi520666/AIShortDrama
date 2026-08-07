"""expand content templates for UGC and commerce drama

Revision ID: j2c4e6f8a0b1
Revises: h9b2d4e6f8a0
Create Date: 2026-08-07
"""

from copy import deepcopy
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "j2c4e6f8a0b1"
down_revision: Union[str, Sequence[str], None] = "h9b2d4e6f8a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UGC_PROVIDER_INSTRUCTION = (
    "你是专业的中文电商UGC种草分镜策划师。完整执行用户提示词，并严格按其中指定的 JSON 结构输出，"
    "不解释，不使用 Markdown。"
)
UGC_PROMPT_BLOCKS = {
    "director_role": (
        "你是商品UGC种草分镜导演，负责直接为项目生成可执行的生图提示词和Seedance 2视频提示词。"
        "只保留“UGC 种草”这一种内容，禁止输出其他内容模板。必须自行在每条prompt和videoPrompt中"
        "完整写出拍摄方式、镜头、景别、运镜、光线、声音和对白。"
    ),
    "shooting_style": (
        "UGC种草统一拍摄风格：全程由人物本人或同行者真实手持手机拍摄。自拍视频使用手臂长度的前置广角；"
        "第三人称跟拍、第一视角和商品近景使用后置1倍主摄。保留轻微腕部晃动、走路起伏、临时调整构图、"
        "自动对焦呼吸、自然曝光变化和环境混合光，手持感自然克制，不是剧烈抖动。\n"
        "不使用三脚架、稳定器、滑轨、机械推镜、环绕运镜、专用微距、人像模式、电影级浅景深、慢动作、"
        "电影调色或商业广告运镜。镜头之间直接硬切，每个镜头只完成一个连续动作，动作结束后再切换，"
        "不快速蒙太奇。背景环境保持清晰可辨，构图允许轻微倾斜、偏离中心和自然截断，保留真实肤质和"
        "手机自动曝光变化。"
    ),
    "dialogue_no_character": (
        "没有角色参考图时不得生成可识别人脸；使用画外音或现场音，画外音必须写成‘画外音说道：\"内容。\"’。"
    ),
    "dialogue_with_characters": (
        "共有{character_count}个指定角色，每个角色只能对应自己的参考图，不得新增人物。{speaker_examples}。"
        "每个镜头都要有与当前动作相关的自然分享或连续画外音，人物未露脸、手部特写和商品特写也不能停止分享。"
        "对白必须使用中文双引号，禁止写“台词：”，禁止背诵式广告口号。"
    ),
    "image_rules": (
        "生图prompt要求：生成一张{columns}列×{rows}行的六格UGC分镜板，按从左到右、从上到下对应镜头1至"
        "镜头6，每个小格保持{ratio}视频画幅。每格是像真实iPhone生活视频截取的未调色原始帧，明确写出人物"
        "动作、地点、商品状态、画面构图和实际拍法；六格之间场景或动作要有区别。分镜板只允许出现“镜头1”至"
        "“镜头6”作为格子标签，不要时长、字幕、价格、二维码、水印、额外Logo或其他可识别文字。包装文字无法"
        "准确复现时，让文字区域侧置、手部遮挡或轻微虚化，不要乱码。生图prompt禁止写对白、音效和背景音乐。"
    ),
    "video_rules": (
        "生视频prompt要求：严格引用图片1分镜图的构图和动作顺序，明确写出{ratio}画幅、参考图关系、六个镜头"
        "的地点、主体动作、景别、单一运镜、手持手机方式、自然光线、现场音和对白。每个镜头只完成一个连续动作，"
        "动作结束后硬切；不能用快速蒙太奇。自拍视频使用手臂长度的前置广角，第一视角和商品近景使用后置1倍主摄，"
        "侧面或背面跟拍使用同行者后置1倍主摄。保留轻微腕部晃动、走路起伏、自动对焦呼吸和曝光变化，不要棚拍、"
        "电影调色、广告布景、背景虚化或英雄产品镜头。对白使用‘她说道：\"内容。\"’、‘他说道：\"内容。\"’、"
        "‘他回答：\"内容。\"’或对应角色编号，禁止写“台词：”。保留脚步、风声、呼吸、开盖和勺子碰触玻璃等"
        "现场声音，不生成背景音乐。视频提示词中所有图片编号必须与上方实际顺序一致。"
    ),
    "first_segment_rule": (
        "第{segment}段：15秒，固定6个镜头，按镜头1至镜头6顺序输出。第一段必须独立开场，开头尽快出现商品。"
    ),
    "extend_segment_rule": (
        "第{segment}段：15秒，固定6个镜头，按镜头1至镜头6顺序输出。本段默认承接第{previous_segment}段；"
        "videoPrompt开头必须明确写“向后延长视频{previous_segment}，延续上一段的主体、场景、光影、声音和"
        "手持拍摄质感”，只有确实换场时才写独立换场。"
    ),
}
CONTINUITY = {
    "cut": {"label": "独立新段", "description": "不引用上一段视频"},
    "extend": {"label": "延续上段", "description": "引用上一段视频保持连续性"},
}
DEFAULT_UGC_CONFIG = {
    "schema_version": 2,
    "templates": [
        {
            "id": "ugc-seeding",
            "label": "UGC 种草",
            "description": "用户视角真实分享体验",
            "enabled": True,
        }
    ],
    "durations": [15, 30, 45, 60],
    "business_instruction": (
        "以真实用户体验分享为主，不设置复杂剧情，不使用广告腔，开头尽快出现商品并通过实际操作和试吃表达感受。"
    ),
    "provider_instruction": UGC_PROVIDER_INSTRUCTION,
    "prompt_blocks": UGC_PROMPT_BLOCKS,
    "continuity": CONTINUITY,
}
DEFAULT_COMMERCE_DRAMA_CONFIG = {
    "schema_version": 1,
    "label": "短剧带货",
    "description": "通过剧情内容完成商品植入与转化",
    "implementation_status": "draft",
    "durations": [],
    "prompt_blocks": {
        key: ""
        for key in (
            "creative_direction",
            "story_structure",
            "character_rules",
            "dialogue_rules",
            "product_placement_rules",
            "image_rules",
            "video_rules",
            "continuity_rules",
            "forbidden_rules",
        )
    },
    "continuity": CONTINUITY,
}


def merge_ugc_config(existing: dict[str, Any] | None) -> dict[str, Any]:
    result = deepcopy(existing or {})
    for key, value in DEFAULT_UGC_CONFIG.items():
        result.setdefault(key, deepcopy(value))
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
            templates.c.key == "product_storyboard"
        )
    ).mappings().first()
    if row:
        connection.execute(
            templates.update()
            .where(templates.c.key == "product_storyboard")
            .values(config=merge_ugc_config(row["config"]), version=row["version"] + 1)
        )
    else:
        connection.execute(
            templates.insert().values(
                key="product_storyboard",
                version=1,
                enabled=True,
                config=deepcopy(DEFAULT_UGC_CONFIG),
            )
        )
    existing_drama = connection.scalar(
        sa.select(templates.c.key).where(templates.c.key == "commerce_drama")
    )
    if not existing_drama:
        connection.execute(
            templates.insert().values(
                key="commerce_drama",
                version=1,
                enabled=False,
                config=deepcopy(DEFAULT_COMMERCE_DRAMA_CONFIG),
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
    connection.execute(templates.delete().where(templates.c.key == "commerce_drama"))
    row = connection.execute(
        sa.select(templates.c.version, templates.c.config).where(
            templates.c.key == "product_storyboard"
        )
    ).mappings().first()
    if row:
        config = deepcopy(row["config"])
        for key in ("schema_version", "provider_instruction", "prompt_blocks", "continuity"):
            config.pop(key, None)
        connection.execute(
            templates.update()
            .where(templates.c.key == "product_storyboard")
            .values(config=config, version=max(1, row["version"] - 1))
        )
