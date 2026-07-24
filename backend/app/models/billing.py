import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
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
    entry_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(BigInteger)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    frozen_after: Mapped[int] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(160))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
