"""Teranga répond seul à « C'est quand la Tabaski ? », depuis son calendrier vérifié (services/events.py).

Décision du propriétaire du 19 octobre 2026 : plus d'indépendance pour Teranga. Les dates viennent telles quelles du
calendrier du dépôt ; une fête lunaire non confirmée reste « estimée ». Toute autre question sur une fête (sens,
prix du mouton, programme, deux fêtes à la fois) va au modèle.
"""

import datetime as dt
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services import quick_answers
from services.quick_answers import quick_answer

TODAY = dt.date(2026, 10, 19)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(quick_answers, "_today", lambda: TODAY)


def _ask(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


ASKED = (
    ("C'est quand la Tabaski ?", "Tabaski (Aïd el-Kébir) : 17 mai 2027"),
    ("Quand est-ce que la Tabaski ?", "Tabaski (Aïd el-Kébir) : 17 mai 2027"),
    ("Quelle est la date de la Tabaski 2027 ?", "Tabaski (Aïd el-Kébir) : 17 mai 2027"),
    ("c est quand la fête du mouton", "Tabaski (Aïd el-Kébir) : 17 mai 2027"),
    ("Korité c'est quand ?", "Korité (Aïd el-Fitr) : 10 mars 2027"),
    ("Date du prochain Magal ?", "Grand Magal de Touba : 23 juillet 2027"),
    ("C'est quand le festival de jazz de Saint-Louis ?", "4 mai 2027 au 8 mai 2027"),
    ("C'est quand la fête de l'indépendance ?", "Fête de l'Indépendance : 4 avril 2027"),
)
NOT_ASKED = (
    "C'est quoi la Tabaski ?",
    "Combien coûte un mouton pour la Tabaski ?",
    "Que faire à Dakar pendant la Tabaski ?",
    "C'est quand la Tabaski et le Magal ?",
    "C'est quand la Tabaski 2029 ?",
    "Tabaski",
    "C'est quand le prochain match du Sénégal ?",
)


@pytest.mark.parametrize("message, expected", ASKED)
def test_date_question_gets_the_calendar_date(message, expected):
    answer = _ask(message)
    assert answer is not None, message
    assert expected in answer["reply"]
    assert "teranga-ai.fr/calendrier-fetes-senegal" in answer["reply"]


def test_lunar_date_not_confirmed_stays_estimated():
    reply = _ask("C'est quand la Tabaski ?")["reply"]
    assert "estimée" in reply and "calendrier lunaire" in reply
    assert "confirmée" not in reply.replace("non confirmée", "")


def test_confirmed_date_is_said_confirmed():
    reply = _ask("C'est quand la fête de l'indépendance ?")["reply"]
    assert "Date confirmée" in reply and "estimée" not in reply


def test_place_is_given_only_when_it_is_precise():
    assert "Lieu : Tivaouane, Ndiassane, Médina Baye" in _ask("C'est quand le Gamou ?")["reply"]
    assert "Tout le pays" not in _ask("C'est quand la Tabaski ?")["reply"]


def test_days_left_are_counted_from_today():
    # Du 19 octobre 2026 au 17 mai 2027 : 210 jours.
    assert "dans 210 jours" in _ask("C'est quand la Tabaski ?")["reply"]


@pytest.mark.parametrize("message", NOT_ASKED)
def test_other_questions_about_holidays_go_to_the_model(message):
    assert _ask(message) is None


def test_a_holiday_already_past_with_no_next_date_goes_to_the_model(monkeypatch):
    monkeypatch.setattr(quick_answers, "_today", lambda: dt.date(2027, 9, 1))
    assert _ask("C'est quand la Tabaski ?") is None


def test_context_and_other_languages_go_to_the_model():
    message = "C'est quand la Tabaski ?"
    earlier = [{"role": "user", "content": "Je viens en mai"}, {"role": "assistant", "content": "Super !"}]
    assert _ask(message, raw={"history": earlier + [{"role": "user", "content": message}]}) is None
    assert _ask(message, raw={"trip_context": "Dakar en mai"}) is None
    assert _ask(message, language="en") is None
    assert _ask(message, language="wo") is None
