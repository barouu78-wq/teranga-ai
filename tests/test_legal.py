import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_privacy_pages_exist_in_french_and_english_and_are_linked():
    from app import app

    client = app.test_client()
    fr = client.get("/confidentialite").get_data(as_text=True)
    en = client.get("/privacy").get_data(as_text=True)
    assert "Politique de confidentialité" in fr and "OpenAI" in fr and "Open-Meteo" in fr
    assert "Privacy policy" in en and "never your location" in en
    assert 'href="/confidentialite"' in client.get("/visiter-goree").get_data(as_text=True)


def test_privacy_contact_email_is_configurable(monkeypatch):
    from routes.legal import render_privacy

    assert "mailto:hello@example.com" in render_privacy("fr", "hello@example.com")
    assert "Google Play" in render_privacy("fr", "")


def test_asset_links_need_package_and_fingerprint(monkeypatch):
    from app import app

    client = app.test_client()
    monkeypatch.delenv("ANDROID_APP_PACKAGE", raising=False)
    assert client.get("/.well-known/assetlinks.json").status_code == 404
    monkeypatch.setenv("ANDROID_APP_PACKAGE", "fr.teranga_ai.twa")
    monkeypatch.setenv("ANDROID_CERT_SHA256", "aa:bb, cc:dd")
    data = client.get("/.well-known/assetlinks.json").get_json()
    assert data[0]["target"] == {"namespace": "android_app", "package_name": "fr.teranga_ai.twa", "sha256_cert_fingerprints": ["AA:BB", "CC:DD"]}


def test_report_endpoint_logs_the_answer_and_needs_csrf(caplog):
    from app import app

    client = app.test_client()
    assert client.post("/api/report", json={"reply": "x"}).status_code == 403  # sans jeton CSRF
    token = client.get("/csrf").get_json()["token"]
    with caplog.at_level("WARNING"):
        response = client.post("/api/report", json={"question": "Q?", "reply": "Réponse fausse", "reason": "wrong"},
                               headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"})
    assert response.status_code == 200 and response.get_json() == {"ok": True}
    assert any("ai-report" in record.getMessage() and "Réponse fausse" in record.getMessage() for record in caplog.records)


def test_manifest_uses_the_new_brand_colors():
    from app import app

    manifest = app.test_client().get("/manifest.webmanifest").get_json()
    assert manifest["theme_color"] == "#b5451b" and manifest["background_color"] == "#fbf3e6"
