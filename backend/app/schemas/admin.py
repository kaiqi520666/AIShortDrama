from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    cost_per_unit: Decimal | None = Field(default=None, ge=0)
    input_cost_per_million: Decimal | None = Field(default=None, ge=0)
    output_cost_per_million: Decimal | None = Field(default=None, ge=0)
    base_credits: int | None = Field(default=None, ge=0)
    freeze_credits: int | None = Field(default=None, ge=0)
    multiplier: Decimal = Field(gt=0, le=100)
    enabled: bool


class RechargeTierMutationRequest(AdminMutation):
    min_amount_cents: int = Field(gt=0, le=10_000_000)
    bonus_rate_bps: int = Field(ge=0, le=3000)
    enabled: bool = True

    @field_validator("min_amount_cents")
    @classmethod
    def require_whole_yuan(cls, value: int) -> int:
        if value % 100:
            raise ValueError("阶梯金额必须为整数元")
        return value


class BillingPolicyUpdateRequest(AdminMutation):
    recharge_min_cents: int = Field(gt=0, le=10_000_000)
    recharge_max_cents: int = Field(gt=0, le=10_000_000)
    unit_amount_cents: int = Field(gt=0, le=10_000_000)
    unit_credits: int = Field(gt=0, le=10_000_000)

    @field_validator("recharge_min_cents", "recharge_max_cents", "unit_amount_cents")
    @classmethod
    def require_whole_yuan_amount(cls, value: int) -> int:
        if value % 100:
            raise ValueError("金额必须为整数元")
        return value

    @model_validator(mode="after")
    def validate_range(self):
        if self.recharge_max_cents < self.recharge_min_cents:
            raise ValueError("充值封顶金额不能小于起充金额")
        return self


class CreditPolicyUpdateRequest(AdminMutation):
    registration_bonus_enabled: bool
    registration_bonus_credits: int = Field(gt=0, le=1_000_000)
    daily_refill_enabled: bool
    daily_minimum_credits: int = Field(gt=0, le=1_000_000)


class ModelAdminSettingUpdateRequest(AdminMutation):
    label: str = Field(min_length=1, max_length=100)
    enabled: bool
    is_default: bool

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("模型展示名称不能为空")
        return value


class ContentTemplateUpdateRequest(AdminMutation):
    enabled: bool
    config: dict


class SystemReferenceAssetUpdateRequest(AdminMutation):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(ge=0, le=100_000)
    active: bool
    tags: list[str] = Field(default_factory=list, max_length=20)
    copyright_note: str = Field(default="", max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("素材名称不能为空")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        result = []
        for item in value:
            item = item.strip()
            if not item or len(item) > 32 or item in result:
                continue
            result.append(item)
        return result
