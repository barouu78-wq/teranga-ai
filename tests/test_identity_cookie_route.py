from app import IDENTITY_COOKIE, app


def test_protected_route_sets_identity_cookie():
    client = app.test_client()
    response = client.get("/health")
    assert IDENTITY_COOKIE not in response.headers.get("Set-Cookie", "")

    response = client.get("/exchange-rates")
    assert response.status_code == 200
    cookie = response.headers.get("Set-Cookie", "")
    assert IDENTITY_COOKIE in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" in cookie


def test_existing_identity_cookie_is_preserved():
    client = app.test_client()
    client.set_cookie(IDENTITY_COOKIE, "A" * 24)
    response = client.get("/exchange-rates")
    assert response.status_code == 200
    assert IDENTITY_COOKIE not in response.headers.get("Set-Cookie", "")
