from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.redis import create_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_pool()
    await app.state.redis.ping()
    yield
    await app.state.redis.aclose()


app = FastAPI(title="AI Short Drama API", lifespan=lifespan)
app.include_router(api_router)
