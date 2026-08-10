from copy import deepcopy
import re
from string import Formatter
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentTemplate


PRODUCT_VISUAL_KEY = "product_visual"
APPAREL_VISUAL_KEY = "apparel_visual"
UGC_STORYBOARD_KEY = "product_storyboard"
COMMERCE_DRAMA_KEY = "commerce_drama"
APPAREL_SHOWCASE_KEY = "apparel_showcase"
PRODUCT_VISUAL_PROTOCOL_ID = "product-visual-v1"
APPAREL_VISUAL_PROTOCOL_ID = "apparel-visual-v2"
STORYBOARD_TEMPLATE_ID = "ugc-seeding"
COMMERCE_DRAMA_TEMPLATE_ID = "commerce-drama"
COMMERCE_DRAMA_PROTOCOL_ID = "commerce-drama-v1"
APPAREL_SHOWCASE_TEMPLATE_ID = "apparel-showcase"
APPAREL_SHOWCASE_PROTOCOL_ID = "apparel-video-v2"
STORYBOARD_DURATIONS = {15, 30, 45, 60}
COMMERCE_DRAMA_DURATIONS = {30, 45, 60}
PRODUCT_VISUAL_GROUPS = {
    "basic": ("white-bg", "first-screen", "multi-angle", "series-show"),
    "marketing": ("core-selling", "use-scenario", "ambient-scene", "contrast-effect"),
    "detail": ("detail-zoom", "specs-info", "tech-specs", "manufacturing", "ingredients"),
    "trust": ("brand-story", "freebies", "warranty", "usage-tips"),
}
PRODUCT_VISUAL_PROVIDER_INSTRUCTION = (
    "你是专业的中文电商视觉策划师。严格按用户指定的 JSON 数组输出，不解释，不使用 Markdown。"
)
PRODUCT_VISUAL_PROMPT_BLOCKS = {
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
PRODUCT_VISUAL_PLACEHOLDERS = {
    "task_instruction": {"types", "aspect_ratio", "resolution"},
    "output_protocol": set(),
}

APPAREL_VISUAL_PROVIDER_INSTRUCTION = (
    "你是专业的中文服饰试穿视觉策划师。模特参考图是可选输入：未提供时必须依据服饰资料创建自然生活化模特，"
    "不得以缺少图片或无法保持一致为由拒绝生成。严格按用户指定的 JSON 对象输出，不解释，不使用 Markdown。"
)
APPAREL_VISUAL_PROMPT_BLOCKS = {
    "task_instruction": (
        "请根据下方明确列出的参考图角色生成一条可直接用于生图的中文图片提示词。模特参考图可选：未提供时，"
        "直接依据服饰资料创建自然生活化模特，不得输出缺少图片、无法生成或要求补充参考图的文案。"
        "输出一张正面全身试穿定妆图。统一画面规格：{aspect_ratio}，{resolution}。"
    ),
    "fidelity_rules": (
        "如提供模特参考图，保持模特的脸部、发型、体型、肤色和身份一致；严格保持服饰类别、颜色、图案、Logo、面料、版型、"
        "长度、开合方式和工艺细节，不新增或删除单品，不改变真实穿着层级。模特自然站立，手臂不遮挡服饰，"
        "人物从头到脚完整可见，背景简洁，光线自然，适合作为后续服饰分镜和视频的一致性参考。"
    ),
    "output_protocol": (
        '严格输出 JSON 对象，格式为 {"prompt":"图片提示词"}。提示词必须明确引用图片1服饰及可选参考图片，'
        "完整描述人物、服饰、姿态、构图、背景和光线，不生成六宫格、多视角拼图、文字、字幕或水印，"
        "不解释，不使用 Markdown。"
    ),
}
APPAREL_VISUAL_PLACEHOLDERS = {
    "task_instruction": {"aspect_ratio", "resolution"},
    "fidelity_rules": set(),
    "output_protocol": set(),
}

APPAREL_SHOWCASE_BLOCKS = (
    "look_rules",
    "model_rules",
    "scene_rules",
    "phone_style_rules",
    "action_rules",
    "video_reference_rules",
    "sound_rules",
    "continuation_rules",
    "forbidden_rules",
)
APPAREL_SHOWCASE_PROVIDER_INSTRUCTION = (
    "你是专业的中文服饰视频策划师。根据服饰资料、可选模特与可选场景，生成一条可直接用于定妆图和"
    "Seedance 视频生成的中文提示词。严格按指定 JSON 输出协议返回合法 JSON 对象，不解释，不使用 Markdown。"
)
APPAREL_SHOWCASE_PROMPT_BLOCKS = {
    "look_rules": (
        "服饰原图必须作为唯一服装依据。定妆图只生成一张正面全身图，服饰类别、颜色、图案、Logo、面料、"
        "版型、长度、开合方式和工艺细节必须一致，不得增加、删除或替换单品。"
    ),
    "model_rules": (
        "优先使用用户确认的模特图片或描述；均未提供时使用默认生活化模特描述。定妆图确认后锁定脸部、发型、"
        "年龄感、肤色、体型和基础造型，视频中不得换脸、换体型或过度美颜。默认描述：{model_description}"
    ),
    "scene_rules": (
        "优先使用用户确认的场景图片或描述；均未提供时使用干净、真实、生活化默认场景。整条视频固定一个场景，"
        "不得在视频中无原因切换场景。默认描述：{scene_description}"
    ),
    "phone_style_rules": (
        "使用 iPhone 后置 1 倍主摄的真实手机实拍感：手持拍摄、自然环境光、自动曝光和对焦、轻微自然晃动。"
        "不使用棚拍灯光、三脚架、稳定器、电影运镜或电影调色。"
    ),
    "action_rules": (
        "人物自然站立、整理衣服、侧身展示、缓慢转圈、轻微走动并展示面料和细节。动作舒缓、连续、像真实"
        "穿搭博主，不使用夸张广告摆拍。"
    ),
    "video_reference_rules": (
        "视频参考图顺序固定：图片1是确认后的定妆图，决定人物、场景、构图和动作；图片2是服饰原图，仅用于"
        "校验服饰细节，不得改变图片1中的人物、场景和穿着效果。"
    ),
    "sound_rules": (
        "默认不生成声音；用户开启声音时只保留环境音、脚步声和衣料摩擦声，禁止背景音乐、旁白、对白、字幕和口播。"
    ),
    "continuation_rules": (
        "用户选择{duration}秒时，系统自动续接15秒片段。每段承接上一段的模特位置、动作方向、服饰状态、"
        "场景、光线和环境音，前端不展示分段或 cut/extend。"
    ),
    "forbidden_rules": (
        "禁止服饰变色、图案或Logo漂移、材质替换、版型变化、衣物穿插、肢体畸形、模特换脸、无原因换装、"
        "快速蒙太奇、对白、口播、旁白、字幕、水印、二维码和额外Logo。"
    ),
}
APPAREL_SHOWCASE_PLACEHOLDERS = {
    "look_rules": set(),
    "model_rules": {"model_description"},
    "scene_rules": {"scene_description"},
    "phone_style_rules": set(),
    "action_rules": set(),
    "video_reference_rules": set(),
    "sound_rules": set(),
    "continuation_rules": {"duration"},
    "forbidden_rules": set(),
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
COMMERCE_DRAMA_PROVIDER_INSTRUCTION = (
    "你是专业的中文电商短剧分镜策划师。请严格执行用户提示词，根据商品资料、角色参考和剧情要求，"
    "生成可直接用于生图和视频生成的短剧分镜方案。商品必须自然参与剧情推进，不得脱离人物动机强行植入；"
    "人物身份、外观、关系、商品状态和场景连续性必须保持稳定。严格按照指定 JSON 输出协议返回一个合法 "
    "JSON 对象，不解释，不使用 Markdown，不添加代码块或额外文本。prompt 和 videoPrompt 必须是完整可执行的"
    "生成提示词，不得省略镜头，不得进行二次概括。"
)
COMMERCE_DRAMA_PROMPT_BLOCKS = {
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
COMMERCE_DRAMA_PLACEHOLDERS = {
    "creative_direction": set(),
    "story_structure": {"segment_count"},
    "character_rules": {"character_count"},
    "dialogue_rules": {"speaker_examples"},
    "product_placement_rules": set(),
    "image_rules": {"columns", "rows", "ratio"},
    "video_rules": {"ratio"},
    "continuity_rules": set(),
    "forbidden_rules": set(),
}

TEMPLATE_DEFINITIONS = {
    PRODUCT_VISUAL_KEY: {
        "group": "image_settings",
        "group_label": "出图设置",
        "label": "商品出图",
        "status": "active",
        "order": 0,
    },
    APPAREL_VISUAL_KEY: {
        "group": "image_settings",
        "group_label": "出图设置",
        "label": "服饰试穿",
        "status": "active",
        "order": 1,
    },
    UGC_STORYBOARD_KEY: {
        "group": "commerce",
        "group_label": "电商模板",
        "label": "UGC 种草",
        "status": "active",
        "order": 2,
    },
    COMMERCE_DRAMA_KEY: {
        "group": "commerce",
        "group_label": "电商模板",
        "label": "短剧带货",
        "status": "active",
        "order": 3,
    },
    APPAREL_SHOWCASE_KEY: {
        "group": "apparel",
        "group_label": "服饰模板",
        "label": "服饰展示",
        "status": "active",
        "order": 4,
    },
}
TEMPLATE_KEYS = set(TEMPLATE_DEFINITIONS)
PRODUCT_TEMPLATE_KEYS = TEMPLATE_KEYS


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


def default_product_visual_prompt_config() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "provider_instruction": PRODUCT_VISUAL_PROVIDER_INSTRUCTION,
        "output_protocol_id": PRODUCT_VISUAL_PROTOCOL_ID,
        "prompt_blocks": deepcopy(PRODUCT_VISUAL_PROMPT_BLOCKS),
    }


def default_apparel_visual_config() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "business_instruction": "生成一张可确认服饰与模特一致性的正面全身试穿定妆图，供后续分镜和视频使用。",
        "provider_instruction": APPAREL_VISUAL_PROVIDER_INSTRUCTION,
        "output_protocol_id": APPAREL_VISUAL_PROTOCOL_ID,
        "prompt_blocks": deepcopy(APPAREL_VISUAL_PROMPT_BLOCKS),
    }


def default_commerce_drama_config() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "label": "短剧带货",
        "description": "通过剧情内容完成商品植入与转化",
        "implementation_status": "ready",
        "durations": [30, 45, 60],
        "provider_instruction": COMMERCE_DRAMA_PROVIDER_INSTRUCTION,
        "output_protocol_id": COMMERCE_DRAMA_PROTOCOL_ID,
        "prompt_blocks": deepcopy(COMMERCE_DRAMA_PROMPT_BLOCKS),
        "continuity": deepcopy(DEFAULT_CONTINUITY),
    }


def default_apparel_showcase_config() -> dict[str, Any]:
    return {
        "schema_version": 3,
        "label": "服饰视频模板",
        "description": "管理服饰定妆图与真实手机实拍视频的默认规则",
        "durations": [15, 30, 45, 60],
        "provider_instruction": APPAREL_SHOWCASE_PROVIDER_INSTRUCTION,
        "output_protocol_id": APPAREL_SHOWCASE_PROTOCOL_ID,
        "prompt_blocks": deepcopy(APPAREL_SHOWCASE_PROMPT_BLOCKS),
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
        if template.key == PRODUCT_VISUAL_KEY:
            config = template.config
            data["config"] = {
                "schema_version": config["schema_version"],
                "groups": deepcopy(config["groups"]),
                "output_protocol_id": config["output_protocol_id"],
            }
        elif template.key == APPAREL_VISUAL_KEY:
            config = template.config
            data["config"] = {
                "schema_version": config["schema_version"],
                "output_protocol_id": config["output_protocol_id"],
            }
        elif template.key == UGC_STORYBOARD_KEY:
            config = template.config
            data["config"] = {
                "schema_version": config["schema_version"],
                "templates": deepcopy(config["templates"]),
                "durations": deepcopy(config["durations"]),
                "continuity": deepcopy(config["continuity"]),
            }
        elif template.key == COMMERCE_DRAMA_KEY:
            config = template.config
            data["config"] = {
                "schema_version": config["schema_version"],
                "label": config["label"],
                "description": config["description"],
                "durations": deepcopy(config["durations"]),
                "continuity": deepcopy(config["continuity"]),
                "output_protocol_id": config["output_protocol_id"],
            }
        elif template.key == APPAREL_SHOWCASE_KEY:
            config = template.config
            data["config"] = {
                "schema_version": config["schema_version"],
                "label": config["label"],
                "description": config["description"],
                "durations": deepcopy(config["durations"]),
                "output_protocol_id": config["output_protocol_id"],
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


def _validate_prompt_block(key: str, value: Any, expected_placeholders: set[str]) -> str:
    text = _text(value, "Prompt 区块", max_length=12_000)
    if not expected_placeholders:
        if re.search(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text):
            raise ValueError(f"{key} 动态变量无效")
        return text
    try:
        placeholders = {
            field_name
            for _, field_name, _, _ in Formatter().parse(text)
            if field_name is not None
        }
    except ValueError as exc:
        raise ValueError("Prompt 动态变量格式无效") from exc
    if placeholders != expected_placeholders:
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
    blocks = value.get("prompt_blocks")
    if (
        value.get("schema_version") != 2
        or value.get("output_protocol_id") != PRODUCT_VISUAL_PROTOCOL_ID
        or not isinstance(blocks, dict)
        or set(blocks) != set(PRODUCT_VISUAL_PROMPT_BLOCKS)
    ):
        raise ValueError("商品出图模板配置无效")
    return {
        "schema_version": 2,
        "groups": result_groups,
        "business_instruction": _text(
            value.get("business_instruction", ""),
            "商品图种业务指令",
            required=False,
        ),
        "provider_instruction": _text(
            value.get("provider_instruction"), "模型角色指令", max_length=2000
        ),
        "output_protocol_id": PRODUCT_VISUAL_PROTOCOL_ID,
        "prompt_blocks": {
            key: _validate_prompt_block(
                key, blocks[key], PRODUCT_VISUAL_PLACEHOLDERS[key]
            )
            for key in PRODUCT_VISUAL_PROMPT_BLOCKS
        },
    }


def _validate_apparel_visual(value: dict[str, Any], _enabled: bool) -> dict[str, Any]:
    blocks = value.get("prompt_blocks")
    if (
        value.get("schema_version") != 2
        or value.get("output_protocol_id") != APPAREL_VISUAL_PROTOCOL_ID
        or not isinstance(blocks, dict)
        or set(blocks) != set(APPAREL_VISUAL_PROMPT_BLOCKS)
    ):
        raise ValueError("服饰试穿模板配置无效")
    return {
        "schema_version": 2,
        "business_instruction": _text(
            value.get("business_instruction", ""),
            "服饰试穿业务指令",
            required=False,
        ),
        "provider_instruction": _text(
            value.get("provider_instruction"), "模型角色指令", max_length=2000
        ),
        "output_protocol_id": APPAREL_VISUAL_PROTOCOL_ID,
        "prompt_blocks": {
            key: _validate_prompt_block(
                key, blocks[key], APPAREL_VISUAL_PLACEHOLDERS[key]
            )
            for key in APPAREL_VISUAL_PROMPT_BLOCKS
        },
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
            key: _validate_prompt_block(key, blocks[key], UGC_PLACEHOLDERS[key])
            for key in UGC_PROMPT_BLOCKS
        },
        "continuity": _validate_continuity(value.get("continuity")),
    }


def _validate_commerce_drama(value: dict[str, Any], _enabled: bool) -> dict[str, Any]:
    blocks = value.get("prompt_blocks")
    if value.get("schema_version") != 2 or not isinstance(blocks, dict) or set(blocks) != set(COMMERCE_DRAMA_BLOCKS):
        raise ValueError("短剧带货模板配置无效")
    durations = value.get("durations")
    if not isinstance(durations, list) or not durations or any(
        item not in COMMERCE_DRAMA_DURATIONS for item in durations
    ):
        raise ValueError("短剧带货时长配置无效")
    if value.get("output_protocol_id") != COMMERCE_DRAMA_PROTOCOL_ID:
        raise ValueError("短剧带货输出协议不允许修改")
    return {
        "schema_version": 2,
        "label": _text(value.get("label"), "短剧带货名称", max_length=64),
        "description": _text(value.get("description"), "短剧带货描述", max_length=255),
        "implementation_status": "ready",
        "durations": sorted(set(durations)),
        "provider_instruction": _text(
            value.get("provider_instruction"), "模型角色指令", max_length=2000
        ),
        "output_protocol_id": COMMERCE_DRAMA_PROTOCOL_ID,
        "prompt_blocks": {
            key: _validate_prompt_block(
                key, blocks[key], COMMERCE_DRAMA_PLACEHOLDERS[key]
            )
            for key in COMMERCE_DRAMA_BLOCKS
        },
        "continuity": _validate_continuity(value.get("continuity")),
    }


def _validate_apparel_showcase(value: dict[str, Any], _enabled: bool) -> dict[str, Any]:
    blocks = value.get("prompt_blocks")
    durations = value.get("durations")
    if (
        value.get("schema_version") != 3
        or value.get("output_protocol_id") != APPAREL_SHOWCASE_PROTOCOL_ID
        or not isinstance(blocks, dict)
        or set(blocks) != set(APPAREL_SHOWCASE_BLOCKS)
    ):
        raise ValueError("服饰视频模板配置无效")
    if (
        not isinstance(durations, list)
        or not durations
        or any(item not in STORYBOARD_DURATIONS for item in durations)
    ):
        raise ValueError("服饰视频时长配置无效")
    return {
        "schema_version": 3,
        "label": _text(value.get("label"), "服饰视频模板名称", max_length=64),
        "description": _text(value.get("description"), "服饰视频模板描述", max_length=255),
        "durations": sorted(set(durations)),
        "provider_instruction": _text(
            value.get("provider_instruction"), "模型角色指令", max_length=2000
        ),
        "output_protocol_id": APPAREL_SHOWCASE_PROTOCOL_ID,
        "prompt_blocks": {
            key: _validate_prompt_block(
                key, blocks[key], APPAREL_SHOWCASE_PLACEHOLDERS[key]
            )
            for key in APPAREL_SHOWCASE_BLOCKS
        },
    }


TEMPLATE_VALIDATORS: dict[str, Callable[[dict[str, Any], bool], dict[str, Any]]] = {
    PRODUCT_VISUAL_KEY: _validate_product_visual,
    APPAREL_VISUAL_KEY: _validate_apparel_visual,
    UGC_STORYBOARD_KEY: _validate_ugc,
    COMMERCE_DRAMA_KEY: _validate_commerce_drama,
    APPAREL_SHOWCASE_KEY: _validate_apparel_showcase,
}


def validate_template_config(key: str, value: Any, *, enabled: bool = False) -> dict[str, Any]:
    validator = TEMPLATE_VALIDATORS.get(key)
    if not validator or not isinstance(value, dict):
        raise ValueError("模板配置无效")
    return validator(value, enabled)


def _storyboard_grid(ratio: str) -> tuple[int, int]:
    try:
        width, height = (int(value) for value in ratio.split(":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("视频画幅比例无效") from exc
    if width <= 0 or height <= 0:
        raise ValueError("视频画幅比例无效")
    return (3, 2) if width / height <= 1 else (2, 3)


def build_product_visual_prompt(config: dict[str, Any], context: dict[str, Any]) -> str:
    validated = _validate_product_visual(config, True)
    selected_ids = context["selected_type_ids"]
    if not isinstance(selected_ids, list) or not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ValueError("商品出图类型无效")
    items = {
        item["id"]: item["label"]
        for group in validated["groups"]
        for item in group["items"]
    }
    if any(item_id not in items for item_id in selected_ids):
        raise ValueError("商品出图类型无效")
    types = "、".join(f"{item_id}={items[item_id]}" for item_id in selected_ids)
    blocks = validated["prompt_blocks"]
    prefix = blocks["task_instruction"].format(
        types=types,
        aspect_ratio=context["aspect_ratio"],
        resolution=context["resolution"],
    )
    instruction = validated["business_instruction"]
    if instruction:
        prefix += f"\n业务要求：{instruction}"
    prefix += "\n商品资料：\n"
    suffix = f"\n{blocks['output_protocol']}"
    product_context = context["product_context"]
    return f"{prefix}{product_context[:max(0, 3000 - len(prefix) - len(suffix))]}{suffix}"


def build_apparel_visual_prompt(config: dict[str, Any], context: dict[str, Any]) -> str:
    validated = _validate_apparel_visual(config, True)
    blocks = validated["prompt_blocks"]
    instruction = validated["business_instruction"]
    business_line = f"\n业务要求：{instruction}" if instruction else ""
    user_requirement = context.get("user_requirement", "").strip()
    user_line = f"\n用户补充要求：{user_requirement}" if user_requirement else ""
    model_provided = context.get("model_reference_provided")
    scene_provided = context.get("scene_reference_provided")
    if model_provided is None and scene_provided is None:
        # Older clients only supplied a positional media_urls list; preserve its model-first convention.
        model_provided = context.get("reference_count", 1) >= 2
        scene_provided = context.get("reference_count", 1) >= 3
    reference_roles = ["图片1：服饰参考图"]
    next_index = 2
    if model_provided:
        reference_roles.append(f"图片{next_index}：模特参考图")
        next_index += 1
    if scene_provided:
        reference_roles.append(f"图片{next_index}：场景参考图")
    reference_rules = (
        "参考图角色（仅可引用以下图片，禁止虚构不存在的图片）："
        + "；".join(reference_roles)
        + "。"
    )
    if model_provided:
        model_rule = "模特参考图已提供：严格保持该模特的脸部、发型、体型、肤色和身份一致。"
    elif context.get("model_description", "").strip():
        model_rule = (
            "未提供模特参考图：这是正常输入。必须依据用户的模特描述创建人物并输出可用提示词，"
            "不得声称缺少图片、无法生成或要求补充模特图。"
        )
    else:
        model_rule = (
            "未提供模特参考图：这是正常输入。必须依据服饰资料创建一位自然生活化成年模特并输出可用提示词，"
            "不得声称缺少图片、无法生成或要求补充模特图。"
        )
    task_instruction = blocks["task_instruction"]
    for legacy_prefix in (
        "图片1是服饰参考图；图片2如存在则为模特参考图，图片3如存在则为场景参考图。",
        "图片1是服饰参考图，图片2是模特参考图。",
    ):
        task_instruction = task_instruction.replace(legacy_prefix, "")
    return (
        f"{reference_rules}\n"
        f"{model_rule}\n"
        f"{task_instruction.format(aspect_ratio=context['aspect_ratio'], resolution=context['resolution'])}"
        f"{business_line}\n"
        f"服饰资料：\n{context['apparel_context']}{user_line}\n"
        f"{blocks['fidelity_rules']}\n{blocks['output_protocol']}"
    )


def build_apparel_showcase_prompt(config: dict[str, Any], context: dict[str, Any]) -> str:
    validated = _validate_apparel_showcase(config, True)
    duration = context.get("duration", 15)
    if duration not in validated["durations"]:
        raise ValueError("服饰视频时长无效")
    ratio = context["aspect_ratio"]
    blocks = validated["prompt_blocks"]
    user_requirement = context.get("user_requirement", "").strip()
    extra = f"\n用户补充要求：{user_requirement}" if user_requirement else ""
    return (
        f"生成 {ratio} 画幅、{duration} 秒服饰展示视频的提示词。\n"
        f"服饰资料：\n{context['apparel_context']}\n\n"
        f"定妆图规则：{blocks['look_rules']}\n\n"
        f"模特规则：{blocks['model_rules'].format(model_description=context.get('model_description') or '未提供，使用系统默认生活化模特')}\n\n"
        f"场景规则：{blocks['scene_rules'].format(scene_description=context.get('scene_description') or '未提供，使用系统默认生活化场景')}\n\n"
        f"手机实拍风格：{blocks['phone_style_rules']}\n\n"
        f"展示动作：{blocks['action_rules']}\n\n"
        f"视频参考规则：{blocks['video_reference_rules']}\n\n"
        f"声音规则：{blocks['sound_rules']}\n\n"
        f"连续生成规则：{blocks['continuation_rules'].format(duration=duration)}\n\n"
        f"禁止项：{blocks['forbidden_rules']}{extra}\n\n"
        '严格输出 JSON 对象，格式为 {"prompt":"完整视频提示词"}，不解释，不使用 Markdown。'
    )


def _reference_instructions(character_count: int, product_count: int) -> tuple[str, str]:
    image_characters = "，".join(
        f"图片{index + 1}是角色{index + 1}参考图" for index in range(character_count)
    )
    image_products = "、".join(
        f"图片{character_count + index + 1}" for index in range(product_count)
    )
    video_characters = "，".join(
        f"图片{index + 2}是角色{index + 1}参考图" for index in range(character_count)
    )
    video_products = "、".join(
        f"图片{character_count + index + 2}" for index in range(product_count)
    )
    image = "。".join(
        item for item in (image_characters, f"{image_products}是商品参考图") if item
    ) + "。"
    video = "，".join(
        item
        for item in ("图片1是本段分镜图", video_characters, f"{video_products}是商品参考图")
        if item
    ) + "。"
    return image, video


def _speaker_instruction(blocks: dict[str, str], character_count: int) -> str:
    if not character_count:
        return blocks["dialogue_no_character"]
    if character_count == 1:
        examples = "她说道：\"内容。\"、他说道：\"内容。\"或他回答：\"内容。\""
    else:
        examples = "、".join(
            f"角色{index + 1}{'回答' if index == 1 else '说道'}：\"内容。\""
            for index in range(character_count)
        )
    return blocks["dialogue_with_characters"].format(
        character_count=character_count,
        speaker_examples=examples,
    )


def build_ugc_storyboard_prompt(config: dict[str, Any], context: dict[str, Any]) -> str:
    validated = _validate_ugc(config, True)
    duration = context["duration"]
    if duration not in validated["durations"]:
        raise ValueError("商品分镜时长无效")
    character_count = context["character_count"]
    product_count = context["product_count"]
    if not 0 <= character_count <= 3 or not 1 <= product_count or character_count + product_count > 6:
        raise ValueError("商品分镜参考图数量无效")
    ratio = context["video_aspect_ratio"]
    columns, rows = _storyboard_grid(ratio)
    image_references, video_references = _reference_instructions(
        character_count, product_count
    )
    blocks = validated["prompt_blocks"]
    segment_count = duration // 15
    segment_rules = "\n".join(
        blocks["first_segment_rule"].format(segment=index)
        if index == 1
        else blocks["extend_segment_rule"].format(
            segment=index, previous_segment=index - 1
        )
        for index in range(1, segment_count + 1)
    )
    product_context = context["product_context"].strip() or "暂无结构化商品资料，严格以商品参考图为准。"
    user_requirement = context.get("user_requirement", "").strip()
    extra = f"\n用户补充要求：{user_requirement}" if user_requirement else ""
    schema = (
        '{"templateId":"ugc-seeding","title":"UGC 种草","globalScript":"整体内容方向",'
        '"segments":[{"segmentIndex":1,"duration":15,"shotCount":6,"plotGoal":"本段内容目标",'
        '"openingState":"开头状态","endingState":"结尾状态","continuityMode":"cut",'
        '"prompt":"镜头1：... 镜头2：... 镜头3：... 镜头4：... 镜头5：... 镜头6：...",'
        '"videoPrompt":"图片1是本段分镜图，... 镜头1：... 镜头2：... 镜头3：... 镜头4：... '
        '镜头5：... 镜头6：..."}]}'
    )
    output_contract = (
        f"严格只输出一个JSON对象，不要Markdown、解释或额外文本，格式必须符合：{schema}。"
        "templateId必须始终为“ugc-seeding”，title必须为“UGC 种草”，"
        f"segments必须恰好{segment_count}条且按顺序。每个segment的duration必须为15、shotCount必须为6、"
        "segmentIndex必须连续；第一段continuityMode必须为“cut”，后续段落只能为“extend”或“cut”。"
        "每条prompt和videoPrompt都必须完整写出镜头1、镜头2、镜头3、镜头4、镜头5、镜头6，不能合并、"
        "省略或输出空镜头。每条videoPrompt至少包含六句与镜头动作对应的自然对白或连续画外音。"
        "JSON字符串中的对白双引号必须正确转义，确保整个结果可被JSON.parse直接解析。商品结构、颜色、材质、"
        "包装和人物身份必须稳定，不得新增人物、商品或文字。"
    )
    return (
        f"{blocks['director_role']}\n\n"
        "本次输入参考图顺序：\n"
        f"生图阶段：{image_references} 生图阶段只有角色图和商品图，不包含分镜图。\n"
        f"生视频阶段：{video_references} 视频阶段图片1是刚生成的分镜图，角色和商品的身份、外观、颜色、"
        "材质、包装结构和真实尺寸以对应参考图为准。\n\n"
        "商品资料：\n"
        f"{product_context}\n\n"
        f"内容方向：{validated['business_instruction']}\n"
        f"{blocks['shooting_style']}\n\n"
        f"{_speaker_instruction(blocks, character_count)}\n\n"
        f"{blocks['image_rules'].format(columns=columns, rows=rows, ratio=ratio)}\n\n"
        f"{blocks['video_rules'].format(ratio=ratio)}\n\n"
        f"{segment_rules}{extra}\n\n"
        f"{output_contract}"
    )


def build_commerce_drama_prompt(config: dict[str, Any], context: dict[str, Any]) -> str:
    validated = _validate_commerce_drama(config, True)
    duration = context["duration"]
    if duration not in validated["durations"]:
        raise ValueError("短剧带货时长无效")
    character_count = context["character_count"]
    product_count = context["product_count"]
    if not 0 <= character_count <= 3 or not 1 <= product_count or character_count + product_count > 6:
        raise ValueError("短剧带货参考图数量无效")
    ratio = context["video_aspect_ratio"]
    columns, rows = _storyboard_grid(ratio)
    image_references, video_references = _reference_instructions(character_count, product_count)
    segment_count = duration // 15
    if not character_count:
        speaker_examples = "人物A说道：\"内容。\"、画外音说道：\"内容。\""
    else:
        speaker_examples = "、".join(
            f"角色{index + 1}{'回答' if index == 1 else '说道'}：\"内容。\""
            for index in range(character_count)
        )
    blocks = validated["prompt_blocks"]
    product_context = context["product_context"].strip() or "暂无结构化商品资料，严格以商品参考图为准。"
    user_requirement = context.get("user_requirement", "").strip()
    extra = f"\n用户补充要求：{user_requirement}" if user_requirement else ""
    schema = (
        '{"templateId":"commerce-drama","title":"短剧标题","globalScript":"完整剧情方向和人物关系",'
        f'"totalDuration":{duration},"characters":[{{"characterIndex":1,"name":"角色名称",'
        '"role":"剧情身份","goal":"人物目标","relationship":"人物关系"}}],'
        '"segments":[{"segmentIndex":1,"duration":15,"shotCount":6,"plotGoal":"本段剧情目标",'
        '"dramaticBeat":"冲突、转折或结果","productPlacement":"商品如何参与剧情",'
        '"openingState":"开头状态","endingState":"结尾状态","continuityMode":"cut",'
        '"prompt":"镜头1：... 镜头2：... 镜头3：... 镜头4：... 镜头5：... 镜头6：...",'
        '"videoPrompt":"图片1是本段分镜图，... 镜头1：... 镜头2：... 镜头3：... 镜头4：... '
        '镜头5：... 镜头6：..."}]}'
    )
    output_contract = (
        f"严格只输出一个JSON对象，不要Markdown、解释或额外文本，格式必须符合：{schema}。"
        "templateId必须始终为“commerce-drama”，characters必须描述本次剧情实际使用的角色；"
        f"segments必须恰好{segment_count}条且按顺序，每条duration必须为15、shotCount必须为6。"
        "第一段continuityMode必须为“cut”，后续只能为“cut”或“extend”。每条prompt和videoPrompt必须"
        "完整写出镜头1至镜头6；dramaticBeat和productPlacement不能为空。JSON字符串内的对白双引号必须"
        "正确转义，确保结果可被JSON.parse直接解析。不得新增未提供的指定角色、商品或商品功效。"
    )
    return (
        "本次输入参考图顺序：\n"
        f"生图阶段：{image_references} 生图阶段只有角色图和商品图，不包含分镜图。\n"
        f"生视频阶段：{video_references} 视频阶段图片1是刚生成的分镜图，角色和商品的身份、外观、颜色、"
        "材质、包装结构和真实尺寸以对应参考图为准。\n\n"
        "商品资料：\n"
        f"{product_context}\n\n"
        f"创作方向：{blocks['creative_direction']}\n\n"
        f"剧情结构：{blocks['story_structure'].format(segment_count=segment_count)}\n\n"
        f"角色规则：{blocks['character_rules'].format(character_count=character_count)}\n\n"
        f"对白规则：{blocks['dialogue_rules'].format(speaker_examples=speaker_examples)}\n\n"
        f"商品植入：{blocks['product_placement_rules']}\n\n"
        f"生图规则：{blocks['image_rules'].format(columns=columns, rows=rows, ratio=ratio)}\n\n"
        f"视频规则：{blocks['video_rules'].format(ratio=ratio)}\n\n"
        f"连续性规则：{blocks['continuity_rules']}\n\n"
        f"禁止项：{blocks['forbidden_rules']}{extra}\n\n"
        f"{output_contract}"
    )


TEMPLATE_BUILDERS = {
    PRODUCT_VISUAL_KEY: build_product_visual_prompt,
    APPAREL_VISUAL_KEY: build_apparel_visual_prompt,
    UGC_STORYBOARD_KEY: build_ugc_storyboard_prompt,
    COMMERCE_DRAMA_KEY: build_commerce_drama_prompt,
    APPAREL_SHOWCASE_KEY: build_apparel_showcase_prompt,
}
