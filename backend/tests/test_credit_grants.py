import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import CreditLedger, User
from app.services.credit_grants import apply_daily_credit_floor


def user(balance: int, *, status: str = "active", is_system: bool = False) -> User:
    user_id = uuid.uuid4()
    return User(
        id=user_id,
        username=f"credit-{user_id.hex[:8]}",
        email=f"credit-{user_id.hex[:8]}@example.com",
        password_hash="test",
        credit_balance=balance,
        credit_frozen=20,
        status=status,
        is_system=is_system,
    )


@pytest.mark.asyncio
async def test_daily_floor_uses_available_balance_and_grants_once_per_day():
    low = user(2)
    enough = user(10)
    disabled = user(1, status="disabled")
    system = user(1, is_system=True)
    async with SessionLocal() as db:
        db.add_all([low, enough, disabled, system])
        await db.commit()

    today = date(2026, 8, 24)
    async with SessionLocal() as db:
        count, credits = await apply_daily_credit_floor(db, today)
        await db.commit()
    assert (count, credits) == (1, 8)

    async with SessionLocal() as db:
        assert (await db.get(User, low.id)).credit_balance == 10
        assert (await db.get(User, disabled.id)).credit_balance == 1
        assert (await db.get(User, system.id)).credit_balance == 1
        ledger = await db.scalar(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == f"daily-floor:{today.isoformat()}:{low.id}"
            )
        )
        assert ledger.amount == 8
        assert ledger.balance_after == 10
        assert ledger.frozen_after == 20
        low_again = await db.get(User, low.id)
        low_again.credit_balance = 1
        await db.commit()

    async with SessionLocal() as db:
        assert await apply_daily_credit_floor(db, today) == (0, 0)
        assert await apply_daily_credit_floor(db, today + timedelta(days=1)) == (1, 9)
        await db.commit()
