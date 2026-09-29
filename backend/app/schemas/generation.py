import uuid
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.model_capabilities import get_default_model, get_model_capability
from app.core.generation_locale import GenerationLocale

DEFAULT_IMAGE_CAPABILITY = get_model_capability("image", get_default_model("image"))
DEFAULT_AUDIO_CAPABILITY = get_model_capability("audio", get_default_model("audio"))


def validate_prompt(value: str, media_label: str) -> str:
    if not value.strip():
        raise ValueError(f"{media_label}提示词不能为空")
    return value.strip()


def validate_prompt_length(prompt: str, model: str, rules: dict) -> None:
    if len(prompt) > rules["prompt_max_length"]:
        raise ValueError(f"{model} 提示词不能超过 {rules['prompt_max_length']} 字符")


class TextGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    locale: GenerationLocale = "zh-CN"

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: str
    prompt: str = Field(min_length=1)

    @field_validator("prompt")
    @classmethod
    def validate_text_prompt(cls, value: str) -> str:
        return validate_prompt(value, "文本")

    @model_validator(mode="after")
    def validate_model_options(self):
        rules = get_model_capability("text", self.model)
        validate_prompt_length(self.prompt, self.model, rules)
        return self


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: str
    prompt: str = Field(min_length=1)
    size: str = DEFAULT_IMAGE_CAPABILITY["default_aspect_ratio"]
    n: Literal[1] = 1
    resolution: str | None = None
    reference_images: list[AnyHttpUrl] = Field(default_factory=list)
    google_search: bool = False
    google_image_search: bool = False

    @field_validator("prompt")
    @classmethod
    def validate_image_prompt(cls, value: str) -> str:
        return validate_prompt(value, "图片")

    @model_validator(mode="after")
    def validate_model_options(self):
        rules = get_model_capability("image", self.model)
        validate_prompt_length(self.prompt, self.model, rules)
        if self.size not in rules["aspect_ratios"]:
            raise ValueError(f"{self.model} 不支持比例 {self.size}")
        if self.resolution and self.resolution not in rules["resolutions"]:
            raise ValueError(f"{self.model} 不支持分辨率 {self.resolution}")
        max_references = rules["reference_limits"]["image"]
        if len(self.reference_images) > max_references:
            raise ValueError(f"{self.model} 参考图片不能超过 {max_references} 张")
        search = rules["search"]
        if self.google_search and not search["google"]:
            raise ValueError(f"{self.model} 不支持搜索增强")
        if self.google_image_search and not search["google_image"]:
            raise ValueError(f"{self.model} 不支持图片搜索增强")
        if self.google_image_search and not self.google_search:
            raise ValueError("google_image_search 需要同时启用 google_search")
        return self


class VideoGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: str
    prompt: str = Field(min_length=1)
    duration: int
    resolution: str
    aspect_ratio: str
    generate_audio: bool | None = None
    return_last_frame: bool = False
    reference_images: list[str] = Field(default_factory=list)
    reference_videos: list[AnyHttpUrl] = Field(default_factory=list)
    reference_audios: list[AnyHttpUrl] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def validate_video_prompt(cls, value: str) -> str:
        return validate_prompt(value, "视频")

    @field_validator("reference_images")
    @classmethod
    def validate_reference_images(cls, values: list[str]) -> list[str]:
        for value in values:
            if value.startswith("asset://") and len(value) > len("asset://"):
                continue
            try:
                AnyHttpUrl(value)
            except ValueError as exc:
                raise ValueError("参考图片必须是公开 URL 或 Seedance 素材地址") from exc
        return values

    @model_validator(mode="after")
    def validate_model_options(self):
        rules = get_model_capability("video", self.model)
        validate_prompt_length(self.prompt, self.model, rules)
        if self.resolution not in rules["resolutions"]:
            raise ValueError(f"{self.model} 不支持分辨率 {self.resolution}")
        if self.aspect_ratio not in rules["aspect_ratios"]:
            raise ValueError(f"{self.model} 不支持比例 {self.aspect_ratio}")
        duration = rules["duration"]
        valid_duration = self.duration in duration.get("options", []) or (
            duration["min"] <= self.duration <= duration["max"]
            if "min" in duration
            else False
        )
        if not valid_duration:
            raise ValueError(f"{self.model} 不支持时长 {self.duration}")
        if self.generate_audio is not None and not rules["generate_audio"]:
            raise ValueError(f"{self.model} 不支持音频生成参数")
        limits = rules["reference_limits"]
        reference_groups = (
            (self.reference_images, "image", "图片"),
            (self.reference_videos, "video", "视频"),
            (self.reference_audios, "audio", "音频"),
        )
        for values, media_type, label in reference_groups:
            if len(values) > limits[media_type]:
                raise ValueError(f"{self.model} 参考{label}不能超过 {limits[media_type]} 个")
        if self.reference_audios and not (self.reference_images or self.reference_videos):
            raise ValueError("参考音频需同时提供图片或视频")
        return self


class AudioGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: str = get_default_model("audio")
    prompt: str = Field(min_length=1)
    format: str = DEFAULT_AUDIO_CAPABILITY["defaults"]["format"]
    sample_rate: int = DEFAULT_AUDIO_CAPABILITY["defaults"]["sample_rate"]
    speech_rate: int = DEFAULT_AUDIO_CAPABILITY["parameters"]["speech_rate"]["default"]
    loudness_rate: int = DEFAULT_AUDIO_CAPABILITY["parameters"]["loudness_rate"]["default"]
    pitch_rate: int = DEFAULT_AUDIO_CAPABILITY["parameters"]["pitch_rate"]["default"]
    reference_images: list[AnyHttpUrl] = Field(default_factory=list)
    reference_audios: list[AnyHttpUrl] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def validate_audio_prompt(cls, value: str) -> str:
        return validate_prompt(value, "音频")

    @model_validator(mode="after")
    def validate_model_options(self):
        rules = get_model_capability("audio", self.model)
        validate_prompt_length(self.prompt, self.model, rules)
        if self.format not in rules["formats"]:
            raise ValueError(f"{self.model} 不支持音频格式 {self.format}")
        if self.sample_rate not in rules["sample_rates"]:
            raise ValueError(f"{self.model} 不支持采样率 {self.sample_rate}")
        for field in ("speech_rate", "loudness_rate", "pitch_rate"):
            value = getattr(self, field)
            bounds = rules["parameters"][field]
            if not bounds["min"] <= value <= bounds["max"]:
                raise ValueError(f"{field} 必须在 {bounds['min']} 到 {bounds['max']} 之间")
        limits = rules["reference_limits"]
        if len(self.reference_images) > limits["image"]:
            raise ValueError(f"参考图片不能超过 {limits['image']} 张")
        if len(self.reference_audios) > limits["audio"]:
            raise ValueError(f"参考音频不能超过 {limits['audio']} 条")
        if self.reference_images and self.reference_audios:
            raise ValueError("参考图片和参考音频不能混用")
        return self
