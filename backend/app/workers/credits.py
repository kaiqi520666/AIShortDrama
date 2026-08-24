from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.services.credit_grants import apply_daily_credit_floor


BEIJING = ZoneInfo("Asia/Shanghai")


async def replenish_daily_credits(_ctx) -> dict[str, int]:
    async with SessionLocal() as db:
        users, credits = await apply_daily_credit_floor(
            db,
            datetime.now(UTC).astimezone(BEIJING).date(),
        )
        await db.commit()
    return {"users": users, "credits": credits}
