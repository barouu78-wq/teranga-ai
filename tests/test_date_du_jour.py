"""Date du jour donnée à l'IA : « ce week-end », « cette année », « la prochaine Tabaski » dépendent d'elle.

La date est calculée côté serveur dans le fuseau de Dakar. L'horloge est toujours figée par
monkeypatch (jamais l'horloge réelle) : chaque date attendue est écrite à la main et a été
vérifiée avec la commande `date` (15 octobre 2026 = jeudi, 1er novembre 2026 = dimanche).
"""

import datetime as dt
import json
from types import SimpleNamespace

import pytest

import services.dakar_date as dakar_date
from app import app, parse_chat_payload

UTC = dt.timezone.utc


def _figer_horloge(monkeypatch, *args):
    """Fige l'horloge du serveur sur l'instant UTC donné (année, mois, jour, heure, minute, seconde)."""
    instant = dt.datetime(*args, tzinfo=UTC)
    monkeypatch.setattr(dakar_date, "_now_utc", lambda: instant)


def _instructions(message, language="fr"):
    with app.test_request_context(
        "/chat", method="POST", json={"message": message, "history": [], "language": language, "audience": "tourist"},
    ):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"]


def test_les_instructions_donnent_la_date_du_jour_a_dakar(monkeypatch):
    _figer_horloge(monkeypatch, 2026, 10, 15, 10, 0, 0)
    instructions = _instructions("Que faire ce week-end à Dakar ?")
    assert "Date du jour : jeudi 15 octobre 2026 (heure de Dakar)." in instructions


def test_la_date_est_en_anglais_quand_la_conversation_est_en_anglais(monkeypatch):
    _figer_horloge(monkeypatch, 2026, 10, 15, 10, 0, 0)
    instructions = _instructions("What can I do in Dakar this weekend?", language="en")
    assert "Today's date: Thursday, October 15, 2026 (Dakar time)." in instructions
    assert "Date du jour :" not in instructions


def test_le_premier_du_mois_s_ecrit_1er(monkeypatch):
    _figer_horloge(monkeypatch, 2026, 11, 1, 9, 0, 0)
    assert "Date du jour : dimanche 1er novembre 2026 (heure de Dakar)." in _instructions("Que visiter à Dakar ?")


@pytest.mark.parametrize(
    ("instant", "attendu"),
    [
        # Dakar est à GMT : à 23 h 59 UTC il est encore le 15 à Dakar (déjà le 16 à Paris, en heure d'été).
        ((2026, 10, 15, 23, 59, 30), "Date du jour : jeudi 15 octobre 2026 (heure de Dakar)."),
        ((2026, 10, 16, 0, 0, 30), "Date du jour : vendredi 16 octobre 2026 (heure de Dakar)."),
    ],
)
def test_la_date_suit_le_fuseau_de_dakar_pres_de_minuit_utc(monkeypatch, instant, attendu):
    _figer_horloge(monkeypatch, *instant)
    assert attendu in _instructions("Que visiter à Dakar ?")


def test_un_instant_donne_dans_un_autre_fuseau_est_ramene_a_dakar():
    # 1 h 30 à Paris (UTC+2 en octobre) le 16 = 23 h 30 UTC le 15 = 23 h 30 à Dakar le 15.
    paris_ete = dt.timezone(dt.timedelta(hours=2))
    assert dakar_date.dakar_today(dt.datetime(2026, 10, 16, 1, 30, tzinfo=paris_ete)) == dt.date(2026, 10, 15)


def test_sans_base_des_fuseaux_le_serveur_reste_a_l_heure_de_dakar(monkeypatch):
    """Base des fuseaux absente du serveur : repli sur GMT, l'heure du Sénégal toute l'année."""
    vrai_fuseau = dakar_date._dakar_zone()
    for jour in (dt.datetime(2026, 1, 15, 12, tzinfo=UTC), dt.datetime(2026, 7, 15, 12, tzinfo=UTC)):
        assert vrai_fuseau.utcoffset(jour) == dt.timedelta(0)  # pas d'heure d'été à Dakar

    def base_absente(_name):
        raise dakar_date.ZoneInfoNotFoundError("Africa/Dakar")

    monkeypatch.setattr(dakar_date, "ZoneInfo", base_absente)
    repli = dakar_date._dakar_zone()
    assert repli.utcoffset(None) == dt.timedelta(0)
    assert dakar_date.dakar_today(dt.datetime(2026, 10, 15, 23, 59, tzinfo=UTC)) == dt.date(2026, 10, 15)


# --- Cache des réponses : une réponse ne doit jamais resservir la date d'un autre jour ------------------------------

# Texte neutre (aucun fait) : il doit seulement dépasser la longueur minimale mise en cache (60 caractères).
REPONSE = "Réponse simulée par le test, assez longue pour être gardée dans le cache des réponses du site."


def _poser(client, message, ip):
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat",
        json={"message": message, "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
        base_url="https://teranga-ai.fr",
        environ_base={"REMOTE_ADDR": ip},
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
    return "".join(e.get("d", "") for e in events)


def test_le_cache_ne_resert_pas_la_reponse_d_un_autre_jour(monkeypatch):
    import app as app_module

    appels = []

    def faux_modele(payload, stream=True):
        appels.append(payload["instructions"])
        yield SimpleNamespace(type="response.output_text.delta", delta=REPONSE)
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text=REPONSE))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", faux_modele)
    client = app_module.app.test_client()

    _figer_horloge(monkeypatch, 2026, 10, 15, 23, 50, 0)
    assert _poser(client, "Que visiter à Thiès ?", "203.0.113.171") == REPONSE
    assert _poser(client, "que visiter à thiès", "203.0.113.172") == REPONSE
    assert len(appels) == 1, "le même jour, la seconde question doit venir du cache"

    # Minuit passé à Dakar : la réponse d'hier porte la date d'hier, elle ne doit pas être resservie.
    _figer_horloge(monkeypatch, 2026, 10, 16, 0, 10, 0)
    assert _poser(client, "Que visiter à Thiès ?", "203.0.113.173") == REPONSE
    assert len(appels) == 2
    assert "Date du jour : jeudi 15 octobre 2026 (heure de Dakar)." in appels[0]
    assert "Date du jour : vendredi 16 octobre 2026 (heure de Dakar)." in appels[1]
