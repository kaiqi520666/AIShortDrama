from app.core.errors import diagnostic_snapshot
from app.providers.toapis import ToApisError


def test_diagnostic_snapshot_redacts_urls_and_credentials():
    diagnostic = diagnostic_snapshot(
        ToApisError(
            "request https://signed.example/file?signature=secret Authorization: Bearer-secret",
            status_code=503,
            request_id="req-123",
            retryable=True,
        ),
        "submit",
    )

    assert diagnostic["stage"] == "submit"
    assert diagnostic["category"] == "upstream_http"
    assert diagnostic["provider_status"] == 503
    assert diagnostic["provider_request_id"] == "req-123"
    assert diagnostic["retryable"] is True
    assert "https://" not in diagnostic["provider_message"]
    assert "secret" not in diagnostic["provider_message"].lower()


def test_unknown_exception_does_not_persist_raw_message():
    diagnostic = diagnostic_snapshot(RuntimeError("database password=private"), "billing")

    assert diagnostic["category"] == "billing"
    assert diagnostic["provider_message"] == "内部异常，详见服务端日志"
