from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CreateRechargeOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_cents: int | None = Field(default=None, ge=100, le=10_000_000)
    provider: Literal["zpay", "cahaya"] = "zpay"
    amount_minor: int | None = Field(default=None, ge=1, le=100_000_000)

    @field_validator("amount_cents")
    @classmethod
    def require_whole_yuan(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value % 100:
            raise ValueError("充值金额必须为整数元")
        return value

    @model_validator(mode="after")
    def validate_provider_amount(self):
        if self.provider == "zpay" and self.amount_cents is None:
            raise ValueError("ZPay 订单缺少人民币金额")
        if self.provider == "cahaya" and self.amount_minor is None:
            raise ValueError("Cahaya 订单缺少印尼盾金额")
        return self
