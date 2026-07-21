from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.redis import create_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis_client()
    await app.state.redis.ping()
    yield
    await app.state.redis.aclose()


app = FastAPI(title="AI Short Drama API", lifespan=lifespan)
app.include_router(api_router)
