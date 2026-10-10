"""Repères « peche_artisanale » (services/facts/peche_artisanale.py) : permis, immatriculation, CLPA, repos biologique."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import peche_artisanale  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in peche_artisanale.TOPICS for fact in facts)

POSITIVE = [
    ("Comment obtenir un permis de pêche artisanale ?", "A pour la pêche à pied"),
    ("Quel est le permis B de pêche pour une pirogue de 10 mètres ?", "B pour les pirogues de 0 à 13 mètres"),
    ("Comment immatriculer ma pirogue ?", "Immatriculation : la loi de 2015"),
    ("C'est quoi le repos biologique du poulpe ?", "un mois pour le poulpe en pêche artisanale en 2012"),
    ("Que sont les CLPA ?", "conseils locaux de pêche artisanale (CLPA)"),
    ("Je veux devenir pêcheur à Mbour, que faut-il faire ?", "Direction des pêches maritimes (DPM)"),
    ("Que dit le Code de la pêche maritime ?", "loi n° 2015-18 du 13 juillet 2015"),
    ("Qui délivre le permis de pêche ? Redevances ?", "non confirmés"),
    ("Rules for artisanal fishing in Senegal", "Cadre : la pêche artisanale"),
]

NEGATIVE = [
    "Une excursion en pirogue dans le delta du Saloum",
    "Où manger du poisson frais à Soumbédioune ?",
    "Permis de pêche sportive à Saly",
    "Je veux faire de la pêche au gros à Saly",
    "Un jus de pêche, ça existe au Sénégal ?",
    "Visiter un village de pêcheurs à Joal",
    "Peut-on pêcher à Dakar ?",
    "Je cherche un permis de conduire pour louer une voiture",
    "Le marché au poisson de Kayar",
    "Que voir à Joal-Fadiouth ?",
    "Parle-moi de Gorée",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert names.count("peche_artisanale") == 1 and "peche_artisanale" in practical_facts._SPECIFIC_FIRST
    for _, pattern, facts in peche_artisanale.TOPICS:
        re.compile(pattern)
        assert facts and all(fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_fact(question, expected):
    assert "peche_artisanale" in matching_topics(question), question
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "peche_artisanale" not in matching_topics(question), question
    assert "Cadre : la pêche artisanale" not in practical_context(question), question


def test_no_fee_or_date_of_closed_season_is_invented():
    assert "FCFA" not in ALL_FACTS and "redevance" in ALL_FACTS.lower()
    numbers = {n.strip() for n in re.findall(r"\d+(?:\s\d{3})*", ALL_FACTS)}
    # loi n° 2015-18 du 13 juillet 2015 ; pirogues de 0 à 13 mètres ; ANSD 2012.
    assert numbers <= {"2015", "18", "13", "0", "2012"}, numbers
    assert "ne sont pas confirmées" in ALL_FACTS or "non confirmés" in ALL_FACTS
    assert "Les dates en vigueur ne sont pas confirmées ici" in ALL_FACTS


def test_tourism_questions_about_pirogues_and_sport_fishing_keep_other_topics():
    assert "peche_artisanale" not in matching_topics("Combien coûte une sortie en pirogue à Palmarin ?")
    assert "peche_artisanale" not in matching_topics("Où faire de la pêche sportive au Sénégal ?")
