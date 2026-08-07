from copy import deepcopy
from string import Formatter
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentTemplate


PRODUCT_VISUAL_KEY = "product_visual"
UGC_STORYBOARD_KEY = "product_storyboard"
COMMERCE_DRAMA_KEY = "commerce_drama"
STORYBOARD_TEMPLATE_ID = "ugc-seeding"
STORYBOARD_DURATIONS = {15, 30, 45, 60}
PRODUCT_VISUAL_GROUPS = {
    "basic": ("white-bg", "first-screen", "multi-angle", "series-show"),
    "marketing": ("core-selling", "use-scenario", "ambient-scene", "contrast-effect"),
    "detail": ("detail-zoom", "specs-info", "tech-specs", "manufacturing", "ingredients"),
    "trust": ("brand-story", "freebies", "warranty", "usage-tips"),
}

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
UGC_PLACEHOLDERS = {
    "director_role": set(),
    "shooting_style": set(),
    "dialogue_no_character": set(),
    "dialogue_with_characters": {"character_count", "speaker_examples"},
    "image_rules": {"columns", "rows", "ratio"},
    "video_rules": {"ratio"},
    "first_segment_rule": {"segment"},
    "extend_segment_rule": {"segment", "previous_segment"},
}
DEFAULT_CONTINUITY = {
    "cut": {"label": "独立新段", "description": "不引用上一段视频"},
    "extend": {"label": "延续上段", "description": "引用上一段视频保持连续性"},
}
COMMERCE_DRAMA_BLOCKS = (
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

TEMPLATE_DEFINITIONS = {
    PRODUCT_VISUAL_KEY: {
        "group": "product_image",
        "group_label": "商品图片模板",
        "label": "商品出图",
        "status": "active",
        "order": 0,
    },
    UGC_STORYBOARD_KEY: {
        "group": "content",
        "group_label": "内容模板",
        "label": "UGC 种草",
        "status": "active",
        "order": 1,
    },
    COMMERCE_DRAMA_KEY: {
        "group": "content",
        "group_label": "内容模板",
        "label": "短剧带货",
        "status": "draft",
        "order": 2,
    },
}
TEMPLATE_KEYS = set(TEMPLATE_DEFINITIONS)
PRODUCT_TEMPLATE_KEYS = {PRODUCT_VISUAL_KEY, UGC_STORYBOARD_KEY}


def default_ugc_config() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "templates": [
            {
                "id": STORYBOARD_TEMPLATE_ID,
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
        "prompt_blocks": deepcopy(UGC_PROMPT_BLOCKS),
        "continuity": deepcopy(DEFAULT_CONTINUITY),
    }


def default_commerce_drama_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "label": "短剧带货",
        "description": "通过剧情内容完成商品植入与转化",
        "implementation_status": "draft",
        "durations": [],
        "prompt_blocks": {key: "" for key in COMMERCE_DRAMA_BLOCKS},
        "continuity": deepcopy(DEFAULT_CONTINUITY),
    }


def template_data(template: ContentTemplate) -> dict[str, Any]:
    return {
        "key": template.key,
        "version": template.version,
        "enabled": template.enabled,
        "config": deepcopy(template.config),
    }


def template_catalog_item(template: ContentTemplate) -> dict[str, Any]:
    definition = TEMPLATE_DEFINITIONS[template.key]
    return {**template_data(template), **definition}


async def get_template_catalog(db: AsyncSession) -> list[dict[str, Any]]:
    templates = list(
        await db.scalars(select(ContentTemplate).where(ContentTemplate.key.in_(TEMPLATE_KEYS)))
    )
    if {template.key for template in templates} != TEMPLATE_KEYS:
        raise RuntimeError("内容模板未初始化")
    return sorted((template_catalog_item(template) for template in templates), key=lambda item: item["order"])


async def get_product_templates(db: AsyncSession) -> dict[str, dict[str, Any]]:
    templates = list(
        await db.scalars(
            select(ContentTemplate).where(ContentTemplate.key.in_(PRODUCT_TEMPLATE_KEYS))
        )
    )
    if {template.key for template in templates} != PRODUCT_TEMPLATE_KEYS:
        raise RuntimeError("商品模板未初始化")
    result = {}
    for template in templates:
        data = template_data(template)
        if template.key == UGC_STORYBOARD_KEY:
            config = template.config
            data["config"] = {
                "schema_version": config["schema_version"],
                "templates": deepcopy(config["templates"]),
                "durations": deepcopy(config["durations"]),
                "continuity": deepcopy(config["continuity"]),
            }
        result[template.key] = data
    return result


def _text(value: Any, label: str, *, max_length: int = 6000, required: bool = True) -> str:
    if not isinstance(value, str) or len(value.strip()) > max_length:
        raise ValueError(f"{label}无效")
    if required and not value.strip():
        raise ValueError(f"{label}无效")
    return value.strip()


def _validate_continuity(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict) or set(value) != {"cut", "extend"}:
        raise ValueError("分镜衔接配置无效")
    result = {}
    for key in ("cut", "extend"):
        item = value[key]
        if not isinstance(item, dict):
            raise ValueError("分镜衔接配置无效")
        result[key] = {
            "label": _text(item.get("label"), "衔接名称", max_length=32),
            "description": _text(item.get("description"), "衔接说明", max_length=120),
        }
    return result


def _validate_prompt_block(key: str, value: Any) -> str:
    text = _text(value, "Prompt 区块", max_length=12_000)
    try:
        placeholders = {
            field_name
            for _, field_name, _, _ in Formatter().parse(text)
            if field_name is not None
        }
    except ValueError as exc:
        raise ValueError("Prompt 动态变量格式无效") from exc
    if placeholders != UGC_PLACEHOLDERS[key]:
        raise ValueError(f"{key} 动态变量无效")
    return text


def _validate_product_visual(value: dict[str, Any], _enabled: bool) -> dict[str, Any]:
    groups = value.get("groups")
    if not isinstance(groups, list) or len(groups) != len(PRODUCT_VISUAL_GROUPS):
        raise ValueError("商品图种分组无效")
    result_groups = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("商品图种分组无效")
        group_id = group.get("id")
        expected_ids = PRODUCT_VISUAL_GROUPS.get(group_id)
        items = group.get("items")
        item_ids = [item.get("id") if isinstance(item, dict) else None for item in items or []]
        if not expected_ids or not isinstance(items, list) or item_ids != list(expected_ids):
            raise ValueError("图种 ID 不允许修改或删除")
        result_groups.append(
            {
                "id": group_id,
                "label": _text(group.get("label"), "图种分组名称", max_length=64),
                "items": [
                    {
                        "id": item["id"],
                        "label": _text(item.get("label"), "图种名称", max_length=64),
                        "default_enabled": bool(item.get("default_enabled")),
                    }
                    for item in items
                ],
            }
        )
    if not any(item["default_enabled"] for group in result_groups for item in group["items"]):
        raise ValueError("至少保留一个默认图种")
    return {
        "groups": result_groups,
        "business_instruction": _text(
            value.get("business_instruction", ""),
            "商品图种业务指令",
            required=False,
        ),
    }


def _validate_ugc(value: dict[str, Any], _enabled: bool) -> dict[str, Any]:
    templates = value.get("templates")
    durations = value.get("durations")
    if not isinstance(templates, list) or len(templates) != 1 or not isinstance(templates[0], dict):
        raise ValueError("商品分镜模板无效")
    template = templates[0]
    if template.get("id") != STORYBOARD_TEMPLATE_ID:
        raise ValueError("分镜模板 ID 不允许修改")
    if not isinstance(durations, list) or not durations or any(item not in STORYBOARD_DURATIONS for item in durations):
        raise ValueError("商品分镜时长无效")
    blocks = value.get("prompt_blocks")
    if not isinstance(blocks, dict) or set(blocks) != set(UGC_PROMPT_BLOCKS):
        raise ValueError("UGC Prompt 区块无效")
    if value.get("schema_version") != 2:
        raise ValueError("UGC 模板版本无效")
    return {
        "schema_version": 2,
        "templates": [
            {
                "id": STORYBOARD_TEMPLATE_ID,
                "label": _text(template.get("label"), "分镜模板名称", max_length=64),
                "description": _text(template.get("description"), "分镜模板描述", max_length=255),
                "enabled": bool(template.get("enabled")),
            }
        ],
        "durations": sorted(set(durations)),
        "business_instruction": _text(value.get("business_instruction"), "商品分镜业务指令"),
        "provider_instruction": _text(
            value.get("provider_instruction"), "模型角色指令", max_length=2000
        ),
        "prompt_blocks": {
            key: _validate_prompt_block(key, blocks[key]) for key in UGC_PROMPT_BLOCKS
        },
        "continuity": _validate_continuity(value.get("continuity")),
    }


def _validate_commerce_drama(value: dict[str, Any], enabled: bool) -> dict[str, Any]:
    if enabled:
        raise ValueError("短剧带货生成流程尚未接入，暂时不能启用")
    blocks = value.get("prompt_blocks")
    if value.get("schema_version") != 1 or not isinstance(blocks, dict) or set(blocks) != set(COMMERCE_DRAMA_BLOCKS):
        raise ValueError("短剧带货模板配置无效")
    durations = value.get("durations")
    if not isinstance(durations, list) or any(not isinstance(item, int) or item <= 0 for item in durations):
        raise ValueError("短剧带货时长配置无效")
    return {
        "schema_version": 1,
        "label": _text(value.get("label"), "短剧带货名称", max_length=64),
        "description": _text(value.get("description"), "短剧带货描述", max_length=255),
        "implementation_status": "draft",
        "durations": sorted(set(durations)),
        "prompt_blocks": {
            key: _text(blocks[key], "短剧带货配置", max_length=12_000, required=False)
            for key in COMMERCE_DRAMA_BLOCKS
        },
        "continuity": _validate_continuity(value.get("continuity")),
    }


TEMPLATE_VALIDATORS: dict[str, Callable[[dict[str, Any], bool], dict[str, Any]]] = {
    PRODUCT_VISUAL_KEY: _validate_product_visual,
    UGC_STORYBOARD_KEY: _validate_ugc,
    COMMERCE_DRAMA_KEY: _validate_commerce_drama,
}


def validate_template_config(key: str, value: Any, *, enabled: bool = False) -> dict[str, Any]:
    validator = TEMPLATE_VALIDATORS.get(key)
    if not validator or not isinstance(value, dict):
        raise ValueError("模板配置无效")
    return validator(value, enabled)
