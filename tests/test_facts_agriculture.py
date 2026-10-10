"""Repères « agriculture » (services/facts/agriculture.py) : campagne agricole, intrants, alerte de l'ANACIM."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import agriculture  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in agriculture.TOPICS for fact in facts)

POSITIVE = [
    ("Quand commence la campagne agricole au Sénégal ?", "Campagne agricole 2026/2027"),
    ("Comment obtenir des semences et des engrais ?", "commissions de distribution"),
    ("Quand faire les semis de mil ?", "faux départs agricoles"),
    ("Je suis agriculteur à Kaffrine, quelles aides existent ?", "DER/FJ"),
    ("Comment financer un projet de maraîchage ?", "DER/FJ"),
    ("Parle-moi de la culture de l'arachide", "ministère de l'Agriculture"),
    ("Qu'est-ce que l'ISRA ?", "à l'ISRA"),
    ("How do farmers get fertilizer in Senegal?", "au moins 30 % des semences et engrais"),
    ("Les paysans manquent d'engrais cette année", "services agricoles locaux"),
]

NEGATIVE = [
    "Que voir à Joal-Fadiouth ?",
    "Qu'est-ce que le thiéboudienne ?",
    "Comment se passe la récolte du sel au Lac Rose ?",
    "Quand est la saison des pluies au Sénégal ?",
    "Quel temps fait-il à Dakar ?",
    "Comment créer une entreprise au Sénégal ?",
    "Cultiver sa curiosité à Dakar",
    "Parle-moi de la culture sénégalaise et de ses traditions",
    "Quelle est la différence entre une semaine à Dakar et une semaine à Saint-Louis ?",
    "Un hôtel près de la plage à Saly",
    "Raconte l'histoire de Saint-Louis",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert names.count("agriculture") == 1 and "agriculture" in practical_facts._SPECIFIC_FIRST
    for _, pattern, facts in agriculture.TOPICS:
        re.compile(pattern)
        assert facts and all(fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_fact(question, expected):
    assert "agriculture" in matching_topics(question), question
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "agriculture" not in matching_topics(question), question
    assert "Campagne agricole 2026/2027" not in practical_context(question), question


def test_season_question_keeps_its_own_topic():
    assert matching_topics("Quand est la saison des pluies ?") == ["saison"]


def test_no_amount_price_or_subsidy_rate_is_invented():
    assert "FCFA" not in ALL_FACTS and "tonnes" not in ALL_FACTS and "subvention" not in ALL_FACTS.lower()
    numbers = {n.strip() for n in re.findall(r"\d+(?:\s\d{3})*", ALL_FACTS)}
    # 2026/2027 ; 30 juin ; 34 mesures ; 30 % ; Kaffrine 2021.
    assert numbers <= {"2026", "2027", "30", "34", "2021"}, numbers


def test_dated_items_say_so_and_unknowns_are_sent_to_the_authority():
    assert "en 2026" in ALL_FACTS and "30 juin 2026" in ALL_FACTS
    assert "ne sont pas confirmés" in ALL_FACTS and "non confirmées" in ALL_FACTS
