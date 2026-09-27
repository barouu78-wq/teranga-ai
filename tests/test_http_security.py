from services.http_security import origin_allowed


def test_origin_allowed_accepts_explicit_origin():
    assert origin_allowed("https://example.com", "", {"https://example.com"})


def test_origin_allowed_uses_referer_origin_when_origin_missing():
    assert origin_allowed("", "https://example.com/path?q=1", {"https://example.com"})


def test_origin_allowed_rejects_missing_or_untrusted_origin():
    allowed = {"https://example.com"}
    assert not origin_allowed("", "", allowed)
    assert not origin_allowed("https://evil.example", "", allowed)


def test_origin_allowed_disables_check_for_empty_allowlist():
    assert origin_allowed("https://anything.example", "", set())
