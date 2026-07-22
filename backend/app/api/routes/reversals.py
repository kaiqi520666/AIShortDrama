import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.providers.dashscope import DashScopeProvider
from app.schemas.response import fail
from app.schemas.reversal import ReversePromptRequest

router = APIRouter()


@router.post("/stream")
async def stream_reverse_prompt(payload: ReversePromptRequest):
    try:
        provider = DashScopeProvider()
    except RuntimeError as exc:
        return JSONResponse(status_code=503, content=fail(str(exc)))

    async def events():
        try:
            async with provider:
                async for content in provider.stream_reverse_prompt(
                    model=payload.model,
                    media_type=payload.media_type,
                    media_url=str(payload.media_url),
                    prompt=payload.prompt,
                ):
                    yield (
                        json.dumps({"type": "delta", "content": content}, ensure_ascii=False) + "\n"
                    )
            yield '{"type":"done"}\n'
        except Exception as exc:
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
