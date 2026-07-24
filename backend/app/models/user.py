import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Integer, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("credit_balance >= 0", name="ck_users_credit_balance_nonnegative"),
        CheckConstraint("credit_frozen >= 0", name="ck_users_credit_frozen_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    auth_version: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    is_system: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    credit_balance: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    credit_frozen: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
