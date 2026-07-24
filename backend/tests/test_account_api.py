import uuid
from datetime import UTC, datetime, time, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import SessionLocal
from app.main import app
from app.models import CreditLedger


@pytest.mark.asyncio
async def test_account_credit_summary_uses_beijing_consume_boundary(override_business_user):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        before = (await client.get("/api/account")).json()["data"]

    beijing = timezone(timedelta(hours=8))
    day_start = datetime.combine(datetime.now(beijing).date(), time.min, beijing).astimezone(UTC)
    entries = [
        CreditLedger(
            id=uuid.uuid4(),
            user_id=override_business_user,
            entry_type=entry_type,
            amount=amount,
            balance_after=0,
            frozen_after=0,
            idempotency_key=f"account-test:{uuid.uuid4()}",
            created_at=created_at,
        )
        for entry_type, amount, created_at in (
            ("consume", 7, day_start - timedelta(seconds=1)),
            ("consume", 11, day_start + timedelta(seconds=1)),
            ("refund", 99, day_start + timedelta(seconds=1)),
            ("freeze", 99, day_start + timedelta(seconds=1)),
        )
    ]
    try:
        async with SessionLocal() as db:
            db.add_all(entries)
            await db.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            after = (await client.get("/api/account")).json()["data"]

        assert after["credits"]["consumed_total"] == before["credits"]["consumed_total"] + 18
        assert after["credits"]["consumed_today"] == before["credits"]["consumed_today"] + 11
        assert after["user"]["username"]
        assert after["user"]["email"]
    finally:
        async with SessionLocal() as db:
            for entry in entries:
                current = await db.get(CreditLedger, entry.id)
                if current:
                    await db.delete(current)
            await db.commit()
