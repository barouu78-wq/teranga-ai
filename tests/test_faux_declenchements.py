"""Faux déclenchements du contexte de l'IA : un mot courant ne doit pas changer le contexte envoyé au modèle.

Mesure sur la branche de la PR #471 (corps de requête de static/home.js, question en dernier élément de history) :
- « bonnes vacances ! », « je pars car j ai fini mes vacances » et « titre de sejour » lançaient le planificateur et le
  modèle complexe (« vacances », « séjour » dans services/intelligence.py) ;
- « le mafe est trop chaud » était une question météo (« chaud » seul) et recevait la prévision ;
- « je suis fatigue car j ai mal dormi » était une question de transport (« car », la conjonction) ;
- « ca n a rien a voir… » et « cartes de visite » lançaient le mode guide (« à voir », « visite ») ;
- « le billet d avion est trop cher » et « une marchande de poisson a soumbedioune » lançaient le mode marché ;
- « passer la douane… » recevait le repère visa (aucun repère douane n'existe) ; « je vends des legumes » ne recevait
  pas le repère vente ;
- « titre de sejour » et « titre foncier » faisaient venir Sadio Mané et Koli Tenguella, « merci en wolof »
  Richard-Toll, Louga et Birago Diop.

Chaque cas négatif a son cas positif voisin, qui doit continuer à déclencher.
"""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.chat_service import select_chat_model  # noqa: E402
from services.practical_facts import matching_topics  # noqa: E402

LUNA, SOL = "gpt-5.6-luna", "gpt-5.6-sol"


def site(*turns, audience="tourist"):
    """Corps de requête comme static/home.js : la question courante est aussi le dernier élément de history."""
    *previous, message = turns
    history = []
    for text in previous:
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": "(réponse)"}]
    history.append({"role": "user", "content": message})
    body = {"message": message, "history": history, "language": "fr", "audience": audience}
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


@pytest.fixture(autouse=True)
def _meteo_simulee(monkeypatch):
    """Météo en direct remplacée par un faux (aucun réseau) qui suit la même condition : intention « weather »."""
    def fake(locations, intent_context, message, *args, **kwargs):
        return "PRÉVISIONS SIMULÉES" if (intent_context or {}).get("intent") == "weather" else None

    monkeypatch.setattr(app_module, "live_weather_context", fake)


def _block(instructions, title):
    if title not in instructions:
        return []
    block = instructions.split(title, 1)[1]
    stop = re.search(r"\n[A-ZÉ][A-ZÉÈ ’']{5,}", block)
    return re.findall(r"^- ([^:(]+?)\s*[:(]", block[: stop.start()] if stop else block, re.M)


def places(payload):
    return _block(payload["instructions"], "LIEUX PERTINENTS :")


def regions(payload):
    return _block(payload["instructions"], "CONTEXTE RÉGIONAL PERTINENT :")


def people(payload):
    return _block(payload["instructions"], "PERSONNALITÉS PERTINENTES :")


def model(payload):
    return select_chat_model(payload, LUNA, SOL)


# « vacances », « séjour » : planificateur et modèle complexe.

@pytest.mark.parametrize("question", [
    "bonnes vacances !",
    "je pars car j ai fini mes vacances",
    "je rentre de vacances demain",
    "titre de sejour",
    "renouveler mon titre de sejour en france",
])
def test_vacances_ou_sejour_sans_projet_ne_lancent_pas_le_planificateur(question):
    payload = site(question)
    assert payload["intent_context"]["intent"] != "trip_planning", question
    assert payload["planner"] is False, question
    assert model(payload) == LUNA, question


@pytest.mark.parametrize("question", [
    "je prepare mes vacances au Senegal",
    "on part en vacances a saly avec les enfants 5 jours",
    "vacances au senegal en decembre quoi faire",
])
def test_un_vrai_projet_de_vacances_lance_toujours_le_planificateur(question):
    payload = site(question)
    assert payload["intent_context"]["intent"] == "trip_planning", question
    assert payload["planner"] is True, question


# « chaud » : météo.

@pytest.mark.parametrize("question", ["le mafe est trop chaud", "le the est trop chaud"])
def test_un_plat_chaud_n_est_pas_une_question_meteo(question):
    payload = site(question)
    assert payload["intent_context"]["intent"] != "weather", question
    assert "PRÉVISIONS SIMULÉES" not in payload["instructions"], question


@pytest.mark.parametrize("question", [
    "il fait chaud a Dakar ?",
    "il fait trop chaud a ziguinchor en avril ?",
    "cest chaud a dakar en ce moment ?",
])
def test_la_chaleur_du_temps_reste_une_question_meteo(question):
    payload = site(question)
    assert payload["intent_context"]["intent"] == "weather", question
    assert "PRÉVISIONS SIMULÉES" in payload["instructions"], question


# « car » : la conjonction n'est pas le car (bus).

@pytest.mark.parametrize("question", ["je suis fatigue car j ai mal dormi", "je pars car j ai fini mes vacances"])
def test_car_conjonction_n_est_pas_un_transport(question):
    assert site(question)["intent_context"]["intent"] != "transport", question


@pytest.mark.parametrize("question", ["le car rapide pour Thies", "prendre le car pour mbour", "gare des cars de thies"])
def test_le_car_bus_reste_un_transport(question):
    assert site(question)["intent_context"]["intent"] == "transport", question


# Mode guide : « à voir », « visite ».

def test_rien_a_voir_ne_lance_pas_le_guide_et_ne_garde_que_le_lac_rose():
    payload = site("ca n a rien a voir mais c est quoi le lac rose")
    assert "guide" not in payload.get("modes", [])
    assert places(payload) == ["Lac Rose / Lac Retba"]
    assert regions(payload) == []


@pytest.mark.parametrize("question", [
    "imprimer des cartes de visite pour ma boutique",
    "carte de visite pas chere dakar",
])
def test_une_carte_de_visite_ne_lance_pas_le_guide(question):
    assert "guide" not in site(question).get("modes", []), question


@pytest.mark.parametrize("question", [
    "que voir a Saint-Louis",
    "visite de Goree",
    "ya quoi a voir a mbour",
    "visiter le lac rose",
])
def test_la_visite_d_un_lieu_garde_le_guide(question):
    assert "guide" in site(question).get("modes", []), question


def test_le_lac_rose_nomme_ne_ramene_ni_le_lac_de_guiers_ni_la_region_de_saint_louis():
    payload = site("visiter le lac rose")
    assert places(payload) == ["Lac Rose / Lac Retba"]
    assert "Saint-Louis" not in regions(payload)


def test_le_lac_de_guiers_nomme_garde_sa_region():
    payload = site("visiter le lac de guiers")
    assert places(payload)[0] == "Lac de Guiers"
    assert "Saint-Louis" in regions(payload)


# Mode marché : « trop cher », « marchande ».

@pytest.mark.parametrize("question", [
    "le billet d avion est trop cher",
    "le resto etait trop cher",
    "ma tante est marchande au marche hlm",
])
def test_trop_cher_ou_une_marchande_ne_lancent_pas_la_negociation(question):
    assert "market" not in site(question).get("modes", []), question


def test_une_marchande_a_soumbedioune_garde_le_lieu_sans_le_mode_marche():
    payload = site("une marchande de poisson a soumbedioune")
    assert "market" not in payload.get("modes", [])
    assert "Soumbédioune" in places(payload)


@pytest.mark.parametrize("question", [
    "negocier au marche Sandaga",
    "je marchande comment au marche hlm",
    "how to haggle at sandaga",
    "C'est trop cher pour un masque, aide-moi à baisser le prix",
    "Combien payer un boubou au marché Sandaga ?",
])
def test_la_negociation_au_marche_garde_le_mode_marche(question):
    assert "market" in site(question, audience="merchant").get("modes", []), question


# Repères pratiques : « douane » n'est pas le visa ; « je vends » est la vente.

@pytest.mark.parametrize("question", [
    "passer la douane avec des medicaments",
    "douane aibd quantite de cigarettes",
    "customs rules for laptop",
])
def test_la_douane_ne_recoit_pas_le_repere_visa(question):
    assert "visa" not in matching_topics(question), question


def test_la_douane_avec_des_medicaments_garde_le_repere_sante():
    assert "sante" in matching_topics("passer la douane avec des medicaments")


@pytest.mark.parametrize("question", ["visa pour le senegal ?", "faut il un passeport pour entrer au senegal"])
def test_le_visa_reste_le_visa(question):
    assert "visa" in matching_topics(question), question


@pytest.mark.parametrize("question", ["je vends des legumes", "nous vendons des tissus en ligne", "je vends du thiakry sur whatsapp"])
def test_je_vends_recoit_le_repere_vente(question):
    assert "vente" in matching_topics(question), question


@pytest.mark.parametrize("question", ["je vends ma voiture", "je vends mon terrain a thies"])
def test_vendre_un_bien_n_est_pas_le_commerce(question):
    assert "vente" not in matching_topics(question), question


# Personnalités et lieux tirés par un mot rare.

@pytest.mark.parametrize("question", ["titre de sejour", "acheter un terrain titre foncier", "titre foncier ou deliberation"])
def test_un_titre_administratif_ne_fait_venir_personne(question):
    payload = site(question, audience="diaspora")
    assert people(payload) == [], question
    assert places(payload) == [], question


def test_le_titre_foncier_garde_son_repere():
    assert "foncier" in matching_topics("acheter un terrain titre foncier")


@pytest.mark.parametrize("question", [
    "comment on dit merci en wolof",
    "traduire bonjour en wolof",
    "apprendre le wolof vite",
])
def test_une_question_de_langue_ne_fait_venir_ni_lieu_ni_personnalite(question):
    payload = site(question)
    assert people(payload) == [], question
    assert places(payload) == [], question
    assert "PHRASES WOLOF SÛRES" in payload["instructions"], question


def test_une_personnalite_nommee_reste_trouvee():
    assert "Birago Diop" in people(site("qui est birago diop"))
    assert "Sadio Mané" in people(site("parle moi de sadio mane"))


def test_un_lieu_nomme_sans_region_ne_ramene_pas_les_regions_du_poisson():
    payload = site("une marchande de poisson a soumbedioune")
    assert regions(payload) == []


def test_un_billet_d_avion_ne_ramene_ni_goree_ni_cap_skirring():
    assert places(site("le billet d avion est trop cher")) == []


def test_un_plat_ou_un_theme_sans_lieu_nomme_garde_ses_regions():
    assert "Saint-Louis" in regions(site("poisson a saint-louis"))
    assert regions(site("ou manger du poisson grille")) != []
