import uuid
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class ReversePromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: Literal["gpt-5.6-sol"]
    media_type: Literal["image"]
    media_url: AnyHttpUrl
    media_urls: list[AnyHttpUrl] = Field(default_factory=list, max_length=9)
    prompt: str = Field(default="", max_length=3000)
    response_mode: Literal[
        "prompt",
        "product_profile",
        "apparel_profile",
        "product_visual_plan",
        "product_storyboard_plan",
        "apparel_storyboard_plan",
        "character_profile",
        "character_visual_plan",
    ] = "prompt"

    @model_validator(mode="after")
    def validate_prompt(self):
        if self.response_mode not in {"product_profile", "apparel_profile"} and not self.prompt.strip():
            raise ValueError("提示词不能为空")
        if self.response_mode in {"product_profile", "product_storyboard_plan"} and len(self.media_urls) > 5:
            raise ValueError("商品创作最多支持 6 张参考图片")
        return self
