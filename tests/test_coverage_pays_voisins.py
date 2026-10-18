"""Thème « pays_voisins » du journal des lacunes (/stats-ia) : mesurer la demande sur les pays voisins.

Le propriétaire veut savoir combien de questions parlent de passer une frontière avant d'investir dans un guide
par pays : chaque question qui reçoit le repère « frontieres » est comptée dans ce thème, sans rien retenir d'elle.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import coverage_log as cl  # noqa: E402
from services.coverage_log import THEME_LABELS, chat_signals, classify, themes_of  # noqa: E402


def _themes(question):
    return themes_of(question, chat_signals({"message": question, "instructions": ""}))


@pytest.mark.parametrize("question", [
    "Faut-il changer de l'argent pour aller à Banjul ?",
    "Comment aller en Casamance en voiture par la Gambie ?",
    "Je vais à Nouakchott par Rosso, quels papiers ?",
    "Quelles sont les frontières du Sénégal ?",
    "Can I drive from Dakar to Banjul?",
])
def test_une_question_sur_un_pays_voisin_est_comptee(question):
    assert "pays_voisins" in _themes(question)


def test_le_repere_frontieres_couvre_le_theme():
    question = "Faut-il changer de l'argent pour aller à Banjul ?"
    signals = chat_signals({"message": question, "instructions": ""})
    assert "repere:frontieres" in signals
    assert classify(question, signals)["pays_voisins"] is True


@pytest.mark.parametrize("question", [
    "Raconte-moi l'histoire de l'empire du Mali et de Soundiata",
    "Médecins sans frontières est présent à Dakar ?",
    "Aller voir les hippopotames du fleuve Gambie au Niokolo-Koba",
    "Quelle est la capitale de la Mauritanie ?",
])
def test_une_question_voisine_n_est_pas_comptee(question):
    assert "pays_voisins" not in _themes(question)


def test_le_theme_a_un_libelle_et_un_lien_vers_son_repere():
    assert THEME_LABELS["pays_voisins"] == "Pays voisins et frontières"
    assert cl._PRACTICAL_THEME["frontieres"] == "pays_voisins"
