"""Google refuse (403) ou quota épuisé (429) : pause, puis Wikipédia/Commons prennent le relais."""

import io
import os
from urllib.error import HTTPError

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402


def test_google_403_pauses_google_instead_of_failing_every_photo(monkeypatch):
    calls = []

    def refused(*args, **kwargs):
        calls.append(1)
        raise HTTPError("https://www.googleapis.com", 403, "Forbidden", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(app_module, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(app_module, "GOOGLE_CSE_ID", "cx")
    monkeypatch.setattr(app_module, "_fetch_google_images", refused)
    monkeypatch.setattr(app_module, "redis_client", None)
    monkeypatch.setattr(app_module, "_google_paused_until", 0.0)

    assert app_module.fetch_google_images("Cap Skirring") == []
    assert app_module.google_images_paused()
    assert app_module.fetch_google_images("Joal-Fadiouth") == []
    assert calls == [1]  # le second appel ne contacte plus Google


def test_other_google_errors_still_raise(monkeypatch):
    def broken(*args, **kwargs):
        raise HTTPError("https://www.googleapis.com", 500, "Server Error", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(app_module, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(app_module, "GOOGLE_CSE_ID", "cx")
    monkeypatch.setattr(app_module, "_fetch_google_images", broken)
    monkeypatch.setattr(app_module, "redis_client", None)
    monkeypatch.setattr(app_module, "_google_paused_until", 0.0)
    try:
        app_module.fetch_google_images("Gorée")
    except HTTPError as exc:
        assert exc.code == 500
    else:
        raise AssertionError("une erreur 500 doit remonter")
    assert not app_module.google_images_paused()
