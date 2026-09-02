from copy import deepcopy
from typing import Any


CAPABILITIES_VERSION = 1

MODEL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "text": {
        "default_model": "gpt-5.6-sol",
        "models": [
            {
                "id": "gpt-5.6-sol",
                "label": "GPT-5.6 Sol",
                "prompt_max_length": 3000,
            }
        ],
    },
    "image": {
        "default_model": "gpt-image-2",
        "models": [
            {
                "id": "gpt-image-2",
                "label": "GPT Image 2",
                "resolutions": ["1K", "2K", "4K"],
                "aspect_ratios": ["1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21"],
                "default_resolution": "1K",
                "default_aspect_ratio": "1:1",
                "prompt_max_length": 32000,
                "reference_limits": {"image": 6},
                "search": {"google": False, "google_image": False},
                "_provider_format": "openai_image",
            },
            {
                "id": "doubao-seedream-5-0-pro",
                "label": "Seedream 5.0 Pro",
                "resolutions": ["1K", "2K"],
                "aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "9:21"],
                "default_resolution": "2K",
                "default_aspect_ratio": "16:9",
                "prompt_max_length": 32000,
                "reference_limits": {"image": 10},
                "search": {"google": False, "google_image": False},
                "_disable_watermark": True,
            },
            {
                "id": "doubao-seedream-5-0",
                "label": "Seedream 5.0",
                "resolutions": ["2K", "3K"],
                "aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "9:21"],
                "default_resolution": "2K",
                "default_aspect_ratio": "16:9",
                "prompt_max_length": 32000,
                "reference_limits": {"image": 10},
                "search": {"google": False, "google_image": False},
                "_disable_watermark": True,
            },
            {
                "id": "gemini-3-pro-image-preview",
                "label": "Gemini 3 Pro",
                "resolutions": ["1K", "2K", "4K"],
                "aspect_ratios": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                "default_resolution": "1K",
                "default_aspect_ratio": "16:9",
                "prompt_max_length": 32000,
                "reference_limits": {"image": 14},
                "search": {"google": False, "google_image": False},
            },
            {
                "id": "gemini-3.1-flash-image-preview",
                "label": "Gemini 3.1 Flash",
                "resolutions": ["1K", "2K", "4K"],
                "aspect_ratios": ["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "5:4", "4:5", "21:9", "1:4", "4:1", "1:8", "8:1"],
                "default_resolution": "1K",
                "default_aspect_ratio": "16:9",
                "prompt_max_length": 32000,
                "reference_limits": {"image": 14},
                "search": {"google": True, "google_image": True},
            },
        ],
    },
    "video": {
        "default_model": "seedance-2-mini",
        "models": [
            {
                "id": "seedance-2",
                "label": "Seedance 2",
                "resolutions": ["480p", "720p", "1080p", "4k"],
                "aspect_ratios": ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"],
                "default_resolution": "720p",
                "default_aspect_ratio": "16:9",
                "default_duration": 5,
                "duration": {"min": 4, "max": 15},
                "prompt_max_length": 32000,
                "reference_limits": {"image": 9, "video": 3, "audio": 3},
                "generate_audio": True,
                "requires_private_asset": True,
                "return_last_frame": True,
            },
            {
                "id": "seedance-2-fast",
                "label": "Seedance 2 Fast",
                "resolutions": ["480p", "720p"],
                "aspect_ratios": ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"],
                "default_resolution": "720p",
                "default_aspect_ratio": "16:9",
                "default_duration": 5,
                "duration": {"min": 4, "max": 15},
                "prompt_max_length": 32000,
                "reference_limits": {"image": 9, "video": 3, "audio": 3},
                "generate_audio": True,
                "requires_private_asset": True,
                "return_last_frame": True,
            },
            {
                "id": "seedance-2-mini",
                "label": "Seedance 2 Mini",
                "resolutions": ["480p", "720p"],
                "aspect_ratios": ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"],
                "default_resolution": "720p",
                "default_aspect_ratio": "16:9",
                "default_duration": 10,
                "duration": {"min": 4, "max": 15},
                "prompt_max_length": 32000,
                "reference_limits": {"image": 9, "video": 3, "audio": 3},
                "generate_audio": True,
                "requires_private_asset": True,
                "return_last_frame": True,
            },
        ],
    },
    "audio": {
        "default_model": "seed-audio-1.0-multilingual",
        "models": [
            {
                "id": "seed-audio-1.0-multilingual",
                "label": "Seed Audio 1.0",
                "prompt_max_length": 3000,
                "formats": ["mp3", "wav", "ogg_opus"],
                "sample_rates": [8000, 16000, 24000, 32000, 44100, 48000],
                "defaults": {"format": "mp3", "sample_rate": 48000},
                "parameters": {
                    "speech_rate": {"min": -50, "max": 100, "default": 0},
                    "loudness_rate": {"min": -50, "max": 100, "default": 0},
                    "pitch_rate": {"min": -12, "max": 12, "default": 0},
                },
                "reference_limits": {"image": 1, "audio": 3},
                "reference_audio_max_seconds": 30,
                "reference_max_bytes": 10 * 1024 * 1024,
            }
        ],
    },
}


def get_model_capability(media_type: str, model_id: str) -> dict[str, Any]:
    media = MODEL_CAPABILITIES.get(media_type)
    if not media:
        raise ValueError(f"不支持的生成类型 {media_type}")
    model = next((item for item in media["models"] if item["id"] == model_id), None)
    if not model:
        raise ValueError(f"不支持的{media_type}模型 {model_id}")
    return model


def get_default_model(media_type: str) -> str:
    media = MODEL_CAPABILITIES.get(media_type)
    if not media:
        raise ValueError(f"不支持的生成类型 {media_type}")
    return media["default_model"]


def capabilities_payload(capabilities: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    def public_value(value):
        if isinstance(value, dict):
            return {
                key: public_value(item)
                for key, item in value.items()
                if not key.startswith("_")
            }
        if isinstance(value, list):
            return [public_value(item) for item in value]
        return value

    return {
        "version": CAPABILITIES_VERSION,
        **public_value(deepcopy(capabilities or MODEL_CAPABILITIES)),
    }
