import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class ModelPriceRule(Base):
    __tablename__ = "model_price_rules"
    __table_args__ = (
        Index(
            "uq_model_price_rules_lookup",
            "media_type",
            "model",
            "specification",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32))
    media_type: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    specification: Mapped[str] = mapped_column(String(32), server_default=text("''"))
    billing_unit: Mapped[str] = mapped_column(String(24))
    cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    input_cost_per_million: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    output_cost_per_million: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    base_credits: Mapped[int | None] = mapped_column(Integer)
    freeze_credits: Mapped[int | None] = mapped_column(Integer)
    multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 3), server_default=text("1.000")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (
        Index("ix_credit_ledger_user_created_at", "user_id", "created_at"),
        Index("uq_credit_ledger_idempotency_key", "idempotency_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("generation_tasks.id", ondelete="SET NULL")
    )
    recharge_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recharge_orders.id", ondelete="SET NULL"), unique=True
    )
    media_type: Mapped[str | None] = mapped_column(String(16))
    model: Mapped[str | None] = mapped_column(String(64))
    entry_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(BigInteger)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    frozen_after: Mapped[int] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(160))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_admin_audit_logs_admin_created_at", "admin_id", "created_at"),
        Index("ix_admin_audit_logs_target_created_at", "target_type", "target_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    before_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    after_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RechargeTier(Base):
    __tablename__ = "recharge_tiers"
    __table_args__ = (
        CheckConstraint("min_amount_cents > 0", name="ck_recharge_tiers_min_amount_positive"),
        CheckConstraint(
            "bonus_rate_bps BETWEEN 0 AND 3000", name="ck_recharge_tiers_bonus_rate"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    min_amount_cents: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    bonus_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RechargeOrder(Base):
    __tablename__ = "recharge_orders"
    __table_args__ = (
        Index("ix_recharge_orders_user_created_at", "user_id", "created_at"),
        Index("ix_recharge_orders_status_created_at", "status", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'paid', 'failed')", name="ck_recharge_orders_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    tier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recharge_tiers.id", ondelete="SET NULL")
    )
    out_trade_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), server_default=text("'zpay'"))
    provider_trade_no: Mapped[str | None] = mapped_column(String(64))
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    base_credits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bonus_credits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_credits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tier_snapshot: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    pay_type: Mapped[str] = mapped_column(String(20), server_default=text("'wxpay'"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    pay_url: Mapped[str | None] = mapped_column(String(500))
    qr_code: Mapped[str | None] = mapped_column(String(500))
    qr_img: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(String(255))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
