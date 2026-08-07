import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from app.services.content_templates import (
    COMMERCE_DRAMA_KEY,
    UGC_STORYBOARD_KEY,
    default_commerce_drama_config,
    default_ugc_config,
    build_ugc_storyboard_prompt,
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


def test_commerce_drama_template_is_editable_but_cannot_be_enabled():
    config = default_commerce_drama_config()
    config["prompt_blocks"]["creative_direction"] = "围绕剧情冲突自然植入商品"
    validated = validate_template_config(COMMERCE_DRAMA_KEY, config, enabled=False)
    assert validated["prompt_blocks"]["creative_direction"] == "围绕剧情冲突自然植入商品"

    with pytest.raises(ValueError, match="暂时不能启用"):
        validate_template_config(COMMERCE_DRAMA_KEY, config, enabled=True)
