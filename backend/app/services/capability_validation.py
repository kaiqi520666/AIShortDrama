from typing import Any

from app.core.model_capabilities import MODEL_CAPABILITIES


class CapabilityConfigurationError(ValueError):
    pass


def validate_model_configuration(
    settings: list[Any],
    price_rules: list[Any] | None = None,
) -> None:
    setting_index = {(item.media_type, item.model_id): item for item in settings}
    if len(setting_index) != len(settings):
        raise CapabilityConfigurationError("模型后台配置存在重复记录")

    for media_type, capability in MODEL_CAPABILITIES.items():
        model_ids = {model["id"] for model in capability["models"]}
        enabled = [
            item
            for item in settings
            if item.media_type == media_type and item.model_id in model_ids and item.enabled
        ]
        defaults = [item for item in enabled if item.is_default]
        if not enabled:
            raise CapabilityConfigurationError(f"{media_type} 没有启用模型")
        if len(defaults) != 1:
            raise CapabilityConfigurationError(f"{media_type} 必须有且只有一个默认模型")

    for item in settings:
        if item.media_type not in MODEL_CAPABILITIES:
            raise CapabilityConfigurationError(f"模型配置不存在: {item.media_type}/{item.model_id}")
        model_ids = {model["id"] for model in MODEL_CAPABILITIES[item.media_type]["models"]}
        if item.model_id not in model_ids:
            raise CapabilityConfigurationError(f"模型配置不存在: {item.media_type}/{item.model_id}")

    if price_rules is not None:
        prices = {
            (item.media_type, item.model, item.specification)
            for item in price_rules
            if item.enabled
        }
        for item in settings:
            if not item.enabled:
                continue
            capability = next(
                model
                for model in MODEL_CAPABILITIES[item.media_type]["models"]
                if model["id"] == item.model_id
            )
            specifications = capability.get("resolutions") or [""]
            if not any(
                (item.media_type, item.model_id, specification) in prices
                for specification in specifications
            ):
                raise CapabilityConfigurationError(
                    f"模型缺少价格规则: {item.media_type}/{item.model_id}"
                )
