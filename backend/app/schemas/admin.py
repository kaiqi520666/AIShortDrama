from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.auth import validate_password


class AdminMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=255)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("操作原因不能为空")
        return value


class CreditAdjustmentRequest(AdminMutation):
    amount: int = Field(ge=-1_000_000, le=1_000_000)

    @field_validator("amount")
    @classmethod
    def reject_zero_amount(cls, value: int) -> int:
        if value == 0:
            raise ValueError("调整积分不能为 0")
        return value


class UserRoleRequest(AdminMutation):
    role: Literal["user", "admin"]


class UserStatusRequest(AdminMutation):
    status: Literal["active", "disabled"]


class AdminResetPasswordRequest(AdminMutation):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        validate_password(value)
        return value


class PriceRuleUpdateRequest(AdminMutation):
    provider: str = Field(min_length=1, max_length=32)
    media_type: Literal["text", "image", "video", "audio"]
    model: str = Field(min_length=1, max_length=64)
    specification: str = Field(max_length=32)
    billing_unit: str = Field(min_length=1, max_length=24)
    cost_per_unit: Decimal | None = Field(default=None, ge=0)
    input_cost_per_million: Decimal | None = Field(default=None, ge=0)
    output_cost_per_million: Decimal | None = Field(default=None, ge=0)
    base_credits: int | None = Field(default=None, ge=0)
    freeze_credits: int | None = Field(default=None, ge=0)
    multiplier: Decimal = Field(gt=0, le=100)
    enabled: bool
