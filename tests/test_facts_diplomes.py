"""Sujet « diplomes » (services/facts/diplomes.py) : faire reconnaître un diplôme (équivalence, CRCE, ANAQ-Sup).

Demande du propriétaire (« Continue », 8 novembre 2026) : la dernière question fréquente de l'accueil sans repère
vérifié, « Comment faire reconnaître un diplôme obtenu à l'étranger ? ». Sources dans services/facts/diplomes.py.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import coverage_log  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402
from services.quick_answers import quick_answer  # noqa: E402


@pytest.mark.parametrize(
    ("question", "phrase"),
    [
        ("Comment faire reconnaître un diplôme obtenu à l'étranger ?", "(CRCE)"),
        ("Comment faire reconnaître un diplôme obtenu à l'étranger ?", "décret n° 2015-582"),
        ("Équivalence de diplôme pour passer un concours de la fonction publique", "concours"),
        ("Quelles pièces pour une équivalence de diplôme ?", "copie légalisée du diplôme"),
        ("Quelles pièces pour une équivalence de diplôme ?", "curriculum vitae"),
        ("Mon diplôme d'une école privée est-il reconnu par l'État ?", "ANAQ-Sup"),
        ("Un doctorat d'une université privée est-il reconnu au Sénégal ?", "ne sont pas reconnus par l'État"),
        ("C'est quoi la CRCE ?", "Commission technique de reconnaissance"),
    ],
)
def test_une_vraie_question_recoit_le_repere(question, phrase):
    assert "diplomes" in matching_topics(question)
    assert phrase in practical_context(question)


@pytest.mark.parametrize(
    "question",
    [
        "Comment s'inscrire à l'université au Sénégal ?",
        "Comment obtenir une bourse d'études ?",
        "Merci pour votre reconnaissance",
        "Reconnaissance faciale à l'aéroport de Dakar",
        "Cérémonie de remise des diplômes à l'UCAD",
        "Je ne reconnais plus Dakar, tout a changé",
        "Mon chien est un chien de race reconnu ?",
    ],
)
def test_une_question_voisine_n_ajoute_pas_le_sujet(question):
    assert "diplomes" not in matching_topics(question)


def test_le_repere_ne_donne_ni_frais_ni_delai_ni_adresse():
    """Aucune source officielle lue ne les donne : ils restent « à vérifier »."""
    texte = practical_context("Comment faire reconnaître un diplôme obtenu à l'étranger ?")
    assert "FCFA" not in texte and "jours" not in texte and "Tél" not in texte
    assert "à vérifier auprès du ministère de la Fonction publique" in texte


def test_la_question_de_l_accueil_recoit_une_reponse_prete():
    answer = quick_answer({"message": "Comment faire reconnaître un diplôme obtenu à l'étranger ?", "language": "fr"}, {})
    assert answer is not None
    assert answer["reply"].startswith("Reconnaissance d'un diplôme")
    assert "Pièces à fournir" in answer["reply"]
    assert answer["theme"] == "etudes"


@pytest.mark.parametrize("message", [
    "Mon diplôme français est-il reconnu au Sénégal ?",
    "Mon doctorat privé est-il reconnu ?",
    "Ma demande d'équivalence de diplôme est refusée, que faire ?",
])
def test_une_situation_va_au_modele(message):
    assert quick_answer({"message": message, "language": "fr"}, {}) is None


def test_le_repere_compte_dans_le_theme_etudes():
    assert coverage_log._PRACTICAL_THEME["diplomes"] == "etudes"
