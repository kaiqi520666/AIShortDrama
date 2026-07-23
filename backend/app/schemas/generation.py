import uuid
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


ImageModel = Literal[
    "gpt-image-2",
    "doubao-seedream-5-0-pro",
    "doubao-seedream-5-0",
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
]

VideoModel = Literal[
    "seedance-2",
    "seedance-2-fast",
    "seedance-2-mini",
    "happyhorse-1.1",
]

SEEDANCE_RATIOS = {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"}
HAPPYHORSE_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4"}
VIDEO_MODEL_RULES: dict[str, dict[str, Any]] = {
    "seedance-2": {
        "resolutions": {"480p", "720p", "1080p", "4k"},
        "ratios": SEEDANCE_RATIOS,
        "duration_range": range(4, 16),
        "duration_auto": True,
        "audio": True,
    },
    "seedance-2-fast": {
        "resolutions": {"480p", "720p"},
        "ratios": SEEDANCE_RATIOS,
        "duration_range": range(4, 16),
        "duration_auto": True,
        "audio": True,
    },
    "seedance-2-mini": {
        "resolutions": {"480p", "720p"},
        "ratios": SEEDANCE_RATIOS,
        "durations": {4, 8, 10, 12, 15},
        "audio": True,
    },
    "happyhorse-1.1": {
        "resolutions": {"720P", "1080P"},
        "ratios": HAPPYHORSE_RATIOS,
        "duration_range": range(3, 16),
        "audio": False,
    },
}

IMAGE_MODEL_RULES: dict[str, dict[str, Any]] = {
    "gpt-image-2": {
        "sizes": {
            "1:1",
            "3:2",
            "2:3",
            "4:3",
            "3:4",
            "5:4",
            "4:5",
            "16:9",
            "9:16",
            "2:1",
            "1:2",
            "21:9",
            "9:21",
        },
        "resolutions": {"1K", "2K", "4K"},
        "request_fields": {"resolution", "response_format", "reference_images"},
        "reference_field": "reference_images",
    },
    "doubao-seedream-5-0-pro": {
        "sizes": {"1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "9:21"},
        "resolutions": {"1K", "2K"},
        "request_fields": {"metadata", "image_urls"},
        "metadata_fields": {"resolution"},
        "reference_field": "image_urls",
        "max_references": 10,
    },
    "doubao-seedream-5-0": {
        "sizes": {"1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "9:21"},
        "resolutions": {"2K", "3K"},
        "request_fields": {"metadata", "image_urls"},
        "metadata_fields": {"resolution"},
        "reference_field": "image_urls",
        "max_references": 10,
    },
    "gemini-3-pro-image-preview": {
        "sizes": {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"},
        "resolutions": {"1K", "2K", "4K"},
        "request_fields": {"metadata", "image_urls"},
        "metadata_fields": {"resolution", "orientation"},
        "reference_field": "image_urls",
        "reference_objects": True,
        "max_references": 14,
    },
    "gemini-3.1-flash-image-preview": {
        "sizes": {
            "1:1",
            "3:2",
            "2:3",
            "4:3",
            "3:4",
            "16:9",
            "9:16",
            "5:4",
            "4:5",
            "21:9",
            "1:4",
            "4:1",
            "1:8",
            "8:1",
        },
        "resolutions": {"0.5K", "1K", "2K", "4K"},
        "request_fields": {"metadata", "image_urls"},
        "metadata_fields": {"resolution", "google_search", "google_image_search"},
        "reference_field": "image_urls",
        "reference_objects": True,
        "max_references": 14,
    },
}


class ImageReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: AnyHttpUrl


class ImageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: Literal["0.5K", "1K", "2K", "3K", "4K"] | None = None
    orientation: Literal["landscape", "portrait"] | None = None
    google_search: bool | None = None
    google_image_search: bool | None = None


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: ImageModel
    prompt: str = Field(min_length=1, max_length=32000)
    size: str = "1:1"
    n: Literal[1] = 1
    resolution: Literal["1k", "2k", "4k"] | None = None
    response_format: Literal["url"] | None = None
    reference_images: list[AnyHttpUrl] = Field(default_factory=list)
    image_urls: list[AnyHttpUrl | ImageReference] = Field(default_factory=list)
    metadata: ImageMetadata | None = None

    @model_validator(mode="after")
    def validate_model_options(self):
        rules = IMAGE_MODEL_RULES[self.model]
        if self.size not in rules["sizes"]:
            raise ValueError(f"{self.model} 不支持比例 {self.size}")

        optional_fields = self.model_fields_set & {
            "resolution",
            "response_format",
            "reference_images",
            "image_urls",
            "metadata",
        }
        unsupported_fields = optional_fields - rules["request_fields"]
        if unsupported_fields:
            raise ValueError(f"{self.model} 不支持参数 {', '.join(sorted(unsupported_fields))}")

        metadata_fields = self.metadata.model_fields_set if self.metadata else set()
        unsupported_metadata = metadata_fields - rules.get("metadata_fields", set())
        if unsupported_metadata:
            raise ValueError(
                f"{self.model} 不支持 metadata 参数 {', '.join(sorted(unsupported_metadata))}"
            )

        resolution = (
            self.resolution.upper()
            if self.resolution
            else getattr(self.metadata, "resolution", None)
        )
        if resolution and resolution not in rules["resolutions"]:
            raise ValueError(f"{self.model} 不支持分辨率 {resolution}")

        references = getattr(self, rules["reference_field"])
        if len(references) > rules.get("max_references", len(references)):
            raise ValueError(f"{self.model} 参考图片不能超过 {rules['max_references']} 张")
        if rules.get("reference_objects") and any(
            not isinstance(item, ImageReference) for item in references
        ):
            raise ValueError(f"{self.model} 的 image_urls 必须使用 URL 对象")
        if (
            not rules.get("reference_objects")
            and rules["reference_field"] == "image_urls"
            and any(isinstance(item, ImageReference) for item in references)
        ):
            raise ValueError(f"{self.model} 的 image_urls 必须使用 URL 字符串")
        if self.metadata and self.metadata.google_image_search and not self.metadata.google_search:
            raise ValueError("google_image_search 需要同时启用 google_search")
        return self


class VideoGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: VideoModel
    prompt: str = Field(min_length=1, max_length=32000)
    duration: int
    resolution: str
    aspect_ratio: str
    generate_audio: bool | None = None
    reference_images: list[AnyHttpUrl] = Field(default_factory=list, max_length=9)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("视频提示词不能为空")
        return value.strip()

    @model_validator(mode="after")
    def validate_model_options(self):
        rules = VIDEO_MODEL_RULES[self.model]
        if self.resolution not in rules["resolutions"]:
            raise ValueError(f"{self.model} 不支持分辨率 {self.resolution}")
        if self.aspect_ratio not in rules["ratios"]:
            raise ValueError(f"{self.model} 不支持比例 {self.aspect_ratio}")
        valid_duration = self.duration in rules.get("durations", set()) or (
            self.duration in rules.get("duration_range", range(0))
        )
        if rules.get("duration_auto") and self.duration == 0:
            valid_duration = True
        if not valid_duration:
            raise ValueError(f"{self.model} 不支持时长 {self.duration}")
        if self.generate_audio is not None and not rules["audio"]:
            raise ValueError(f"{self.model} 不支持音频生成参数")
        return self
