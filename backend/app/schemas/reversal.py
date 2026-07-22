import uuid
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ReversePromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: Literal["qwen3.7-plus", "qwen3.6-flash"]
    media_type: Literal["image", "video"]
    media_url: AnyHttpUrl
    prompt: str = Field(min_length=1, max_length=32000)
