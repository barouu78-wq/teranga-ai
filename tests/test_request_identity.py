from services.request_identity import client_ip


def test_client_ip_uses_proxy_normalized_remote_addr():
    assert client_ip("203.0.113.10") == "203.0.113.10"
    assert client_ip(None) == "unknown"


def test_client_ip_is_bounded():
    assert len(client_ip("x" * 100)) == 64
