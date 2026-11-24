"""Widget partenaire (/widget.js) : les visiteurs qu'il envoie sont comptés par partenaire, sans donnée personnelle."""

import datetime as dt
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

B = "https://teranga-ai.fr"
CLE = "un-mot-de-passe-solide-123"


def _client():
    from app import app

    return app.test_client()


def _stats(client, ip):
    # Adresse propre à chaque test : la page limite les essais de mot de passe par visiteur.
    return client.post("/stats-partenaires", data={"cle": CLE}, base_url=B,
                       environ_base={"REMOTE_ADDR": ip}).get_data(as_text=True)


def _arrivee(client, source, ip, medium="widget"):
    # Le lien exact que construit static/widget.js.
    url = f"/?lang=fr&utm_source={source}&utm_medium={medium}&utm_campaign=partenaires"
    return client.get(url, base_url=B, environ_base={"REMOTE_ADDR": ip})


def test_les_visiteurs_envoyes_par_le_widget_sont_comptes_par_partenaire(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    assert _arrivee(client, "hotel-widget-a", "203.0.113.71").status_code == 200
    assert _arrivee(client, "hotel-widget-a", "203.0.113.72").status_code == 200
    page = _stats(client, "203.0.113.72")
    assert "Widget (visiteurs envoyés)" in page
    assert "<td>Widget (visiteurs envoyés)</td><td>hotel-widget-a</td><td>2</td>" in page


def test_une_visite_sans_le_widget_ne_compte_pas(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    _arrivee(client, "lettre-pas-widget", "203.0.113.73", medium="email")
    client.get("/?utm_source=sans-medium-widget", base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.73"})
    page = _stats(client, "203.0.113.73")
    assert "lettre-pas-widget" not in page
    assert "sans-medium-widget" not in page


def test_le_nom_du_partenaire_est_nettoye(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    _arrivee(client, "Hotel%3Cb%3EX%3C%2Fb%3E", "203.0.113.74")
    page = _stats(client, "203.0.113.74")
    assert "<b>X" not in page
    assert "<td>hotelbxb</td>" in page


def test_un_script_ne_peut_pas_gonfler_les_chiffres(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    for _ in range(10):
        assert _arrivee(client, "hotel-gonfle", "203.0.113.75").status_code == 200
    assert "<td>hotel-gonfle</td><td>6</td>" in _stats(client, "203.0.113.75")


def test_le_nombre_de_partenaires_differents_est_borne():
    from services.click_stats import ClickStats

    stats = ClickStats()
    day = dt.date(2026, 10, 21)
    for n in range(5):
        stats.record("widget", f"partenaire-{n}", day, max_fields=3)
    stats.record("widget", "partenaire-0", day, max_fields=3)
    rows = {(kind, source): n for kind, source, n in stats.summary(months=1, today=day)[0]["rows"]}
    assert rows == {
        ("widget", "partenaire-0"): 2,
        ("widget", "partenaire-1"): 1,
        ("widget", "partenaire-2"): 1,
        ("widget", "autre"): 2,
    }
