import os
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

SW = Path(__file__).resolve().parents[1] / "static" / "sw.js"


def test_service_worker_is_served_from_root_with_full_scope():
    from app import app

    response = app.test_client().get("/sw.js")
    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert response.headers["Service-Worker-Allowed"] == "/"
    assert response.headers["Cache-Control"] == "no-store"
    assert "caches.open" in response.get_data(as_text=True)


def test_service_worker_never_caches_private_or_live_endpoints():
    source = SW.read_text(encoding="utf-8")
    never = source.split("const NEVER_CACHE = [", 1)[1].split("];", 1)[0]
    for path in ("/chat", "/tts", "/stt", "/realtime-call", "/csrf", "/api/", "/image-proxy"):
        assert f"'{path}'" in never
    assert "'/offline'" in source.split("const PRECACHE = [", 1)[1].split("];", 1)[0]


@pytest.mark.skipif(shutil.which("node") is None, reason="node non disponible")
def test_service_worker_is_valid_javascript():
    result = subprocess.run([shutil.which("node"), "--check", str(SW)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_offline_page_is_available_and_not_indexed():
    from app import app

    response = app.test_client().get("/offline")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Vous êtes hors ligne" in html
    assert '<meta name="robots" content="noindex">' in html
    assert '<link rel="stylesheet" href="/static/site.css?v=' in html
