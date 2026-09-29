import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from app.services.content_templates import (
    APPAREL_SHOWCASE_KEY,
    APPAREL_VISUAL_KEY,
    COMMERCE_DRAMA_KEY,
    PRODUCT_VISUAL_GROUPS,
    PRODUCT_VISUAL_KEY,
    UGC_STORYBOARD_KEY,
    build_apparel_showcase_prompt,
    build_apparel_visual_prompt,
    build_commerce_drama_prompt,
    build_product_visual_prompt,
    build_ugc_storyboard_prompt,
    default_apparel_showcase_config,
    default_apparel_visual_config,
    default_commerce_drama_config,
    default_product_visual_prompt_config,
    default_ugc_config,
    validate_template_config,
)


ROOT_DIR = Path(__file__).resolve().parents[2]


def load_template_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "j2c4e6f8a0b1_expand_content_templates.py"
    )
    spec = importlib.util.spec_from_file_location("ugc_template_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_commerce_drama_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "k3d5f7a9b1c2_enable_commerce_drama.py"
    )
    spec = importlib.util.spec_from_file_location("commerce_drama_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_product_visual_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "n5f7h9j1l3m4_migrate_product_visual_prompt.py"
    )
    spec = importlib.util.spec_from_file_location("product_visual_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_apparel_visual_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "q7h9j1l3n5o6_simplify_apparel_try_on.py"
    )
    spec = importlib.util.spec_from_file_location("apparel_visual_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_apparel_reference_instruction_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "s9k1m3o5q7r8_fix_apparel_reference_instruction.py"
    )
    spec = importlib.util.spec_from_file_location("apparel_reference_instruction_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_apparel_optional_model_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "t1v3x5z7b9c0_fix_apparel_optional_model_copy.py"
    )
    spec = importlib.util.spec_from_file_location("apparel_optional_model_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def product_visual_config():
    group_labels = {
        "basic": "基础展示",
        "marketing": "营销卖点",
        "detail": "详情说明",
        "trust": "信任保障",
    }
    item_labels = {
        "white-bg": "白底图",
        "first-screen": "首屏主视觉",
        "multi-angle": "多角度",
        "series-show": "系列 SKU",
        "core-selling": "核心卖点",
        "use-scenario": "使用场景",
        "ambient-scene": "氛围场景",
        "contrast-effect": "效果对比",
        "detail-zoom": "细节图",
        "specs-info": "规格尺寸",
        "tech-specs": "参数表",
        "manufacturing": "工艺",
        "ingredients": "成分",
        "brand-story": "品牌故事",
        "freebies": "配件 / 赠品",
        "warranty": "售后保障",
        "usage-tips": "使用建议",
    }
    return {
        **default_product_visual_prompt_config(),
        "groups": [
            {
                "id": group_id,
                "label": group_labels[group_id],
                "items": [
                    {
                        "id": item_id,
                        "label": item_labels[item_id],
                        "default_enabled": item_id == "white-bg",
                    }
                    for item_id in item_ids
                ],
            }
            for group_id, item_ids in PRODUCT_VISUAL_GROUPS.items()
        ],
        "business_instruction": "",
    }


def test_product_visual_migration_preserves_operator_fields_and_is_idempotent():
    migration = load_product_visual_migration()
    existing = {
        "groups": [{"id": "custom", "label": "已调整", "items": []}],
        "business_instruction": "已验证业务要求",
    }

    merged = migration.merge_product_visual_config(existing)

    assert merged["groups"] == existing["groups"]
    assert merged["business_instruction"] == "已验证业务要求"
    assert merged["provider_instruction"] == migration.PROVIDER_INSTRUCTION
    assert merged["prompt_blocks"] == migration.PROMPT_BLOCKS
    assert migration.merge_product_visual_config(merged) == merged


def test_apparel_visual_migration_preserves_operator_fields_and_is_idempotent():
    migration = load_apparel_visual_migration()
    existing = {
        "schema_version": 1,
        "groups": [{"id": "views", "items": migration.OLD_VIEWS}],
        "selected_view_ids": ["front", "back"],
        "business_instruction": "已验证试穿要求",
        "prompt_blocks": {"fidelity_rules": "已验证服饰保真规则"},
    }

    merged = migration.simplify_apparel_visual_config(existing)

    assert merged["schema_version"] == 2
    assert merged["output_protocol_id"] == "apparel-visual-v2"
    assert merged["business_instruction"] == "已验证试穿要求"
    assert merged["prompt_blocks"]["fidelity_rules"] == "已验证服饰保真规则"
    assert "groups" not in merged
    assert "selected_view_ids" not in merged
    assert migration.simplify_apparel_visual_config(merged) == merged

    defaults = migration.simplify_apparel_visual_config({
        "business_instruction": migration.OLD_BUSINESS_INSTRUCTION,
        "prompt_blocks": {"fidelity_rules": migration.OLD_FIDELITY_RULES},
    })
    assert defaults["business_instruction"] == migration.BUSINESS_INSTRUCTION
    assert defaults["prompt_blocks"]["fidelity_rules"] == migration.FIDELITY_RULES


def test_apparel_reference_instruction_migration_only_replaces_known_fixed_copy():
    migration = load_apparel_reference_instruction_migration()
    assert migration.TASK_INSTRUCTION.startswith("请根据下方明确列出的参考图角色")
    assert any("图片2是模特参考图" in value for value in migration.OLD_PREFIXES)


def test_apparel_optional_model_migration_only_targets_system_defaults():
    migration = load_apparel_optional_model_migration()
    assert "模特参考图可选" in migration.TASK_INSTRUCTION
    assert "不得以缺少图片或无法保持一致为由拒绝生成" in migration.PROVIDER_INSTRUCTION


def test_product_visual_builder_matches_accepted_frontend_prompt_byte_for_byte():
    config = product_visual_config()
    context = {
        "product_context": "商品名称：测试商品",
        "selected_type_ids": ["white-bg", "core-selling"],
        "aspect_ratio": "16:9",
        "resolution": "2K",
        "reference_count": 2,
    }
    expected = (
        "请根据参考商品图片和商品资料，为以下图种分别生成一条中文图片提示词："
        "white-bg=白底图、core-selling=核心卖点。统一画面规格：16:9，2K。\n"
        "商品资料：\n商品名称：测试商品\n"
        '严格输出 JSON 数组，格式为 [{"type":"图种ID","prompt":"提示词"}]。'
        "每个图种必须且只能出现一次，顺序与请求一致。每条提示词不超过 100 个中文字符，只描述该图种"
        "特有的构图、场景、光线、视角与文案布局，不重复商品资料，不虚构图片和资料中没有的商品事实，"
        "不解释，不使用 Markdown。"
    )

    assert build_product_visual_prompt(config, context) == expected


def test_product_visual_validation_rejects_changed_placeholders():
    config = product_visual_config()
    config["prompt_blocks"]["task_instruction"] = config["prompt_blocks"][
        "task_instruction"
    ].replace("{types}", "{unknown}")
    with pytest.raises(ValueError, match="动态变量"):
        validate_template_config(PRODUCT_VISUAL_KEY, config, enabled=True)


def test_ugc_template_migration_preserves_existing_operator_fields():
    migration = load_template_migration()
    existing = {
        "templates": [
            {
                "id": "ugc-seeding",
                "label": "自定义 UGC",
                "description": "已经运营调整",
                "enabled": False,
            }
        ],
        "durations": [15, 45],
        "business_instruction": "已验证的运营指令",
    }

    merged = migration.merge_ugc_config(existing)

    assert merged["templates"] == existing["templates"]
    assert merged["durations"] == [15, 45]
    assert merged["business_instruction"] == "已验证的运营指令"
    assert merged["schema_version"] == 2
    assert merged["prompt_blocks"] == migration.UGC_PROMPT_BLOCKS
    assert migration.merge_ugc_config(merged) == merged


def test_ugc_template_validation_rejects_changed_placeholders():
    config = default_ugc_config()
    validated = validate_template_config(UGC_STORYBOARD_KEY, config, enabled=True)
    assert validated == config

    config["prompt_blocks"]["image_rules"] = config["prompt_blocks"][
        "image_rules"
    ].replace("{ratio}", "{unknown}")
    with pytest.raises(ValueError, match="动态变量"):
        validate_template_config(UGC_STORYBOARD_KEY, config, enabled=True)


def test_backend_ugc_builder_matches_accepted_frontend_prompt_byte_for_byte():
    golden = json.loads(
        (ROOT_DIR / "contracts" / "ugc-storyboard-v1-golden.json").read_text(
            encoding="utf-8"
        )
    )
    config = default_ugc_config()
    for item in golden["cases"]:
        prompt = build_ugc_storyboard_prompt(config, item)
        assert len(prompt) == item["length"], item["name"]
        assert hashlib.sha256(prompt.encode()).hexdigest() == item["sha256"], item["name"]


@pytest.mark.parametrize("drama", [False, True])
def test_indonesian_storyboard_contract(drama):
    config = default_commerce_drama_config() if drama else default_ugc_config()
    builder = build_commerce_drama_prompt if drama else build_ugc_storyboard_prompt
    prompt = builder(config, {
        "locale": "id", "product_context": "Kopi", "duration": 30,
        "video_aspect_ratio": "9:16", "character_count": 1, "product_count": 1,
        "user_requirement": "Dapur terang",
    })
    assert "Bahasa keluaran wajib bahasa Indonesia" in prompt
    assert "Adegan 6" in prompt
    assert "Gambar 3: produk 1" in prompt
    assert "tepat 2 segmen" in prompt
    assert "Dapur terang" in prompt
    assert ("commerce-drama" if drama else "ugc-seeding") in prompt


def test_commerce_drama_migration_preserves_operator_blocks_and_is_idempotent():
    migration = load_commerce_drama_migration()
    existing = {
        "label": "自定义短剧",
        "description": "已验证描述",
        "durations": [45, 60],
        "prompt_blocks": {"creative_direction": "自定义创作方向"},
    }
    merged = migration.merge_commerce_drama_config(existing)

    assert merged["label"] == "自定义短剧"
    assert merged["description"] == "已验证描述"
    assert merged["durations"] == [45, 60]
    assert merged["prompt_blocks"]["creative_direction"] == "自定义创作方向"
    assert merged["prompt_blocks"]["story_structure"]
    assert merged["implementation_status"] == "ready"
    assert migration.merge_commerce_drama_config(merged) == merged


def test_commerce_drama_template_is_valid_and_builds_complete_prompt():
    config = default_commerce_drama_config()
    config["prompt_blocks"]["creative_direction"] = "围绕剧情冲突自然植入商品"
    validated = validate_template_config(COMMERCE_DRAMA_KEY, config, enabled=True)
    assert validated["prompt_blocks"]["creative_direction"] == "围绕剧情冲突自然植入商品"
    prompt = build_commerce_drama_prompt(
        config,
        {
            "product_context": "商品名称：测试商品",
            "duration": 30,
            "video_aspect_ratio": "9:16",
            "character_count": 1,
            "product_count": 1,
            "user_requirement": "家庭场景",
        },
    )
    assert "全片共2个15秒剧情段落" in prompt
    assert "图片1是角色1参考图" in prompt
    assert '"templateId":"commerce-drama"' in prompt
    assert "dramaticBeat" in prompt
    assert "用户补充要求：家庭场景" in prompt


def test_commerce_drama_validation_rejects_changed_protocol_or_placeholders():
    config = default_commerce_drama_config()
    config["output_protocol_id"] = "changed"
    with pytest.raises(ValueError, match="输出协议"):
        validate_template_config(COMMERCE_DRAMA_KEY, config, enabled=True)

    config = default_commerce_drama_config()
    config["prompt_blocks"]["story_structure"] = "共{unknown}段"
    with pytest.raises(ValueError, match="动态变量"):
        validate_template_config(COMMERCE_DRAMA_KEY, config, enabled=True)


def test_apparel_visual_builder_creates_one_server_prompt():
    config = default_apparel_visual_config()
    validated = validate_template_config(APPAREL_VISUAL_KEY, config, enabled=True)
    prompt = build_apparel_visual_prompt(validated, {
        "apparel_context": "单品1：白色衬衫（面料：棉）",
        "aspect_ratio": "9:16",
        "resolution": "1K",
        "reference_count": 2,
        "user_requirement": "自然日光",
    })
    assert "一张正面全身试穿定妆图" in prompt
    assert "图片1：服饰参考图；图片2：模特参考图" in prompt
    assert "用户补充要求：自然日光" in prompt
    assert '"prompt":"图片提示词"' in prompt
    assert "不生成六宫格、多视角拼图" in prompt


def test_apparel_visual_builder_does_not_invent_missing_references():
    config = validate_template_config(APPAREL_VISUAL_KEY, default_apparel_visual_config(), enabled=True)
    prompt = build_apparel_visual_prompt(config, {
        "apparel_context": "单品1：粉色连衣裙",
        "aspect_ratio": "9:16",
        "resolution": "1K",
        "reference_count": 1,
        "model_reference_provided": False,
        "scene_reference_provided": False,
    })
    assert "参考图角色（仅可引用以下图片，禁止虚构不存在的图片）：图片1：服饰参考图。" in prompt
    assert "图片2：模特参考图" not in prompt
    assert "图片3：场景参考图" not in prompt
    assert "图片2如存在则为模特参考图" not in prompt
    assert "这是正常输入" in prompt
    assert "创建一位自然生活化成年模特" in prompt
    assert "不得声称缺少图片、无法生成或要求补充模特图" in prompt


def test_apparel_showcase_builder_creates_video_prompt_contract():
    config = default_apparel_showcase_config()
    validated = validate_template_config(APPAREL_SHOWCASE_KEY, config, enabled=True)
    prompt = build_apparel_showcase_prompt(validated, {
        "apparel_context": "单品1：白色衬衫",
        "duration": 60,
        "aspect_ratio": "9:16",
        "user_requirement": "最后在街景收尾",
    })
    assert "生成 9:16 画幅、60 秒服饰展示视频的提示词" in prompt
    assert "图片1是确认后的定妆图" in prompt
    assert "图片2是服饰原图" in prompt
    assert "iPhone 后置 1 倍主摄" in prompt
    assert "缓慢转圈" in prompt
    assert "用户补充要求：最后在街景收尾" in prompt
