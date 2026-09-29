import json
import uuid

import httpx
import pytest
from fastapi import HTTPException

from app.core.errors import (
    ApiError,
    InsufficientCreditsError,
    LocalizedValueError,
    RequestError,
    error_fields,
    task_error_fields,
)
from app.main import app, api_exception_handler, http_exception_handler
from app.models import GenerationTask
from app.schemas.response import fail, success
from app.services.generation_tasks import task_payload
from app.services.recharge import RechargeError


def test_response_envelopes_keep_existing_fields():
    assert success({"content": "保留生成内容"}) == {
        "code": 0, "message": "ok", "data": {"content": "保留生成内容"},
    }
    assert fail("原始信息", {"balance": 1}, error_key="insufficient_credits") == {
        "code": 1, "message": "原始信息", "data": {"balance": 1},
        "error_key": "insufficient_credits", "error_params": {},
    }


@pytest.mark.parametrize("status,key", [
    (401, "unauthorized"), (402, "insufficient_credits"), (403, "forbidden"),
    (404, "not_found"), (409, "conflict"), (422, "invalid_request"),
    (429, "rate_limited"), (500, "service_unavailable"), (502, "upstream_unavailable"),
])
def test_status_fallback_never_depends_on_message(status, key):
    assert error_fields(RuntimeError("任意中文或供应商错误"), status_code=status) == {
        "error_key": key, "error_params": {},
    }


@pytest.mark.asyncio
async def test_api_handler_preserves_caused_error_key_and_parameters():
    original = LocalizedValueError(
        "文件不能超过 20MB", error_key="file_size_limit", error_params={"limit": "20MB"},
    )
    wrapped = RequestError(str(original), {"asset": "unchanged"})
    wrapped.__cause__ = original
    response = await api_exception_handler(None, wrapped)
    assert response.status_code == 422
    assert json.loads(response.body) == {
        "code": 1, "message": str(original), "data": {"asset": "unchanged"},
        "error_key": "file_size_limit", "error_params": {"limit": "20MB"},
    }


@pytest.mark.asyncio
async def test_api_error_status_and_explicit_key_take_precedence():
    error = InsufficientCreditsError("原文不改")
    response = await api_exception_handler(None, error)
    assert response.status_code == 402
    assert json.loads(response.body)["error_key"] == "insufficient_credits"
    outer = ApiError("outer", error_key="queue_failed")
    outer.__cause__ = LocalizedValueError("inner")
    assert error_fields(outer)["error_key"] == "queue_failed"


@pytest.mark.asyncio
async def test_http_handler_preserves_status_mapping_and_headers():
    response = await http_exception_handler(
        None, HTTPException(status_code=400, detail="原参数错误", headers={"X-Test": "kept"}),
    )
    assert response.status_code == 422
    assert response.headers["X-Test"] == "kept"
    assert json.loads(response.body)["error_key"] == "invalid_request"


def test_recharge_error_parameters_survive_route_wrapper():
    error = RechargeError(
        "充值金额无效", error_key="recharge_amount", error_params={"min": 10, "max": 100},
    )
    wrapped = RequestError(str(error))
    wrapped.__cause__ = error
    assert error_fields(wrapped)["error_params"] == {"min": 10, "max": 100}


@pytest.mark.parametrize("status,key", [
    ("failed", "generation_failed"), ("cancelled", "task_cancelled"), ("timeout", "task_timeout"),
])
def test_task_projection_leaves_stored_error_content_and_result_unchanged(status, key):
    task = GenerationTask(
        id=uuid.uuid4(), workspace_id=uuid.uuid4(), node_id="node-1",
        task_type="image", model="test", status=status, progress=0,
        error_message="历史错误不改", prompt="用户提示词",
        result={"content": "生成内容不改"},
    )
    result = task_payload(task)
    assert result["error_key"] == key
    assert result["error_message"] == task.error_message == "历史错误不改"
    assert result["result"] == {"content": "生成内容不改"}
    assert task.prompt == "用户提示词"
    assert task_error_fields("succeeded") == {}


@pytest.mark.asyncio
async def test_framework_and_origin_errors_have_structured_envelopes():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.get("/api/route-that-does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["error_key"] == "not_found"
        invalid_origin = await client.post("/api/auth/login", headers={"Origin": "https://other.test"}, json={})
        assert invalid_origin.status_code == 403
        assert invalid_origin.json()["error_key"] == "invalid_origin"
        validation = await client.post("/api/auth/login", json={})
        assert validation.status_code == 422
        assert validation.json()["error_key"] == "invalid_request"
