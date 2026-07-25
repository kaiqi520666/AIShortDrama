from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateRechargeOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_cents: int = Field(ge=3500, le=350000)

    @field_validator("amount_cents")
    @classmethod
    def require_whole_yuan(cls, value: int) -> int:
        if value % 100:
            raise ValueError("充值金额必须为整数元")
        return value
