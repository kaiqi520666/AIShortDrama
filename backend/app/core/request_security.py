from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.schemas.response import fail

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


class SameOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in SAFE_METHODS or not request.url.path.startswith("/api"):
            return await call_next(request)
        source = request.headers.get("origin") or request.headers.get("referer")
        if not source and get_settings().app_env == "production":
            return JSONResponse(status_code=403, content=fail("请求来源无效"))
        if source and not self._allowed(source, request.headers.get("host", "")):
            return JSONResponse(status_code=403, content=fail("请求来源无效"))
        return await call_next(request)

    @staticmethod
    def _allowed(source: str, request_host: str) -> bool:
        source_url = urlsplit(source)
        source_host = source_url.hostname
        target_host = urlsplit(f"//{request_host}").hostname
        if source_url.netloc.casefold() == request_host.casefold():
            return True
        return get_settings().app_env != "production" and {
            source_host,
            target_host,
        }.issubset(LOOPBACK_HOSTS)
