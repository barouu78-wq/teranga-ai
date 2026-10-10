"""Repères « travail » (services/facts/travail.py) : bonnes questions détectées, aucune question voisine captée,
aucun chiffre non sourcé, contexte réellement transmis à l'IA."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import travail  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in travail.TOPICS for fact in facts)

# (question, phrase exacte attendue dans le contexte)
POSITIVE = [
    ("Quel est le salaire minimum au Sénégal ?", "ne pas en donner de mémoire"),
    ("C'est quoi le SMIG au Sénégal ?", "SMIG (salaire minimum interprofessionnel garanti)"),
    ("Combien de jours de congés payés ai-je droit ?", "peuvent donc avoir changé"),
    ("Mon patron m'a licencié sans préavis, que faire ?", "inspection du travail de sa région"),
    ("Quelle est l'indemnité de licenciement ?", "ne pas les citer de mémoire"),
    ("Le congé de maternité dure combien de semaines au Sénégal ?", "porté de 14 à 18 semaines"),
    ("Y a-t-il un nouveau Code du travail au Sénégal ?", "loi n° 2026-18 du 3 septembre 2026"),
    ("Quelle est la durée maximale d'un CDD ?", "ne donner aucun chiffre sans avoir lu le texte officiel"),
    ("Mon employeur ne me paie plus mon salaire depuis trois mois", "garder le contrat, les bulletins de paie"),
    ("Le télétravail est-il autorisé au Sénégal ?", "cadre pour le télétravail"),
    ("Où se plaindre à l'inspection du travail à Dakar ?", "juge du travail"),
    ("Quelle est la période d'essai dans un contrat de travail ?", "Nouveau Code du travail"),
    ("What is the minimum wage in Senegal?", "SMIG (salaire minimum interprofessionnel garanti)"),
    ("Is there a labour law in Senegal?", "loi n° 2026-18"),
    ("I was a victim of unfair dismissal in Dakar", "inspection du travail"),
]

# Questions voisines : elles ne parlent pas de droit du travail, rien ne doit être ajouté.
NEGATIVE = [
    "Mon fils a du travail scolaire à faire",
    "Je travaille dans le tourisme à Dakar",
    "Je cherche un travail à Dakar",
    "Le travail des enfants dans les mines de Kédougou",
    "Je veux faire une licence en droit à l'UCAD",
    "Quel préavis pour quitter mon logement à Dakar ?",
    "Préavis de grève des enseignants",
    "Où partir en congés au Sénégal ?",
    "Un contrat de location pour une villa à Saly",
    "Quel est le salaire d'un médecin ?",
    "Mon patron de restaurant à Saint-Louis est très gentil",
    "Les droits de l'homme au Sénégal",
    "Raconte l'histoire de Saint-Louis",
    "Parle-moi de Gorée",
    "Je suis volontaire pour une ONG au Sénégal",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert "travail" in names and names.count("travail") == 1
    assert "travail" in practical_facts._SPECIFIC_FIRST
    for name, pattern, facts in travail.TOPICS:
        re.compile(pattern)
        assert facts and all(isinstance(fact, str) and fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_fact(question, expected):
    assert "travail" in matching_topics(question)
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "travail" not in matching_topics(question), question
    assert "Nouveau Code du travail" not in practical_context(question), question


def test_no_unsourced_figure_or_article_of_the_old_code():
    # Aucun montant, aucune durée, aucun numéro d'article de l'ancien code : seules deux dates et trois chiffres
    # sourcés (loi 2026-18, loi 97-17 remplacée, 14 -> 18 semaines, 50 textes d'application) sont permis.
    assert "FCFA" not in ALL_FACTS and "F CFA" not in ALL_FACTS
    assert not re.search(r"\bL\.? ?\d{2,3}\b", ALL_FACTS)
    assert not re.search(r"jours ouvrables|par mois de service|mois de préavis|semaines de congé", ALL_FACTS)
    numbers = set(re.findall(r"\d[\d  ]*\d|\d", ALL_FACTS))
    allowed = {"2026", "18", "3", "17", "97", "1997", "14", "50", "1", "2018", "2023", "2"}
    unexpected = {n.strip() for n in numbers} - allowed
    assert not unexpected, f"chiffres non prévus (à sourcer ou retirer) : {unexpected}"


def test_every_claim_that_can_change_is_marked_to_verify():
    assert ALL_FACTS.count("à vérifier") >= 2
    assert "selon la presse" in ALL_FACTS or "par la presse" in ALL_FACTS


def test_labour_topic_comes_before_generic_topics_when_the_limit_cuts():
    # « perdu » déclenche aussi « urgences » : le sujet précis passe avant.
    names = matching_topics("J'ai perdu mon emploi après un licenciement, que faire ?")
    assert names[0] == "travail" and "urgences" in names


def test_other_topics_keep_their_own_answers():
    assert matching_topics("C'est quoi la CMU ?") == ["protection"]
    assert matching_topics("Comment renouveler ma carte d'identité ?") == ["papiers"]
    assert matching_topics("Comment créer une entreprise au Sénégal ?") == ["entreprise"]
    # Un sujet voisin ne vole pas la question de travail : la retraite reste « protection » (+ travail si dit).
    assert "protection" in matching_topics("Comment cotiser à l'IPRES pour ma retraite ?")
    assert "travail" not in matching_topics("Comment cotiser à l'IPRES pour ma retraite ?")
