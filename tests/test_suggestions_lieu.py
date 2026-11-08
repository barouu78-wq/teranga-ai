"""Suggestions sous une réponse (`ux_hints.followups`) : le lieu n'est ajouté que s'il s'écrit bien.

Vu le 8 novembre 2026 dans la capture de la vidéo « visa » : « Que faire ensuite ? à senegal ». Le serveur collait
« à <lieu normalisé> » à chaque suggestion, y compris après un point d'interrogation, pour le pays entier ou une
région (« à casamance »), et sans majuscule ni accent (« Options à saint-louis »).
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.intelligence import build_intent_context, build_ux_hints  # noqa: E402


def suggestions(intent, place):
    return build_ux_hints({"intent": intent, "location": place}, {"place": place})["followups"]


def test_la_question_visa_n_a_plus_de_suggestion_mal_formee():
    followups = build_intent_context("Faut-il un visa pour le Sénégal ?")["ux_hints"]["followups"]
    assert followups == ["Préciser ma demande", "Comparer", "Que faire ensuite ?"]


@pytest.mark.parametrize("place", ["dakar", "senegal", "casamance", "lac rose"])
def test_une_suggestion_en_question_ne_recoit_jamais_de_lieu(place):
    assert "Que faire ensuite ?" in suggestions("general_information", place)


@pytest.mark.parametrize(("place", "attendu"), [
    ("dakar", "Options à Dakar"),
    ("saint-louis", "Options à Saint-Louis"),
    ("goree", "Options à Gorée"),
    ("thies", "Options à Thiès"),
    ("kedougou", "Options à Kédougou"),
    ("ziguinchor", "Options à Ziguinchor"),
])
def test_une_ville_s_ecrit_avec_majuscule_et_accents(place, attendu):
    assert suggestions("restaurant", place)[0] == attendu


@pytest.mark.parametrize("place", ["senegal", "casamance", "lac rose", "delta du saloum", "aibd", "<b>x</b>"])
def test_un_lieu_qui_ne_prend_pas_a_reste_hors_du_libelle(place):
    # « au Sénégal », « en Casamance », « au lac Rose » : sans le lieu, la suggestion reste une relance du fil.
    assert suggestions("restaurant", place) == ["Options", "Prix", "Localiser"]
