from services.observability import build_request_log


def test_request_log_excludes_query_string_and_sanitizes_fields():
    result = build_request_log(
        request_id="abc/123",
        method="post",
        path="/chat?message=secret",
        status="429",
        duration_ms="12.3456",
    )

    assert result == {
        "request_id": "abc123",
        "method": "POST",
        "path": "/chat",
        "status": 429,
        "duration_ms": 12.35,
    }


def test_request_log_never_contains_request_body_fields():
    result = build_request_log(
        request_id="abc",
        method="GET",
        path="/health",
        status=200,
        duration_ms=1,
    )

    assert set(result) == {"request_id", "method", "path", "status", "duration_ms"}
