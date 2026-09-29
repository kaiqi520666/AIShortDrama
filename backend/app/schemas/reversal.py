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


class ProductVisualTemplateContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_context: str = Field(max_length=6000)
    selected_type_ids: list[str] = Field(min_length=1, max_length=17)
    aspect_ratio: str = Field(pattern=r"^\d{1,3}:\d{1,3}$")
    resolution: str = Field(pattern=r"^\d{1,3}[Kk]$")
    reference_count: int = Field(ge=1, le=6)

    @model_validator(mode="after")
    def validate_type_ids(self):
        if len(self.selected_type_ids) != len(set(self.selected_type_ids)) or any(
            not 1 <= len(item) <= 32 for item in self.selected_type_ids
        ):
            raise ValueError("商品出图类型无效")
        return self


class ApparelVisualTemplateContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apparel_context: str = Field(max_length=6000)
    aspect_ratio: str = Field(pattern=r"^\d{1,3}:\d{1,3}$")
    resolution: str = Field(pattern=r"^\d{1,3}[Kk]$")
    reference_count: int = Field(ge=1, le=3)
    model_reference_provided: bool | None = None
    scene_reference_provided: bool | None = None
    model_description: str = Field(default="", max_length=600)
    scene_description: str = Field(default="", max_length=600)
    user_requirement: str = Field(default="", max_length=600)


class ApparelVideoTemplateContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apparel_context: str = Field(max_length=6000)
    aspect_ratio: str = Field(pattern=r"^\d{1,3}:\d{1,3}$")
    duration: int
    model_description: str = Field(default="", max_length=600)
    scene_description: str = Field(default="", max_length=600)
    user_requirement: str = Field(default="", max_length=600)


class ReversePromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    node_id: str = Field(min_length=1, max_length=64)
    model: Literal["gpt-5.6-sol"]
    media_type: Literal["image"]
    media_url: AnyHttpUrl
    media_urls: list[AnyHttpUrl] = Field(default_factory=list, max_length=9)
    prompt: str = Field(default="", max_length=6000)
    template_key: Literal[
        "product_visual",
        "apparel_visual",
        "product_storyboard",
        "commerce_drama",
        "apparel_showcase",
    ] | None = None
    template_version: int | None = Field(default=None, ge=1)
    template_context: (
        StoryboardTemplateContext
        | ProductVisualTemplateContext
        | ApparelVisualTemplateContext
        | ApparelVideoTemplateContext
        | None
    ) = None
    response_mode: Literal[
        "prompt",
        "product_profile",
        "apparel_profile",
        "product_visual_plan",
        "outfit_visual_plan",
        "apparel_video_plan",
        "product_storyboard_plan",
    ] = "prompt"

    @model_validator(mode="after")
    def validate_prompt(self):
        storyboard_mode = self.response_mode == "product_storyboard_plan"
        product_visual_mode = self.response_mode == "product_visual_plan"
        apparel_visual_mode = self.response_mode == "outfit_visual_plan"
        apparel_video_mode = self.response_mode == "apparel_video_plan"
        if product_visual_mode:
            if self.prompt.strip():
                raise ValueError("商品出图 Prompt 必须由服务端模板生成")
            if (
                self.template_key != "product_visual"
                or not self.template_version
                or not isinstance(self.template_context, ProductVisualTemplateContext)
            ):
                raise ValueError("商品出图模板参数不完整")
            if 1 + len(self.media_urls) != self.template_context.reference_count:
                raise ValueError("商品出图参考图数量不一致")
        elif apparel_visual_mode:
            if self.prompt.strip():
                raise ValueError("服饰试穿 Prompt 必须由服务端模板生成")
            if (
                self.template_key != "apparel_visual"
                or not self.template_version
                or not isinstance(self.template_context, ApparelVisualTemplateContext)
            ):
                raise ValueError("服饰试穿模板参数不完整")
            if 1 + len(self.media_urls) != self.template_context.reference_count:
                raise ValueError("服饰试穿参考图数量不一致")
        elif apparel_video_mode:
            if self.prompt.strip():
                raise ValueError("服饰视频 Prompt 必须由服务端模板生成")
            if (
                self.template_key != "apparel_showcase"
                or not self.template_version
                or not isinstance(self.template_context, ApparelVideoTemplateContext)
            ):
                raise ValueError("服饰视频模板参数不完整")
            if len(self.media_urls) != 1:
                raise ValueError("服饰视频必须使用定妆图和服饰原图")
        elif storyboard_mode:
            if self.prompt.strip():
                raise ValueError("商品分镜 Prompt 必须由服务端模板生成")
            if (
                self.template_key not in {"product_storyboard", "commerce_drama"}
                or not self.template_version
                or not isinstance(self.template_context, StoryboardTemplateContext)
            ):
                raise ValueError("商品分镜模板参数不完整")
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
            "product_visual_plan",
            "outfit_visual_plan",
            "apparel_video_plan",
            "product_storyboard_plan",
        } and not self.prompt.strip():
            raise ValueError("提示词不能为空")
        if self.response_mode in {
            "product_profile",
            "product_visual_plan",
            "product_storyboard_plan",
        } and len(self.media_urls) > 5:
            raise ValueError("商品创作最多支持 6 张参考图片")
        return self
