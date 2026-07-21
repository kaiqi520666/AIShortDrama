from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.database import engine
from app.schemas.response import success

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    await request.app.state.redis.ping()
    return success({"status": "ok"})
