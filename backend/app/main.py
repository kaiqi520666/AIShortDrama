from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.redis import create_redis_pool
from app.core.errors import ApiError, error_fields
from app.core.request_security import SameOriginMiddleware
from app.schemas.response import fail
from app.core.observability import reset_request_id, set_request_id
import logging


logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        context_token = set_request_id(request_id)
        started_at = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            reset_request_id(context_token)
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "api_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code if response else 500,
                    "duration_ms": elapsed_ms,
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_pool()
    await app.state.redis.ping()
    yield
    await app.state.redis.aclose()


app = FastAPI(title="AI Short Drama API", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SameOriginMiddleware)
app.include_router(api_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    status_code = 422 if exc.status_code == 400 else exc.status_code
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=status_code,
        content=fail(message, **error_fields(exc, status_code=status_code)),
        headers=exc.headers,
    )


@app.exception_handler(ApiError)
async def api_exception_handler(_request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.message, exc.data, **error_fields(exc, status_code=exc.status_code)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=422, content=fail("请求参数无效", error_key="invalid_request"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _exc: Exception):
    logger.exception(
        "Unhandled API error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(status_code=500, content=fail("服务暂时不可用", error_key="service_unavailable"))
