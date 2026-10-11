"""Recherche web : elle se déclenche pour les questions dont la réponse change, et ne se limite aux sites officiels
que lorsque la réponse EST une information officielle.

Constat (84 questions de vérification réalistes, sans réseau) : 39 ne déclenchaient pas la recherche web, parce que
la liste de mots ignorait les pluriels (« vols », « restaurants », « taxis », « pharmacies », « manifestations »,
« résultats ») et des sujets entiers (TVA, SMIG, dengue, choléra, coupures d'électricité, embouteillages, concours,
année scolaire, change, Western Union…). À l'inverse, un restaurant, un horaire de TER ou un prix était cherché
uniquement sur trois ou quatre sites de l'État (agriculture.gouv.sn, transports.gouv.sn, ansd.sn…), où la réponse
n'existe pas.

Chaque cas négatif a son cas positif voisin.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.model_params import build_model_kwargs  # noqa: E402
from services.web_policy import preferred_domains, reasoning_effort, search_context_size, should_use_web  # noqa: E402

# La réponse change : la vérification web est attendue.
AVEC_WEB = [
    # pluriels
    "Quels vols pour Dakar en décembre ?",
    "Y a-t-il des vols directs Paris Dakar ?",
    "Quels sont les meilleurs restaurants de Dakar ?",
    "Les restaurants de Saint-Louis",
    "Où trouver des taxis à Dakar la nuit ?",
    "Quelles pharmacies de garde à Dakar ?",
    "Y a-t-il des manifestations à Dakar ?",
    "Résultats du bac 2026",
    "Quels sont les événements culturels à Dakar ?",
    "Quelles sont les offres d'emploi à Dakar ?",
    "Quels sont les hôpitaux ouverts la nuit à Dakar ?",
    # impôts, salaires, frais
    "Quelle est la TVA au Sénégal ?",
    "Quel est le SMIG au Sénégal ?",
    "Quels sont les frais de Western Union ?",
    "Le loyer moyen à Dakar",
    "Quel est le montant des frais de scolarité à l'UCAD ?",
    # santé publique
    "Quelle est la situation de la dengue à Dakar ?",
    "Y a-t-il une épidémie de choléra au Sénégal ?",
    # perturbations
    "Y a-t-il des embouteillages sur la VDN ?",
    "Les coupures d'électricité à Dakar",
    "Y a-t-il des pannes de courant à Dakar ?",
    "Y a-t-il des manifs à Dakar ?",
    # emploi, école
    "Recrutement fonction publique 2026",
    "Les concours de la fonction publique",
    "Quand commence l'année scolaire ?",
    "Résultats du BFEM",
    # change, transports, démarches
    "Où changer mes euros à Dakar ?",
    "Quelles compagnies aériennes volent vers Dakar ?",
    "Quel est le meilleur opérateur mobile ?",
    "Comment obtenir un permis de conduire au Sénégal ?",
    "Quels papiers pour voyager au Sénégal avec un bébé ?",
    "Ça coûte combien d'aller à Gorée ?",
    # sport, politique, voyage
    "Quand joue les Lions de la Teranga ?",
    "Qui est l'entraîneur des Lions ?",
    "Qui dirige le Sénégal ?",
    "Quelles sont les consignes de voyage de la France pour le Sénégal ?",
    # sujets des repères sourcés (#419, #422, #425), avec et sans accents
    "Que dit le nouveau code du travail ?",
    "Mon employeur peut-il me licencier ? Quel licenciement est abusif ?",
    "Quelle est la durée du congé de maternité ?",
    "Que fait l'inspection du travail ?",
    "Comment faire une déclaration de naissance ?",
    "Comment fonctionne une mutuelle de santé ?",
    "Que prévoit l'assurance maladie universelle ?",
    "Que contient le code de la sécurité sociale de 2026 ?",
    "La césarienne est-elle gratuite ?",
    "Où faire une dialyse à Dakar ?",
    "Que fait un poste de santé ?",
    "Quand commence la campagne agricole ?",
    "Où trouver des semences et de l'engrais ?",
    "Comment obtenir un permis de pêche ?",
    "Quelles sont les dates du repos biologique ?",
    "Comment obtenir des bons de formation ?",
    "C'est quoi le 3FPT ?",
    "Comment s'inscrire à l'ANPEJ ?",
    "Comment fonctionne le nano-crédit de la DER/FJ ?",
    "code du travail", "licenciement", "conge de maternite", "smig", "salaire minimum", "inspection du travail",
    "declaration de naissance", "mutuelle de sante", "assurance maladie universelle", "code de la securite sociale",
    "cesarienne", "dialyse", "poste de sante", "campagne agricole", "semences", "engrais", "permis de peche",
    "repos biologique", "bons de formation", "3fpt", "anpej", "nano-credit",
]

# La réponse est stable : pas de recherche web (coût et délai inutiles).
SANS_WEB = [
    "Quelle est la capitale du Sénégal ?",
    "Qui est Senghor ?",
    "Raconte l'histoire de Gorée",
    "Comment dit-on merci en wolof ?",
    "C'est quoi le thieboudienne ?",
    "Que voir à Saint-Louis ?",
    "Parle-moi de la Casamance",
    "Quelles sont les langues du Sénégal ?",
    "Qui était Lat Dior ?",
    "Quelle est la signification de Teranga ?",
    "Mon fils a du travail scolaire à faire",
    "Je travaille dans le tourisme à Dakar",
    "Je cherche un travail à Dakar",
    "Raconte-moi l'histoire du Fouta",
    "Parle-moi des fermes de la Casamance",
    "Quels sont les plats traditionnels de la Casamance ?",
    "Marge sur un sac acheté 5000 FCFA et vendu 8000",
    "Je veux changer de numéro",
    "Mes souvenirs d'enfance à Dakar, comment les écrire dans un livre ?",
    "Comment apprendre le wolof ?",
]


@pytest.mark.parametrize("question", AVEC_WEB)
def test_une_question_dont_la_reponse_change_declenche_la_recherche_web(question):
    assert should_use_web(question), question


@pytest.mark.parametrize("question", SANS_WEB)
def test_une_question_stable_ne_declenche_pas_la_recherche_web(question):
    assert not should_use_web(question), question


def test_le_pluriel_ne_change_pas_le_sens_des_mots_courts():
    # « ter », « sim », « bus » : pas de pluriel automatique sur les mots de moins de 4 lettres ; « ferme » (la ferme).
    assert not should_use_web("Visiter des fermes")
    assert should_use_web("Horaire du TER")


# --- Filtre de domaines : réservé aux informations officielles ---

def _outil(domaine, planner=False):
    kwargs = build_model_kwargs(
        {"use_web": True, "planner": planner, "deep_reasoning": False, "instructions": "i", "input_text": "q",
         "intent_context": {"domain": domaine}},
        model="gpt-test", reasoning_effort=reasoning_effort, search_context_size=search_context_size,
        preferred_domains=preferred_domains, stream=False,
    )
    return kwargs["tools"][0]


@pytest.mark.parametrize("domaine", ["food", "transport", "travel", "economy", "culture", "environment", "general", "business"])
def test_restaurants_transports_voyages_et_prix_sont_cherches_sur_tout_le_web(domaine):
    assert preferred_domains(domaine) == ()
    assert "filters" not in _outil(domaine)


@pytest.mark.parametrize("domaine,premier", [
    ("administration", "diplomatie.gouv.sn"), ("society", "ansd.sn"), ("agriculture", "ansd.sn"), ("territory", "ansd.sn"),
])
def test_une_information_officielle_reste_cherchee_sur_les_sites_officiels(domaine, premier):
    domaines = preferred_domains(domaine)
    assert domaines[0] == premier
    # Tous les ministères (sante.gouv.sn, education.gouv.sn, sec.gouv.sn…), pas trois sites seulement.
    assert "gouv.sn" in domaines
    assert _outil(domaine)["filters"]["allowed_domains"] == list(domaines)


def test_la_meteo_reste_limitee_a_l_anacim_et_aux_sites_de_l_etat():
    domaines = preferred_domains("weather")
    assert domaines[:2] == ("anacim.sn", "ansd.sn") and "gouv.sn" not in domaines
    assert _outil("weather")["filters"]["allowed_domains"] == list(domaines)
