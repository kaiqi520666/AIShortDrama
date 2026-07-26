import uuid
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class ReversePromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: Literal["qwen3.7-plus", "qwen3.6-flash"]
    media_type: Literal["image", "video"]
    media_url: AnyHttpUrl
    media_urls: list[AnyHttpUrl] = Field(default_factory=list, max_length=9)
    prompt: str = Field(default="", max_length=3000)
    response_mode: Literal["prompt", "product_profile", "product_visual_plan"] = "prompt"

    @model_validator(mode="after")
    def validate_prompt(self):
        if self.response_mode != "product_profile" and not self.prompt.strip():
            raise ValueError("提示词不能为空")
        return self
