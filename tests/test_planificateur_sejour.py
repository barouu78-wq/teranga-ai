"""« Pendant ton séjour » : les fêtes du calendrier vérifié qui tombent dans les dates du voyage.

« Go » du propriétaire, 24 novembre 2026 : à partir des dates de départ et de retour, le planificateur montre les
fêtes du calendrier (services/events.py) et l'IA en tient compte. Aucune fête inventée ; une date lunaire reste
« estimée, à confirmer ». Navigateur : tests/e2e/test_planificateur_sejour.py.
"""

import datetime as dt
import json
import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import events  # noqa: E402
from services.events import events_between  # noqa: E402
from services.trip_planner import _html, _prompt  # noqa: E402

D = dt.date
FAUX = (
    (D(2030, 1, 10), None, "Fête A", "Dakar", "holiday", True, "Conseil A."),
    (D(2030, 1, 14), D(2030, 1, 16), "Festival B", "Saint-Louis", "festival", True, "Conseil B."),
    (D(2030, 1, 20), None, "Fête C", "Tout le pays", "religious", False, "Conseil C."),
    ("2030-01-12", None, "Ligne mal saisie", "?", "holiday", True, ""),
)


def _noms(start, end):
    return [e["name"] for e in events_between(start, end)]


def test_les_fetes_du_sejour_bornes_comprises(monkeypatch):
    monkeypatch.setattr(events, "EVENTS", FAUX)
    # Le jour du départ et celui du retour comptent ; une ligne mal saisie n'apparaît jamais.
    assert _noms(D(2030, 1, 10), D(2030, 1, 14)) == ["Fête A", "Festival B"]
    # Un festival commencé avant le départ et pas encore fini compte aussi.
    assert _noms(D(2030, 1, 15), D(2030, 1, 18)) == ["Festival B"]
    assert _noms(D(2030, 1, 17), D(2030, 1, 19)) == []
    assert events_between(D(2030, 1, 20), D(2030, 1, 20))[0]["confirmed"] is False


def _data(arrival, departure):
    return {"lang": "fr", "arrival": arrival, "departure": departure, "adults": 2, "children": 0,
            "interests": [], "budget": "Confort", "pace": "Équilibré", "regions": [], "surprise": False}


def test_l_ia_recoit_les_fetes_du_sejour_avec_leur_statut(monkeypatch):
    monkeypatch.setattr(events, "EVENTS", FAUX)
    prompt = _prompt(_data("2030-01-09", "2030-01-21"))
    assert "Holidays and events during the trip" in prompt
    assert "- Fête A (Dakar): 2030-01-10 [confirmed]. Conseil A." in prompt
    assert "- Festival B (Saint-Louis): 2030-01-14 to 2030-01-16 [confirmed]. Conseil B." in prompt
    assert "- Fête C (Tout le pays): 2030-01-20 [estimated, to be confirmed]. Conseil C." in prompt
    assert "Do not invent other holidays or events." in prompt
    assert "Ligne mal saisie" not in prompt
    # Sans fête dans les dates, rien n'est ajouté (pas de titre seul).
    assert "Holidays and events during the trip" not in _prompt(_data("2030-01-01", "2030-01-05"))


def _config(html):
    return json.loads(re.search(r'<script type="application/json" id="trip-config">(.*?)</script>', html, re.S).group(1))


def test_la_page_porte_le_calendrier_pour_le_navigateur(monkeypatch):
    monkeypatch.setattr(events, "EVENTS", FAUX)
    fr = _config(_html("https://example.com", "fr"))
    assert fr["during_trip"] == "Pendant ton séjour"
    assert fr["events"] == [
        {"name": "Fête A", "start": "2030-01-10", "end": None, "confirmed": True, "kind": "Jour férié", "tips": "Conseil A."},
        {"name": "Festival B", "start": "2030-01-14", "end": "2030-01-16", "confirmed": True, "kind": "Festival",
         "tips": "Conseil B."},
        {"name": "Fête C", "start": "2030-01-20", "end": None, "confirmed": False, "kind": "Fête religieuse",
         "tips": "Conseil C."},
    ]
    en = _config(_html("https://example.com", "en"))
    assert en["during_trip"] == "During your trip"
    assert en["events"][2]["kind"] == "Religious holiday"
    # Les conseils du calendrier sont écrits en français : la page anglaise ne les mélange pas à l'anglais.
    assert all(e["tips"] == "" for e in en["events"])


def test_un_nom_de_fete_ne_peut_pas_casser_la_page(monkeypatch):
    monkeypatch.setattr(events, "EVENTS", ((D(2030, 1, 10), None, "</script><b>X", "Dakar", "holiday", True, ""),))
    html = _html("https://example.com", "fr")
    assert "</script><b>X" not in html
    assert _config(html)["events"][0]["name"] == "</script><b>X"
