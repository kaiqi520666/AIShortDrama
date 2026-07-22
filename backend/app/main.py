from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.redis import create_redis_pool
from app.core.request_security import SameOriginMiddleware
from app.schemas.response import fail


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_pool()
    await app.state.redis.ping()
    yield
    await app.state.redis.aclose()


app = FastAPI(title="AI Short Drama API", lifespan=lifespan)
app.add_middleware(SameOriginMiddleware)
app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=fail(str(exc.detail)))
