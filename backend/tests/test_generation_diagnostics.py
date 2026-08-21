from app.core.errors import diagnostic_snapshot
from app.providers.toapis import ToApisError


def test_diagnostic_snapshot_redacts_urls_and_credentials():
    diagnostic = diagnostic_snapshot(
        ToApisError(
            "request https://signed.example/file?signature=secret Authorization: Bearer-secret",
            status_code=503,
            request_id="req-123",
            retryable=True,
            code="upstream_error",
            details={"token": "private", "message": "request failed"},
        ),
        "submit",
    )

    assert diagnostic["stage"] == "submit"
    assert diagnostic["category"] == "upstream_http"
    assert diagnostic["provider_status"] == 503
    assert diagnostic["provider_request_id"] == "req-123"
    assert diagnostic["provider_code"] == "upstream_error"
    assert diagnostic["provider_error"] == {"token": "[REDACTED]", "message": "request failed"}
    assert diagnostic["retryable"] is True
    assert "https://" not in diagnostic["provider_message"]
    assert "secret" not in diagnostic["provider_message"].lower()
    assert diagnostic["exception_message"] == (
        "request https://signed.example/file?signature=[REDACTED] "
        "Authorization=[REDACTED]"
    )
    assert diagnostic["exception_module"] == "app.providers.toapis"
    assert diagnostic["cause_chain"] == []
    assert "ToApisError" in diagnostic["traceback"]


def test_unknown_exception_persists_redacted_details_and_cause_chain():
    try:
        try:
            raise OSError("storage token=private")
        except OSError as exc:
            raise RuntimeError("database password=private") from exc
    except RuntimeError as exc:
        diagnostic = diagnostic_snapshot(exc, "billing")

    assert diagnostic["category"] == "billing"
    assert diagnostic["provider_message"] == "内部异常，详见服务端日志"
    assert diagnostic["exception_message"] == "database password=[REDACTED]"
    assert diagnostic["cause_chain"] == [
        {
            "exception_type": "OSError",
            "exception_module": "builtins",
            "exception_message": "storage token=[REDACTED]",
        }
    ]
    assert "RuntimeError: database password=[REDACTED]" in diagnostic["traceback"]
    assert "OSError: storage token=[REDACTED]" in diagnostic["traceback"]


def test_diagnostic_snapshot_redacts_quoted_credentials():
    diagnostic = diagnostic_snapshot(
        RuntimeError("headers={'Authorization': 'Bearer private', 'api_key': 'secret'}")
    )

    assert "private" not in diagnostic["exception_message"]
    assert "secret" not in diagnostic["exception_message"]
    assert diagnostic["exception_message"].count("[REDACTED]") == 2
