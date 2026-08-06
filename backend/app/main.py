from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.redis import create_redis_pool
from app.core.errors import ApiError
from app.core.request_security import SameOriginMiddleware
from app.schemas.response import fail
import logging


logger = logging.getLogger(__name__)


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
    status_code = 422 if exc.status_code == 400 else exc.status_code
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(status_code=status_code, content=fail(message))


@app.exception_handler(ApiError)
async def api_exception_handler(_request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content=fail(exc.message, exc.data))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=422, content=fail("请求参数无效"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _exc: Exception):
    logger.exception("Unhandled API error", extra={"method": request.method, "path": request.url.path})
    return JSONResponse(status_code=500, content=fail("服务暂时不可用"))
