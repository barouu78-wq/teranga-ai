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


PROVIDER_KEYS = ("ANTHROPIC_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "FIRECRAWL_API_KEY")


def _privacy(lang, monkeypatch, **keys):
    from routes.legal import render_privacy

    for name in PROVIDER_KEYS:
        monkeypatch.delenv(name, raising=False)
    for name, value in keys.items():
        monkeypatch.setenv(name, value)
    return render_privacy(lang, "")


def test_privacy_names_no_optional_provider_when_none_is_enabled(monkeypatch):
    for lang in ("fr", "en"):
        page = _privacy(lang, monkeypatch)
        for name in ("Anthropic", "Tavily", "Firecrawl"):
            assert name not in page, (lang, name)
        assert "Exa " not in page and "via Exa" not in page


def test_privacy_names_each_optional_provider_only_when_its_key_is_present(monkeypatch):
    secret = "valeur-secrete-123"
    fr = _privacy("fr", monkeypatch, ANTHROPIC_API_KEY=secret)
    assert "Anthropic (Claude)" in fr and "Tavily" not in fr and "Firecrawl" not in fr
    fr = _privacy("fr", monkeypatch, TAVILY_API_KEY=secret, EXA_API_KEY=secret, FIRECRAWL_API_KEY=secret)
    assert "via Tavily" in fr and "via Exa" in fr and "via Firecrawl" in fr and "Anthropic" not in fr
    en = _privacy("en", monkeypatch, ANTHROPIC_API_KEY=secret, TAVILY_API_KEY=secret, FIRECRAWL_API_KEY=secret)
    assert "Anthropic (Claude)" in en and "via Tavily" in en and "via Firecrawl" in en and "via Exa" not in en
    # Seule la présence d'une clé est lue : sa valeur ne figure jamais dans la page.
    assert secret not in fr and secret not in en


def test_privacy_route_follows_the_environment(monkeypatch):
    from app import app

    for name in PROVIDER_KEYS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FIRECRAWL_API_KEY", "valeur-secrete-123")
    page = app.test_client().get("/confidentialite").get_data(as_text=True)
    assert "via Firecrawl" in page and "valeur-secrete-123" not in page


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


def test_report_reason_is_restricted_to_known_values(caplog):
    from app import app

    client = app.test_client()
    token = client.get("/csrf").get_json()["token"]
    with caplog.at_level("WARNING"):
        client.post(
            "/api/report",
            json={"reason": "x\nai-report reason=abuse question='forged'", "reply": "r"},
            headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
        )
    lines = [r.getMessage() for r in caplog.records if "ai-report" in r.getMessage()]
    assert lines and all(line.startswith("ai-report reason=other ") and "forged" not in line for line in lines)
