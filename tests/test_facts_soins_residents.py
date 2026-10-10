"""Repères « soins_residents » (services/facts/soins_residents.py) : soins publics, gratuités, mutuelles, réforme 2026."""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402
from services import practical_facts  # noqa: E402
from services.facts import soins_residents  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402

ALL_FACTS = " ".join(fact for _, _, facts in soins_residents.TOPICS for fact in facts)

POSITIVE = [
    ("Où se faire soigner gratuitement à Dakar ?", "Gratuités"),
    ("C'est quoi un poste de santé et un centre de santé ?", "le système est organisé en pyramide"),
    ("Quel est mon district sanitaire ?", "établissements publics de santé (EPS)"),
    ("Combien coûte la cotisation à une mutuelle de santé ?", "7 000 FCFA par personne"),
    ("Comment adhérer à la CMU ?", "soit 3 500 FCFA pour l'adhérent"),
    ("Quel est le prix de l'inscription à une mutuelle de santé ?", "à vérifier auprès de l'Agence de la CMU"),
    ("La césarienne est-elle gratuite au Sénégal ?", "la césarienne et la dialyse"),
    ("La dialyse est-elle prise en charge ? Soins gratuits ?", "plan Sésame"),
    ("Que prévoit le nouveau Code de la sécurité sociale ?", "assurance maladie universelle en trois régimes"),
    ("Y a-t-il une assurance maladie universelle au Sénégal ?", "projet de loi n° 16/2026"),
    ("Quel est le numéro vert du ministère de la Santé ?", "800 00 50 50"),
    ("Où trouver la liste des hôpitaux régionaux du pays ?", "régions médicales"),
    ("What are the public hospitals like in Senegal?", "le système est organisé en pyramide"),
]

NEGATIVE = [
    "Quel est le meilleur hôpital de Dakar pour un touriste ?",
    "Où trouver une pharmacie de garde à Dakar ?",
    "Faut-il un vaccin contre la fièvre jaune ?",
    "Mon enfant a de la fièvre, que faire ?",
    "Combien coûte une consultation chez un médecin à Dakar ?",
    "Comment cotiser à l'IPRES pour ma retraite ?",
    "Quelle est la cotisation de ma mutuelle d'entreprise en France ?",
    "Combien coûte une assurance voyage santé ?",
    "Le Sénégal a-t-il un bon système de santé ?",
    "Parle-moi de la santé mentale au Sénégal",
    "Parle-moi de Gorée",
    "Les sapeurs-pompiers de Dakar interviennent en combien de temps ?",
]


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


def test_module_is_loaded_and_registered():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert names.count("soins_residents") == 1 and "soins_residents" in practical_facts._SPECIFIC_FIRST
    for _, pattern, facts in soins_residents.TOPICS:
        re.compile(pattern)
        assert facts and all(fact.strip() for fact in facts)


@pytest.mark.parametrize("question,expected", POSITIVE, ids=[q for q, _ in POSITIVE])
def test_question_triggers_the_topic_with_the_exact_fact(question, expected):
    assert "soins_residents" in matching_topics(question), question
    assert expected in practical_context(question)
    assert expected.casefold() in _context(question).casefold()


@pytest.mark.parametrize("question", NEGATIVE)
def test_neighbouring_questions_do_not_trigger_the_topic(question):
    assert "soins_residents" not in matching_topics(question), question
    assert "Soins publics : le système" not in practical_context(question), question


def test_existing_protection_and_urgence_answers_are_unchanged():
    # Tests historiques de practical_facts : « CMU » seul reste du sujet « protection » uniquement.
    assert matching_topics("C'est quoi la CMU ?") == ["protection"]
    assert matching_topics("Quelle est la bourse de sécurité familiale ?") == ["protection"]
    assert matching_topics("Quels sont les numéros d'urgence ?") == ["urgences"]
    # Une question de cotisation reçoit les deux sujets : le général « protection » et le détail « soins_residents ».
    names = matching_topics("Combien coûte la cotisation de la CMU ?")
    assert "protection" in names and "soins_residents" in names


def test_every_figure_has_a_source_and_every_unstable_claim_is_hedged():
    assert "à vérifier" in ALL_FACTS and "pas confirmés" in ALL_FACTS
    numbers = {n.strip() for n in re.findall(r"\d[\d  ]*\d|\d", ALL_FACTS)}
    # 1515 SAMU ; 7 000 / 3 500 FCFA (CMU) ; 0 à 5 ans, 60 ans ; niveaux 1, 2, 3 ; 2016, 2013, 2020, 2026 ; code 16/2026 ;
    # 18 août ; 50 textes ; numéro vert 800 00 50 50 ; « Covid-19 » (19).
    allowed = {"1515", "7 000", "3 500", "0", "5", "60", "1", "2", "3", "2016", "2013", "2020", "2026", "16", "18",
               "50", "800 00 50 50", "000", "19"}
    unexpected = numbers - allowed
    assert not unexpected, f"chiffres non prévus (à sourcer ou retirer) : {unexpected}"


def test_no_invented_tariff_or_hospital_headcount():
    assert not re.search(r"\b\d+ (hôpitaux|centres de santé|postes de santé|districts)\b", ALL_FACTS)
    assert "tarif" not in ALL_FACTS.lower()


def test_new_social_security_code_is_never_presented_as_fully_applicable():
    assert "ne rien promettre" in ALL_FACTS
    assert "ne sont pas confirmés" in ALL_FACTS
