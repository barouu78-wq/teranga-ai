"""Trous du contexte de l'IA repérés par /stats-ia et un banc de questions réalistes (24 octobre 2026).

Rien de nouveau n'est inventé : chaque correction rend à l'IA un fait déjà vérifié dans le dépôt.
- « Quelle est la monnaie du Sénégal ? » ne recevait pas le repère « argent » (franc CFA, parité fixe).
- « Quel est le plat national ? » ne recevait pas la fiche du ceebu jën, que la base dit « Plat national ».
- « Que faire au Sénégal en une semaine ? » ne recevait aucune fiche : la base donne maintenant son panorama
  (biens UNESCO et points forts de chaque région) quand une question de voyage ne nomme aucun lieu.
- « Je pars au Sénégal en décembre » ne recevait pas le repère des saisons.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.coverage_log import classify, read_question  # noqa: E402
from services.practical_facts import matching_topics, practical_context  # noqa: E402
from services.quick_answers import quick_answer  # noqa: E402
from services.senegal_knowledge import format_senegal_knowledge  # noqa: E402

KNOWLEDGE = app_module.SENEGAL_KNOWLEDGE


def _base(question):
    return format_senegal_knowledge(KNOWLEDGE, query=question, people=app_module.SENEGAL_PEOPLE)


def _payload(message):
    with app_module.app.test_request_context("/chat", method="POST", json={"message": message, "language": "fr"}):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


# --- Monnaie --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Quelle est la monnaie du Sénégal ?",
    "Quelle monnaie utilise-t-on au Sénégal ?",
    "Il faut prévoir de la monnaie pour les taxis ?",
    "What currency is used in Senegal?",
])
def test_une_question_sur_la_monnaie_recoit_le_repere_argent(question):
    assert "argent" in matching_topics(question)
    assert "655,957" in practical_context(question)


@pytest.mark.parametrize("question", [
    "Quelle est la devise du Sénégal ?",  # la devise nationale (une phrase), pas l'argent
    "Comment dit-on merci en wolof ?",
])
def test_la_devise_nationale_n_est_pas_l_argent(question):
    assert "argent" not in matching_topics(question)


# --- Plat national --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Quel est le plat national du Sénégal ?",
    "Le plat national sénégalais ?",
])
def test_le_plat_national_recoit_la_fiche_du_ceebu_jen(question):
    context = _base(question)
    assert "PLATS ET BOISSONS PERTINENTS" in context
    assert "Ceebu jën (thiéboudienne)" in context and "Plat national" in context


def test_c_est_quoi_le_plat_national_a_sa_reponse_prete():
    answer = quick_answer({"message": "C'est quoi le plat national ?", "language": "fr"}, {})
    assert answer is not None
    assert answer["reply"].startswith("Ceebu jën (thiéboudienne)")
    assert "Plat national, inscrit au patrimoine culturel immatériel de l'UNESCO en 2021." in answer["reply"]


# --- Voyage sans lieu précis ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Que faire au Sénégal en une semaine ?",
    "Je pars au Sénégal en décembre, des conseils ?",
    "Quels sont les incontournables du Sénégal ?",
    "Que visiter au Sénégal ?",
    "Itinéraire de 10 jours au Sénégal",
    "Idées de vacances au Sénégal",
    # Relecture Codex de #520 : une fiche qui parle d'enfants (parc de Hann) ne doit pas remplacer le panorama.
    "Que faire au Sénégal en une semaine avec des enfants ?",
])
def test_une_question_de_voyage_sans_lieu_recoit_le_panorama_de_la_base(question):
    context = _base(question)
    assert "PANORAMA DU SÉNÉGAL" in context
    for site in KNOWLEDGE["unesco_world_heritage"]:
        assert site in context
    # Toutes les régions, pas seulement Dakar (règle du prompt : ne pas réduire le Sénégal à Dakar).
    for region in ("Dakar", "Saint-Louis", "Kédougou", "Ziguinchor", "Fatick", "Matam"):
        assert f"{region} :" in context
    assert "Pays Bassari" in context and "Delta du Saloum" in context


@pytest.mark.parametrize("question", [
    "Que visiter à Dakar ?",                         # un lieu nommé : ses fiches suffisent
    "Que faire en Casamance ?",
    "Quelles sont les plus belles plages du Sénégal ?",  # la base trouve déjà des plages
    "Que faire en cas d'accident ?",
    "Quels papiers pour un séjour au Sénégal ?",     # démarche, pas visite
    "Quels vaccins pour voyager au Sénégal ?",
    "Comment créer une entreprise ?",
    "Comment ça marche ?",
    "Mon séjour en prison",
    "Que faire contre le paludisme ?",
    "Quoi faire ce soir ?",
    "Je veux visiter un appartement à louer",
    "Je veux partir travailler en France",
])
def test_pas_de_panorama_hors_d_une_question_de_visite_sans_lieu(question):
    assert "PANORAMA DU SÉNÉGAL" not in _base(question)


def test_le_panorama_arrive_jusqu_au_contexte_du_chat_et_couvre_le_voyage():
    payload = _payload("Que faire au Sénégal en une semaine ?")
    assert "PANORAMA DU SÉNÉGAL" in payload["instructions"]
    assert classify(*read_question(payload, KNOWLEDGE["places"])) == {"voyage": True}


# --- Saison quand un mois de voyage est cité ------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Je pars au Sénégal en décembre, des conseils ?",
    "On part en vacances au Sénégal en août",
    "Voyage à Dakar en février, il fait quel temps ?",
    "Je veux visiter le Sénégal en juillet",
])
def test_un_mois_de_voyage_recoit_le_repere_des_saisons(question):
    assert "saison" in matching_topics(question)


@pytest.mark.parametrize("question", [
    "Je pars à la retraite en janvier",
    "Inscription à l'université en octobre",
    "C'est quand la Tabaski en juin ?",
    "Je vais à la mairie en mars pour mon acte de naissance",
    "Je rends visite à ma mère en janvier",  # relecture Codex de #520 : une visite ordinaire n'est pas un voyage
    "Je pars en mission en mars",
])
def test_un_mois_hors_voyage_ne_donne_pas_les_saisons(question):
    assert "saison" not in matching_topics(question)
