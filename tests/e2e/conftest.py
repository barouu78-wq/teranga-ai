"""Tests de clics dans un vrai navigateur (Chromium via Playwright).

Ignorés si Playwright ou Chromium manque ; la CI les lance dans un job dédié.
Les API coûteuses (OpenAI, TTS…) sont simulées dans le navigateur : seul le
serveur Flask local est réellement joint.
"""

import os
import threading

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5.6-luna")

try:
    from playwright import sync_api
except ImportError:  # pragma: no cover - dépend de la machine
    sync_api = None


@pytest.fixture(scope="session")
def base_url():
    from werkzeug.serving import make_server

    from app import app

    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="session")
def browser():
    # En CI (job e2e), un navigateur manquant doit faire échouer, pas ignorer.
    required = os.getenv("E2E_REQUIRED") == "1"
    if sync_api is None:
        if required:
            pytest.fail("Playwright non installé")
        pytest.skip("Playwright non installé")
    with sync_api.sync_playwright() as p:
        options = {}
        local = "/opt/pw-browsers/chromium"
        if os.path.exists(local) and not os.getenv("CI"):
            options["executable_path"] = local
        try:
            instance = p.chromium.launch(**options)
        except Exception as exc:  # navigateur absent : on n'échoue pas la suite unitaire
            if required:
                raise
            pytest.skip(f"Chromium indisponible : {exc}")
        yield instance
        instance.close()


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(
        locale="fr-FR",
        service_workers="block",
        permissions=["clipboard-read", "clipboard-write"],
    )
    # Rien ne sort de la machine : seul le serveur de test répond.
    context.route(
        lambda url: not url.startswith(base_url) and not url.startswith("data:") and not url.startswith("blob:"),
        lambda route: route.abort(),
    )
    context.route(f"{base_url}/exchange-rates*", lambda route: route.fulfill(json={"rates": {"EUR": 655.957}}))
    pg = context.new_page()
    pg.errors = []
    pg.on("pageerror", lambda exc: pg.errors.append(str(exc)))
    yield pg
    context.close()
