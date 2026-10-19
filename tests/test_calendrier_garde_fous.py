"""Calendrier des fêtes : deux garde-fous sur des dates qui expirent ou qui changent.

1. Le calendrier vérifié (services/events.py) s'arrête à sa dernière date. Passé cette date, l'IA ne doit pas recevoir
   un titre « PROCHAINES FÊTES » suivi de rien : le journal des lacunes (services/coverage_log.py) compterait alors les
   questions sur les fêtes comme couvertes, et personne ne verrait que le calendrier est vide.
2. Les dates des fêtes lunaires sont écrites deux fois : dans le calendrier et dans static/theme.js (touche de fête du
   thème). Une date confirmée quelques jours avant la fête est corrigée dans le calendrier : le thème doit suivre.
"""

import datetime as dt
import os
import re
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import events  # noqa: E402
from services.coverage_log import chat_signals, classify  # noqa: E402

# Lendemain de la dernière date du calendrier actuel (Assomption et Gamou, 15 août 2027).
APRES_LE_CALENDRIER = dt.date(2027, 8, 16)
QUESTION = "Quels conseils pour voyager pendant la Tabaski avec des enfants ?"


def _horloge(monkeypatch, day):
    """Simule seulement l'horloge du calendrier : services/events.py lit la date du jour avec _dt.date.today()."""

    class Jour(dt.date):
        @classmethod
        def today(cls):
            return cls(day.year, day.month, day.day)

    monkeypatch.setattr(events, "_dt", SimpleNamespace(date=Jour))


def _contexte_du_chat(question):
    from app import app, parse_chat_payload

    with app.test_request_context("/chat", method="POST", json={"message": question, "language": "fr"}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload


def test_aucun_bloc_de_fetes_quand_aucune_fete_n_est_a_venir():
    assert events.events_context(APRES_LE_CALENDRIER) == ""
    assert events.events_context(APRES_LE_CALENDRIER, query="c est quand la tabaski") == ""


def test_le_chat_n_envoie_pas_de_titre_vide_et_la_lacune_reste_visible(monkeypatch):
    # Un jour où le calendrier a des dates : le bloc est là, le thème « fêtes » est couvert.
    _horloge(monkeypatch, dt.date(2026, 10, 19))
    payload = _contexte_du_chat(QUESTION)
    assert "Tabaski (Aïd el-Kébir) (Tout le pays) : 17 mai 2027" in payload["instructions"]
    assert classify(QUESTION, chat_signals(payload))["fetes"] is True

    # Après la dernière date : pas de titre seul, et le journal des lacunes voit la question comme non couverte.
    _horloge(monkeypatch, APRES_LE_CALENDRIER)
    payload = _contexte_du_chat(QUESTION)
    assert "PROCHAINES FÊTES" not in payload["instructions"]
    assert classify(QUESTION, chat_signals(payload))["fetes"] is False


# Clé de la fête dans static/theme.js → début du nom dans services/events.py.
_FETES_DU_THEME = {"korite": "Korité", "tabaski": "Tabaski", "magal": "Grand Magal"}


def _dates_du_theme():
    """{(année, clé): (mois, jour)} lus dans le tableau FETES de static/theme.js."""
    source = (Path(__file__).resolve().parents[1] / "static" / "theme.js").read_text(encoding="utf-8")
    bloc = re.search(r"var FETES=\{(.*?)\n\s*\};", source, re.S)
    assert bloc, "tableau FETES introuvable dans static/theme.js"
    dates = {}
    for year, fetes in re.findall(r"(\d{4}):\{([^}]*)\}", bloc.group(1)):
        for key, month, day in re.findall(r"(\w+):\[(\d+),(\d+),\d+\]", fetes):
            dates[(int(year), key)] = (int(month), int(day))
    return dates


def test_le_tableau_des_fetes_du_theme_est_bien_lu():
    dates = _dates_du_theme()
    assert dates[(2027, "tabaski")] == (5, 17)
    assert dates[(2026, "magal")] == (8, 2)


def test_les_dates_de_fete_du_theme_suivent_le_calendrier():
    theme = _dates_du_theme()
    for start, _end, name, *_rest in events.EVENTS:
        for key, prefix in _FETES_DU_THEME.items():
            if name.startswith(prefix):
                assert theme.get((start.year, key)) == (start.month, start.day), (
                    f"{name} {start.year} : le calendrier dit le {start.day}/{start.month}, static/theme.js dit "
                    f"{theme.get((start.year, key))}. Mettre la même date dans le tableau FETES de static/theme.js."
                )
