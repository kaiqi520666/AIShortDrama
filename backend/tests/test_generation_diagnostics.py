from app.core.errors import diagnostic_snapshot
from app.providers.toapis import ToApisError


def test_diagnostic_snapshot_persists_provider_details_only():
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

    assert diagnostic == {"token": "[REDACTED]", "message": "request failed"}


def test_exception_without_provider_details_has_no_diagnostic_snapshot():
    assert diagnostic_snapshot(RuntimeError("database password=private"), "billing") is None


def test_non_toapis_details_are_not_persisted():
    error = RuntimeError("request failed")
    error.details = {"message": "not a ToAPIs response"}

    assert diagnostic_snapshot(error, "submit") is None


def test_diagnostic_snapshot_redacts_credentials_in_provider_details():
    diagnostic = diagnostic_snapshot(
        ToApisError(
            "request failed",
            details={
                "Authorization": "Bearer private",
                "message": "api_key: secret",
            },
        )
    )

    assert diagnostic == {
        "Authorization": "[REDACTED]",
        "message": "api_key=[REDACTED]",
    }
