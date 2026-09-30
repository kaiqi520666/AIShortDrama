from types import SimpleNamespace

import pytest

from app.services.capability_validation import (
    CapabilityConfigurationError,
    validate_model_configuration,
)


def setting(media_type, model_id, *, enabled=True, is_default=False):
    return SimpleNamespace(media_type=media_type, model_id=model_id, enabled=enabled, is_default=is_default)


def test_model_configuration_requires_one_default_per_media_type():
    settings = [
        setting("text", "gpt-5.6-sol", is_default=True),
        setting("image", "gpt-image-2", is_default=True),
        setting("video", "seedance-2-mini", is_default=True),
        setting("audio", "seed-audio-1.0-multilingual", is_default=True),
    ]
    validate_model_configuration(settings)

    with pytest.raises(CapabilityConfigurationError, match="image"):
        validate_model_configuration([item for item in settings if item.media_type != "image"])


def test_model_configuration_rejects_unknown_models_and_missing_prices():
    settings = [
        setting("text", "gpt-5.6-sol", is_default=True),
        setting("text", "unknown", is_default=True),
        setting("image", "gpt-image-2", is_default=True),
        setting("video", "seedance-2-mini", is_default=True),
        setting("audio", "seed-audio-1.0-multilingual", is_default=True),
    ]
    with pytest.raises(CapabilityConfigurationError, match="不存在"):
        validate_model_configuration(settings)

    settings = [item for item in settings if item.model_id != "unknown"]
    with pytest.raises(CapabilityConfigurationError, match="缺少价格"):
        validate_model_configuration(settings, [])
