import os
from pathlib import Path

from flask import Flask

from services.google_ads_tag import GOOGLE_ADS_ORIGINS, google_ads_config, google_ads_tag, inject_google_ads


def test_config_requires_a_valid_tag_id():
    assert google_ads_config("") is None
    assert google_ads_config(None) is None
    assert google_ads_config("G-ABC123") is None
    assert google_ads_config('AW-123" onload="x') is None
    assert google_ads_config(" aw-18578242897 ") == {"tag_id": "AW-18578242897", "origins": GOOGLE_ADS_ORIGINS}


def test_tag_is_our_local_consent_controller_only():
    tag = google_ads_tag(google_ads_config("AW-18578242897"))
    assert tag == '<script src="/static/google-ads-consent.js" defer data-tag-id="AW-18578242897"></script>'
    assert "googletagmanager" not in tag
    assert google_ads_tag(None) == ""


def test_inject_only_into_public_html_pages():
    app = Flask(__name__)
    config = google_ads_config("AW-18578242897")
    with app.test_request_context("/"):
        html = app.response_class("<html><head><title>x</title></head><body></body></html>", mimetype="text/html")
        assert "google-ads-consent.js" in inject_google_ads(html, config, path="/").get_data(as_text=True)
        private = app.response_class("<html><head></head><body></body></html>", mimetype="text/html")
        assert "google-ads" not in inject_google_ads(private, config, path="/stats-partenaires").get_data(as_text=True)
        json_resp = app.response_class('{"a":1}', mimetype="application/json")
        assert "google-ads" not in inject_google_ads(json_resp, config, path="/api").get_data(as_text=True)
        off = app.response_class("<html><head></head></html>", mimetype="text/html")
        assert inject_google_ads(off, None, path="/") is off


def test_consent_script_loads_nothing_before_explicit_accept():
    """Le fichier ne charge gtag.js que dans loadTag(), appelée seulement après « accepted »."""
    js = Path(__file__).resolve().parents[1].joinpath("static", "google-ads-consent.js").read_text(encoding="utf-8")
    assert js.count("googletagmanager.com/gtag/js") == 1
    load_tag = js.split("function loadTag()", 1)[1].split("\n  }\n", 1)[0]
    assert 'readConsent() !== "accepted"' in load_tag
    assert "googletagmanager.com/gtag/js" in load_tag
    assert '"consent", "default", DENIED' in load_tag
    # Stockage local bloqué : l'accord reste en mémoire pour charger la balise quand même.
    assert "memoryConsent = value" in js and "if (memoryConsent) return memoryConsent" in js
    assert 'data-choice="reject"' in js and 'data-choice="accept"' in js


def _client(monkeypatch, tag_id):
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    import app as app_module

    monkeypatch.setitem(app_module.app.config, "GOOGLE_ADS", google_ads_config(tag_id))
    return app_module.app.test_client()


def test_site_loads_controller_and_opens_csp_only_when_enabled(monkeypatch):
    client = _client(monkeypatch, "AW-18578242897")
    response = client.get("/confidentialite")
    body = response.get_data(as_text=True)
    assert 'data-tag-id="AW-18578242897"' in body
    assert "data-ads-consent" in body and "Google Ads" in body
    csp = response.headers["Content-Security-Policy"]
    script_src = next(part for part in csp.split(";") if part.strip().startswith("script-src"))
    # Comparaison exacte des jetons de la directive (pas une recherche de sous-chaîne, CodeQL).
    assert set(GOOGLE_ADS_ORIGINS) <= set(script_src.split()[1:])

    off = _client(monkeypatch, "")
    response = off.get("/confidentialite")
    assert "google-ads-consent.js" not in response.get_data(as_text=True)
    assert "data-ads-consent" not in response.get_data(as_text=True)
    assert "googletagmanager" not in response.headers["Content-Security-Policy"]


def test_private_pages_never_get_google_ads(monkeypatch):
    client = _client(monkeypatch, "AW-18578242897")
    monkeypatch.setenv("STATS_TOKEN", "jeton-de-test-assez-long-1234")
    response = client.get("/stats-partenaires")
    assert "google-ads-consent.js" not in response.get_data(as_text=True)
    assert "googletagmanager" not in response.headers.get("Content-Security-Policy", "")


# Conversions (constat du 23 novembre 2026) : la balise se déclarait (« config ») sans jamais envoyer de conversion ;
# Google Ads ne savait pas quels clics menaient à quelque chose et ne pouvait rien optimiser. GOOGLE_ADS_CONVERSIONS
# (Render) donne l'étiquette de chaque action : « question:AW-…/…,appli:AW-…/… ».

def test_les_conversions_se_lisent_dans_une_variable_et_refusent_le_reste():
    from services.google_ads_tag import google_ads_conversions

    raw = " question:AW-18578242897/AbC_d-12 , appli:AW-18578242897/xyz98765 "
    assert google_ads_conversions(raw) == {"question": "AW-18578242897/AbC_d-12", "appli": "AW-18578242897/xyz98765"}
    assert google_ads_conversions("") == {} and google_ads_conversions(None) == {}
    # Action inconnue, étiquette mal formée, injection : ignorées une à une, jamais tout le reste.
    raw = 'inconnue:AW-123456/abcd,question:AW-12/abcd,appli:AW-123456/ab"cd,cv:AW-123456/abcd1234'
    assert google_ads_conversions(raw) == {"cv": "AW-123456/abcd1234"}


def test_la_balise_porte_les_etiquettes_de_conversion():
    config = google_ads_config("AW-18578242897", "question:AW-18578242897/AbC_d-12")
    assert config["conversions"] == {"question": "AW-18578242897/AbC_d-12"}
    tag = google_ads_tag(config)
    assert 'data-conversion-question="AW-18578242897/AbC_d-12"' in tag
    assert "googletagmanager" not in tag
    # Sans conversion configurée, la balise reste exactement la même qu'avant.
    assert google_ads_config("AW-18578242897", "") == {"tag_id": "AW-18578242897", "origins": GOOGLE_ADS_ORIGINS}
    assert google_ads_config("", "question:AW-18578242897/AbC_d-12") is None  # pas de balise : pas de conversion


def test_le_script_n_envoie_une_conversion_qu_apres_accord():
    js = Path(__file__).resolve().parents[1].joinpath("static", "google-ads-consent.js").read_text(encoding="utf-8")
    conversion = js.split("function sendConversion(", 1)[1].split("\n  }\n", 1)[0]
    assert "started" in conversion and 'readConsent() !== "accepted"' in conversion
    assert '"event", "conversion"' in conversion and "send_to" in conversion
