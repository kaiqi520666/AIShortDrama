from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("资产名称不能为空")
        return value.strip()


class AssetPrivateAvatarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str | None = Field(default=None, min_length=1, max_length=128)


class ComposeImageBoardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    node_id: str = Field(min_length=1, max_length=64)
    asset_ids: list[str] = Field(min_length=6, max_length=6)

    @field_validator("asset_ids")
    @classmethod
    def validate_asset_ids(cls, value: list[str]) -> list[str]:
        if len(set(value)) != 6:
            raise ValueError("总览图需要 6 个不同的图片资产")
        return value
