"""Sujet « outil_cv » (services/facts/outil_cv.py) : l'IA propose l'outil gratuit /cv à qui parle de CV.

Plan du 21 novembre 2026 (tout sur le CV pour l'emploi) : le chat ne connaissait pas l'outil « Mon CV ». Une personne
qui demandait de l'aide pour son CV recevait un texte dans la conversation, jamais le lien vers l'outil qui le met en
page et l'enregistre en PDF. Le repère ne décrit que ce que fait la page /cv (services/cv.py), rien d'autre.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import matching_topics, practical_context  # noqa: E402
from services.quick_answers import quick_answer  # noqa: E402


@pytest.mark.parametrize(
    "question",
    [
        "Aide-moi à faire mon CV",
        "Comment faire un bon CV pour postuler à Dakar ?",
        "Peux-tu corriger mon curriculum vitae ?",
        "J'ai besoin d'une lettre de motivation pour un stage",
        "Comment écrire une lettre de motivation pour la banque ?",
        "Adapte mon CV à cette offre d'emploi",
        "Can you help me write my CV?",
        "I need a cover letter for a job in Dakar",
    ],
)
def test_une_demande_de_cv_recoit_le_lien_de_l_outil(question):
    assert "outil_cv" in matching_topics(question)
    texte = practical_context(question)
    assert "https://teranga-ai.fr/cv" in texte and "gratuit" in texte


@pytest.mark.parametrize(
    "question",
    [
        "Une voiture de 7 CV consomme combien ?",
        "Le moteur fait 110 cv, c'est puissant ?",
        "Combien de CV fiscaux pour une Peugeot 208 ?",
        "Comment trouver du travail à Thiès ?",
        "Quel est le salaire minimum au Sénégal ?",
        "Je veux un résumé de l'histoire de Gorée",
        "Lettre de réclamation à la Senelec",
    ],
)
def test_une_question_voisine_n_ajoute_pas_l_outil(question):
    assert "outil_cv" not in matching_topics(question)


def test_le_repere_ne_dit_que_ce_que_fait_la_page():
    texte = practical_context("Aide-moi à faire mon CV")
    for fait in ("PDF, Word ou photo", "2 Mo", "9 modèles", "lettre de motivation", "n'invente"):
        assert fait in texte
    # Un outil du site, pas un fait qui change : pas de prix, pas de délai promis.
    assert "FCFA" not in texte and "minutes" not in texte


def test_le_sujet_passe_avant_les_sujets_generaux():
    question = "Aide-moi à faire mon CV pour un emploi à la banque, avec ma carte d'identité et mon numéro Orange Money"
    assert "outil_cv" in matching_topics(question)


def test_une_demande_de_cv_va_au_modele_avec_le_repere():
    """Pas de réponse prête : le modèle aide la personne et lui propose l'outil."""
    assert quick_answer({"message": "Aide-moi à faire mon CV", "language": "fr"}, {}) is None
