"""Repères « naissance » (services/facts/naissance.py) : déclaration de naissance au Sénégal, sans faux déclenchement."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import naissance  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in naissance.TOPICS for fact in facts)

POSITIVE = [
    ("Comment déclarer la naissance de mon enfant au Sénégal ?", "jusqu'à 45 jours après la naissance"),
    ("Quel est le délai pour la déclaration de naissance ?", "certains sites juridiques citent 30 jours"),
    ("Mon enfant n'a jamais été déclaré, il a trois ans", "autorisation d'inscription tardive de naissance"),
    ("Ma fille est née à la maison, où la déclarer à la naissance ?", "y compris pour une naissance à domicile"),
    ("Que veut dire déclaration tardive pour un acte de naissance ?", "mention « déclaration tardive »"),
    ("C'est quoi l'ANEC, l'Agence nationale de l'État civil ?", "Agence nationale de l'État civil, ANEC"),
    ("Mon bébé est né à Thiès, comment l'enregistrer à la mairie ?", "centre d'état civil"),
    ("Comment obtenir un jugement supplétif ?", "président du tribunal d'instance"),
    ("Naissance non déclarée depuis plus d'un an, que faire ?", "Après un an"),
    ("How do I register my baby's birth in Senegal?", "centre d'état civil"),
]

NEGATIVE = [
    "Quelle est la date de naissance de Léopold Sédar Senghor ?",
    "Où est né Youssou N'Dour ?",
    "Je dois déclarer mes revenus d'entreprise",
    "Comment déclarer un objet à la douane ?",
    "Quel est le taux de natalité et de naissances au Sénégal ?",
    "Il n'a pas déclaré ses revenus à l'administration",
    "Mon enfant va à l'école près de la mairie de Dakar",
    "Je cherche une maternité pour accoucher à Dakar",
    "Comment inscrire mon enfant à l'école ?",
    "Parle-moi de Gorée",
    "Quels sont les numéros d'urgence au Sénégal ?",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert names.count("naissance") == 1 and "naissance" in practical_facts._SPECIFIC_FIRST
    for _, pattern, facts in naissance.TOPICS:
        re.compile(pattern)
        assert facts and all(fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_fact(question, expected):
    assert "naissance" in matching_topics(question), question
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "naissance" not in matching_topics(question), question
    assert "Naissance survenue au Sénégal" not in practical_context(question), question


def test_existing_papers_topic_keeps_its_questions_and_the_new_one_completes_it():
    # « extrait de naissance » reste du sujet « papiers » seul (test historique de practical_facts).
    assert matching_topics("Comment avoir un extrait de naissance ?") == ["papiers"]
    names = matching_topics("Comment faire un jugement supplétif pour un acte de naissance ?")
    assert "papiers" in names and "naissance" in names


def test_the_deadlines_come_from_the_official_agency_and_no_amount_is_given():
    # 45 jours et un an : ANEC ; aucun coût inventé.
    assert "45 jours" in ALL_FACTS and "un an" in ALL_FACTS
    assert "FCFA" not in ALL_FACTS and "gratuit" not in ALL_FACTS.lower()
    assert "non confirmé" in ALL_FACTS


def test_scope_is_limited_to_births_in_senegal():
    assert "naissance à l'étranger" in ALL_FACTS and "ambassade ou au consulat" in ALL_FACTS
