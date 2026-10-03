from flask import Response

from services.http_headers import add_security_headers


def test_add_security_headers_sets_security_and_cache_headers():
    response = add_security_headers(Response("ok"), path="/health")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_add_security_headers_uses_nonce_and_hsts():
    response = add_security_headers(
        Response("ok"),
        path="/icon.svg",
        nonce="abc123",
        forwarded_proto="https",
    )

    assert response.headers["Cache-Control"] == "public, max-age=86400"
    assert "'nonce-abc123'" in response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains"
    assert "Server" not in response.headers
