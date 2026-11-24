"""Repères « wolof » (services/facts/wolof.py) : bases de débutant, à faire relire par un locuteur."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import wolof  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in wolof.TOPICS for fact in facts)

POSITIVE = [
    ("Comment dit-on merci en wolof ?", "« Jërëjëf »"),
    ("Comment dire bonjour en wolof ?", "« Salaam aleekum »"),
    ("Les nombres en wolof de 1 à 10", "juróom-benn (5 + 1)"),
    ("Apprendre le wolof : quelles phrases de base ?", "repères de débutant"),
    ("Que veut dire Nanga def ?", "« Maa ngi fi rekk »"),
    ("Que veut dire Baal ma ?", "excusez-moi, pardon"),
    ("What does jerejef mean?", "« Jërëjëf »"),
    ("How do you say hello in Wolof?", "« Salaam aleekum »"),
    ("Je voudrais parler wolof avec ma belle-famille", "repères de débutant"),
    ("Excuse me in Wolof, how do I say it?", "« Baal ma »"),
    ("Compter jusqu'à dix en wolof", "fukk"),
    ("Salutations en wolof pour un voyageur", "à la prochaine"),
]

NEGATIVE = [
    "Les Wolofs sont-ils majoritaires au Sénégal ?",
    "L'histoire de l'empire du Djolof et des Wolofs",
    "Quelles langues parle-t-on au Sénégal ?",
    "Quels mots français viennent du wolof ?",
    "Parle-moi de la langue wolof et de son histoire",
    "Je parle français et anglais",
    "Le thiéboudienne est un plat wolof",
    "Bonjour, je cherche un hôtel à Dakar",
    "Merci pour votre aide",
    "Où apprendre le français à Dakar ?",
    "Combien de personnes parlent wolof ?",
    "Parle-moi de Gorée",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert names.count("wolof") == 1 and "wolof" in practical_facts._SPECIFIC_FIRST
    for _, pattern, facts in wolof.TOPICS:
        re.compile(pattern)
        assert facts and all(fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_expression(question, expected):
    assert "wolof" in matching_topics(question), question
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "wolof" not in matching_topics(question), question
    assert "Wolof, repères de débutant" not in practical_context(question), question


def test_the_languages_topic_keeps_its_own_questions():
    assert matching_topics("Quelles langues parle-t-on au Sénégal ?") == ["langue"]


def test_the_ai_is_told_the_expressions_are_unreviewed_and_spelling_varies():
    assert "n'ont pas été relues par un locuteur" in ALL_FACTS
    assert "l'orthographe varie" in ALL_FACTS
    assert "conseiller de les faire confirmer par un locuteur" in ALL_FACTS


def test_numbers_one_to_ten_are_complete_and_nothing_beyond_is_invented():
    for word in ("benn", "ñaar", "ñett", "ñeent", "juróom", "juróom-benn", "juróom-ñaar", "juróom-ñett", "juróom-ñeent", "fukk"):
        assert word in ALL_FACTS, word
    # Au-delà de 10 et les prix : explicitement non confirmés, aucune expression inventée.
    assert "Au-delà de 10 et pour les prix : non confirmé" in ALL_FACTS
    for invented in ("ñaata", "fukk ak", "téeméer", "junni", "s'il vous plaît"):
        assert invented not in ALL_FACTS, invented
