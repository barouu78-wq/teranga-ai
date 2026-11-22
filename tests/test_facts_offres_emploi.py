"""Sujet « offres_emploi » (services/facts/offres_emploi.py) : à qui cherche un emploi, l'IA propose /offres-emploi.

Décision du propriétaire du 22 novembre 2026 (« on met juste leur lien ») : la page /offres-emploi renvoie vers des
sites d'offres vérifiés. Le chat ne la connaissait pas. Le repère ne décrit que la page, sans offre ni employeur :
Teranga ne lit pas les offres de ces sites.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.practical_facts import matching_topics, practical_context  # noqa: E402


@pytest.mark.parametrize(
    "question",
    [
        "Où trouver des offres d'emploi au Sénégal ?",
        "Comment trouver du travail à Thiès ?",
        "Je cherche un emploi à Dakar",
        "Je cherche un stage en comptabilité",
        "Quels sont les sites d'emploi au Sénégal ?",
        "Des offres de stage pour étudiants ?",
        "Aide-moi dans ma recherche d'emploi",
        "Where can I find a job in Dakar?",
        "Any job offers in Senegal?",
    ],
)
def test_une_recherche_d_emploi_recoit_le_lien_de_la_page(question):
    assert "offres_emploi" in matching_topics(question)
    texte = practical_context(question)
    assert "https://teranga-ai.fr/offres-emploi" in texte and "https://teranga-ai.fr/cv" in texte


@pytest.mark.parametrize(
    "question",
    [
        "Quel est l'emploi du temps des écoles ?",
        "Où trouver le mode d'emploi de mon décodeur ?",
        "Que dit le droit du travail sur les congés ?",
        "Les travaux de la VDN sont finis ?",
        "Je cherche un restaurant à Saly",
        "Comment trouver un taxi à l'aéroport ?",
        "Le travail des enfants au Sénégal",
        "Aide-moi à faire mon CV",
    ],
)
def test_une_question_voisine_n_ajoute_pas_la_page(question):
    assert "offres_emploi" not in matching_topics(question)


def test_le_repere_ne_cite_aucune_offre_et_rappelle_de_ne_jamais_payer():
    texte = practical_context("Je cherche un emploi à Dakar")
    for fait in ("Emploi Dakar", "Senjob", "Concoursn", "ANPEJ", "22 novembre 2026", "jamais d'argent"):
        assert fait in texte
    assert "FCFA" not in texte
