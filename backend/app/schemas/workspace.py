import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def empty_canvas() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nodes": [],
        "edges": [],
        "groups": [],
        "sequence": 1,
        "group_sequence": 1,
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="未命名工作台", min_length=1, max_length=100)
    workspace_type: Literal["general", "ecommerce"]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("工作台名称不能为空")
        return value.strip()


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("工作台名称不能为空")
        return value.strip()


class CanvasUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    sequence: int = Field(default=1, ge=1)
    group_sequence: int = Field(default=1, ge=1)
    viewport: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0, "zoom": 1})

    @field_validator("nodes", "edges", "groups")
    @classmethod
    def validate_collection_size(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(value) > 4000:
            raise ValueError("画布内容超出允许大小")
        return value


class WorkspaceIdRequest(BaseModel):
    workspace_id: uuid.UUID
