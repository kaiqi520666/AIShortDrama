import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BillingPolicy(Base):
    __tablename__ = "billing_policies"
    __table_args__ = (
        CheckConstraint("key = 'default'", name="ck_billing_policies_singleton"),
        CheckConstraint("recharge_min_cents > 0", name="ck_billing_policies_min_positive"),
        CheckConstraint("recharge_max_cents >= recharge_min_cents", name="ck_billing_policies_range"),
        CheckConstraint("unit_amount_cents > 0", name="ck_billing_policies_unit_amount"),
        CheckConstraint("unit_credits > 0", name="ck_billing_policies_unit_credits"),
    )

    key: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    recharge_min_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    recharge_max_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_credits: Mapped[int] = mapped_column(Integer, nullable=False)
    idr_recharge_min: Mapped[int] = mapped_column(Integer, server_default=text("150000"), nullable=False)
    idr_recharge_max: Mapped[int] = mapped_column(Integer, server_default=text("15000000"), nullable=False)
    idr_unit_amount: Mapped[int] = mapped_column(Integer, server_default=text("150000"), nullable=False)
    idr_unit_credits: Mapped[int] = mapped_column(Integer, server_default=text("1000"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditPolicy(Base):
    __tablename__ = "credit_policies"
    __table_args__ = (
        CheckConstraint("key = 'default'", name="ck_credit_policies_singleton"),
        CheckConstraint(
            "registration_bonus_credits > 0",
            name="ck_credit_policies_registration_bonus_positive",
        ),
        CheckConstraint(
            "daily_minimum_credits > 0",
            name="ck_credit_policies_daily_minimum_positive",
        ),
    )

    key: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    registration_bonus_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true")
    )
    registration_bonus_credits: Mapped[int] = mapped_column(
        Integer, server_default=text("10")
    )
    daily_refill_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true")
    )
    daily_minimum_credits: Mapped[int] = mapped_column(
        Integer, server_default=text("10")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ModelAdminSetting(Base):
    __tablename__ = "model_admin_settings"
    __table_args__ = (
        Index("uq_model_admin_settings_media_model", "media_type", "model_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContentTemplate(Base):
    __tablename__ = "content_templates"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
