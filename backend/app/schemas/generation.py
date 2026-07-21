from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class ImageGenerationRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    model: Literal["gpt-image-2"]
    prompt: str = Field(min_length=1, max_length=32000)
    size: Literal[
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
    ] = "1:1"
    resolution: Literal["1k", "2k", "4k"] = "1k"
    n: Literal[1] = 1
    response_format: Literal["url"] = "url"
    reference_images: list[AnyHttpUrl] = Field(default_factory=list)
