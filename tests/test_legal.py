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


def test_asset_links_declare_the_android_app(monkeypatch):
    from app import app
    from routes.legal import ANDROID_CERT_SHA256, asset_links

    client = app.test_client()
    monkeypatch.delenv("ANDROID_APP_PACKAGE", raising=False)
    monkeypatch.delenv("ANDROID_CERT_SHA256", raising=False)
    target = client.get("/.well-known/assetlinks.json").get_json()[0]["target"]
    assert target["package_name"] == "fr.teranga_ai"
    assert target["sha256_cert_fingerprints"] == list(ANDROID_CERT_SHA256)
    assert all(len(fp.split(":")) == 32 for fp in target["sha256_cert_fingerprints"])
    # La variable d'environnement ajoute une empreinte valide, sans retirer celles du code ;
    # une valeur mal formée est ignorée plutôt que publiée.
    extra = ":".join(["AB"] * 32)
    monkeypatch.setenv("ANDROID_APP_PACKAGE", "fr.autre.app")
    monkeypatch.setenv("ANDROID_CERT_SHA256", f"SHA256: {extra.lower()}, pas-une-empreinte, {ANDROID_CERT_SHA256[0]}")
    data = client.get("/.well-known/assetlinks.json").get_json()
    assert data[0]["target"]["package_name"] == "fr.autre.app"
    assert data[0]["target"]["sha256_cert_fingerprints"] == [*ANDROID_CERT_SHA256, extra]
    assert asset_links("", extra) == [] and asset_links("pkg", "") == [] and asset_links("pkg", "AA:BB") == []


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


def test_manifest_has_store_ready_screenshots_and_shortcuts():
    from PIL import Image

    from app import app

    client = app.test_client()
    manifest = client.get("/manifest.webmanifest").get_json()
    assert {icon["purpose"] for icon in manifest["icons"]} == {"any", "maskable"}
    assert len(manifest["shortcuts"]) == 3 and manifest["prefer_related_applications"] is False
    for shot in manifest["screenshots"]:
        response = client.get(shot["src"])
        assert response.status_code == 200
        width, height = Image.open(__import__("io").BytesIO(response.data)).size
        assert shot["sizes"] == f"{width}x{height}"
        assert height / width <= 2  # rapport maximal accepté par Google Play


def test_manifest_lists_wide_screenshots_and_play_app_when_configured(monkeypatch):
    from app import app

    client = app.test_client()
    monkeypatch.delenv("ANDROID_APP_PACKAGE", raising=False)
    manifest = client.get("/manifest.webmanifest").get_json()
    assert {shot["form_factor"] for shot in manifest["screenshots"]} == {"narrow", "wide"}
    assert "related_applications" not in manifest
    monkeypatch.setenv("ANDROID_APP_PACKAGE", "fr.terangaai.app")
    manifest = client.get("/manifest.webmanifest").get_json()
    assert manifest["related_applications"][0] == {
        "platform": "play", "id": "fr.terangaai.app",
        "url": "https://play.google.com/store/apps/details?id=fr.terangaai.app",
    }
    assert manifest["prefer_related_applications"] is False
