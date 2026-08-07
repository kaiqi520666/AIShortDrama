import uuid
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class StoryboardTemplateContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_context: str = Field(default="", max_length=6000)
    duration: int
    video_aspect_ratio: str = Field(min_length=3, max_length=16)
    character_count: int = Field(ge=0, le=3)
    product_count: int = Field(ge=1, le=6)
    user_requirement: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def validate_reference_count(self):
        if self.character_count + self.product_count > 6:
            raise ValueError("商品创作最多支持 6 张参考图片")
        return self


class ReversePromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: Literal["gpt-5.6-sol"]
    media_type: Literal["image"]
    media_url: AnyHttpUrl
    media_urls: list[AnyHttpUrl] = Field(default_factory=list, max_length=9)
    prompt: str = Field(default="", max_length=6000)
    template_key: Literal["product_storyboard"] | None = None
    template_version: int | None = Field(default=None, ge=1)
    template_context: StoryboardTemplateContext | None = None
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
        storyboard_mode = self.response_mode == "product_storyboard_plan"
        if storyboard_mode:
            if self.prompt.strip():
                raise ValueError("UGC 分镜 Prompt 必须由服务端模板生成")
            if not self.template_key or not self.template_version or not self.template_context:
                raise ValueError("UGC 分镜模板参数不完整")
            reference_count = 1 + len(self.media_urls)
            expected_count = (
                self.template_context.character_count + self.template_context.product_count
            )
            if reference_count != expected_count:
                raise ValueError("商品分镜参考图数量不一致")
        elif any((self.template_key, self.template_version, self.template_context)):
            raise ValueError("当前任务不支持内容模板参数")
        if self.response_mode not in {
            "product_profile",
            "apparel_profile",
            "product_storyboard_plan",
        } and not self.prompt.strip():
            raise ValueError("提示词不能为空")
        if self.response_mode in {"product_profile", "product_storyboard_plan"} and len(self.media_urls) > 5:
            raise ValueError("商品创作最多支持 6 张参考图片")
        return self
