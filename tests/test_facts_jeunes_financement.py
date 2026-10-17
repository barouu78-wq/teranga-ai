"""Repères « jeunes_financement » (services/facts/jeunes_financement.py) : DER/FJ, ANPEJ, 3FPT."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import jeunes_financement  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in jeunes_financement.TOPICS for fact in facts)

POSITIVE = [
    ("Comment obtenir un financement DER/FJ ?", "guichet public de financement"),
    ("Comment fonctionne la DER FJ pour les femmes ?", "Entrepreneuriat rapide des Femmes et des Jeunes"),
    ("C'est quoi le nano-crédit ?", "petits prêts"),
    ("Qu'est-ce que l'ANPEJ ?", "accueille, informe et oriente"),
    ("Comment avoir un bon de formation du 3FPT ?", "campagne terminée"),
    ("Quels financements pour les jeunes entrepreneurs au Sénégal ?", "guichet public de financement"),
    ("Y a-t-il un programme d'emploi des jeunes au Sénégal ?", "ANPEJ"),
    ("BE YES, comment s'inscrire ?", "programme d'accompagnement de la DER/FJ"),
    ("Où trouver un prêt pour les jeunes entrepreneurs ?", "DER/FJ"),
    ("Youth employment programs in Senegal", "DER/FJ"),
]

NEGATIVE = [
    "Je cherche un emploi à Dakar",
    "Quel est le taux de chômage au Sénégal ?",
    "Où sortent les jeunes de Dakar le soir ?",
    "Un bon de réduction pour un restaurant",
    "Financement de mon voyage au Sénégal",
    "Mon fils veut faire une formation de cuisinier",
    "Quel est le meilleur moment pour partir ?",
    "Un bon plan pour dormir à Saly",
    "Parle-moi de Gorée",
    "Quelle est la différence entre un prêt et un don ?",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert names.count("jeunes_financement") == 1 and "jeunes_financement" in practical_facts._SPECIFIC_FIRST
    for _, pattern, facts in jeunes_financement.TOPICS:
        re.compile(pattern)
        assert facts and all(fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_fact(question, expected):
    assert "jeunes_financement" in matching_topics(question), question
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "jeunes_financement" not in matching_topics(question), question
    assert "DER/FJ : la Délégation" not in practical_context(question), question


def test_existing_business_and_studies_topics_are_unchanged():
    assert matching_topics("Comment créer une entreprise au Sénégal ?") == ["entreprise"]
    assert matching_topics("Comment s'inscrire à Campusen après le bac ?") == ["etudes"]


def test_no_amount_and_the_unconfirmed_rate_is_flagged():
    assert "FCFA" not in ALL_FACTS
    numbers = {n.strip() for n in re.findall(r"\d+(?:\s\d{3})*", ALL_FACTS.replace("3FPT", "FPT"))}
    # 2025 (tournées), 2026 (campagne), 2018 (ANPEJ), 5 000 bons, 1er au 5 octobre, 15 à 40 ans, 90 % non confirmé.
    assert numbers <= {"2025", "2026", "2027", "2018", "5 000", "1", "5", "15", "40", "90"}, numbers
    assert "non confirmé, à vérifier" in ALL_FACTS
    assert "campagne terminée" in ALL_FACTS


def test_every_scheme_points_to_its_organism_and_warns_against_paying_intermediaries():
    for marker in ("der.sn", "anpej.sn", "site du 3FPT"):
        assert marker in ALL_FACTS
    assert "aucun « frais de dossier »" in ALL_FACTS
