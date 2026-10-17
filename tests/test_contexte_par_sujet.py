"""Le contexte envoyé à l'IA suit le sujet de la question, pas les quatre tours d'avant.

Mesure sur main (corps de requête de static/home.js, question en dernier élément de history) :
« que voir a kedougou », « et a podor ? », puis « c est quoi le yassa » recevait les fiches Podor et Kédougou,
les régions Saint-Louis et Kédougou, El Hadji Omar Tall, Baaba Maal, Mansour Seck et les deux dossiers du
Fouta-Toro : le choix des lieux (services/senegal_knowledge.py) lisait les quatre derniers tours collés à la
question (services/intelligence.py, contextual_query), même quand le sujet avait changé.

Désormais, une question qui nomme son propre sujet (lieu, plat, dossier historique, langue, repère pratique
national comme la carte SIM ou les urgences) et ne renvoie pas au tour précédent choisit ses fiches seule.
Une vraie relance (« Et à Podor ? », « Combien de temps faut-il pour la visite ? », « Et pour dormir ? »)
garde le lieu du fil.
"""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402


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


def dishes(payload):
    return _block(payload["instructions"], "PLATS ET BOISSONS PERTINENTS :")


def dossiers(payload):
    return re.findall(r"DOSSIER HISTORIQUE — ([^:]+) :", payload["instructions"])


# Le cas du propriétaire.

def test_une_question_sur_un_plat_ne_recoit_pas_les_lieux_des_tours_precedents():
    payload = site("que voir a kedougou", "et a podor ?", "c est quoi le yassa")
    assert "Yassa" in dishes(payload)
    assert not {"Podor", "Kédougou"} & set(places(payload))
    assert not {"Saint-Louis", "Kédougou"} & set(regions(payload))
    assert not any("Fouta" in title for title in dossiers(payload))
    assert not {"El Hadji Omar Tall", "Baaba Maal", "Mansour Seck"} & set(people(payload))


def test_une_vraie_relance_garde_le_lieu_du_tour_precedent():
    # Cas positif voisin : « Et à Podor ? » se comprend avec « que voir » du tour d'avant.
    payload = site("que voir a kedougou", "et a podor ?")
    assert "Podor" in places(payload)


# Nouveau sujet : la question choisit ses fiches seule.

NOUVEAU_SUJET = [
    # (tours précédents, question, fiches qui ne doivent plus venir), quatre profils.
    (("que voir a kedougou", "et a podor ?"), "comment on dit merci en wolof", {"Podor", "Kédougou"}),
    (("visiter saint louis 2 jours",), "numero police stp", {"Île de Saint-Louis", "Podor"}),
    (("que faire a saly",), "quelle carte sim prendre a l aeroport", {"Saly"}),
    (("what to see in casamance",), "how much is a sim card", {"Cap Skirring", "Oussouye"}),
    (("magal touba c quand",), "recette thieboudienne", {"Touba", "Toubab Dialaw"}),
    (("raconte l histoire de goree",), "c est quoi le mafe", {"Île de Gorée"}),
    (("comment negocier au marche sandaga",), "quel temps demain a dakar", {"Marché Sandaga", "Marché Kermel"}),
    (("c est quoi le fouta toro",), "meilleure plage pres de dakar", {"Île à Morphil"}),
    (("que voir a kedougou",), "quelle est la monnaie du senegal", {"Kédougou"}),
]


@pytest.mark.parametrize("previous,message,absent", NOUVEAU_SUJET, ids=[case[1] for case in NOUVEAU_SUJET])
def test_un_nouveau_sujet_ne_recoit_pas_les_fiches_du_sujet_precedent(previous, message, absent):
    payload = site(*previous, message)
    assert not absent & set(places(payload)), places(payload)


def test_le_dossier_du_fouta_ne_suit_pas_une_question_sur_les_plages():
    payload = site("c est quoi le fouta toro", "meilleure plage pres de dakar")
    assert not any("Fouta" in title for title in dossiers(payload))


@pytest.mark.parametrize("previous,message,absent,audience", [
    ("je rentre a ziguinchor en aout", "comment envoyer de l argent avec wave", {"Ziguinchor"}, "diaspora"),
    ("visiter mbour", "acheter un terrain titre foncier", {"Mbour"}, "diaspora"),
    ("taxi de yoff a ouakam combien", "c est quoi le ninea", {"Corniche de Dakar", "Île de Ngor"}, "merchant"),
], ids=["diaspora-wave", "diaspora-terrain", "commercant-ninea"])
def test_profils_diaspora_et_commercant(previous, message, absent, audience):
    payload = site(previous, message, audience=audience)
    assert not absent & set(places(payload)), places(payload)


def test_les_intentions_affichees_sont_celles_du_nouveau_sujet():
    payload = site("visiter saint louis 2 jours", "numero police stp")
    assert "Intentions détectées : générale." in payload["instructions"]


# Vraies relances : le lieu du fil reste (cas positifs voisins).

RELANCES = [
    (("Je veux visiter Gorée",), "Combien de temps faut-il pour la visite ?", "Île de Gorée"),
    (("que voir a podor",), "et pour dormir ?", "Podor"),
    (("chaloupe goree",), "combien le billet ?", "Île de Gorée"),
    (("je veux visiter la maison des esclaves",), "c est ouvert le lundi ?", "Île de Gorée"),
    (("planifie 3 jours a saint louis",), "ajoute une journee au djoudj", "Île de Saint-Louis"),
    (("parle moi de goree",), "precise l histoire", "Île de Gorée"),
    (("je veux aller au lac rose",), "ca coute combien ?", "Lac Rose / Lac Retba"),
]


@pytest.mark.parametrize("previous,message,kept", RELANCES, ids=[case[1] for case in RELANCES])
def test_une_relance_garde_le_lieu_du_fil(previous, message, kept):
    assert kept in places(site(*previous, message))


# « Et pour manger ? » après la météo : une relance de restauration sur le lieu de la météo.

@pytest.mark.parametrize("weather_question,place", [
    ("Quel temps fait-il à Dakar ?", "dakar"),
    ("meteo saint louis demain", "saint-louis"),
    ("il pleut a ziguinchor ?", "ziguinchor"),
])
def test_et_pour_manger_apres_la_meteo_est_une_relance_de_restauration(weather_question, place):
    payload = site(weather_question, "Et pour manger ?")
    intent_context = payload["intent_context"]
    assert intent_context["intent"] == "restaurant"
    assert intent_context["location"] == place
    assert "PRÉVISIONS SIMULÉES" not in payload["instructions"]
    assert "weather" not in payload["context"]["intents"]
    assert "Intentions détectées : food." in payload["instructions"]
    assert "DOMAINE PERTINENT (food)" in payload["instructions"]
    assert intent_context["ux_hints"]["followups"][0] == f"Options à {place}"


def test_et_demain_apres_la_meteo_reste_une_meteo():
    # Cas positif voisin : une relance sans sujet propre garde l'intention du fil.
    payload = site("Quel temps fait-il à Dakar ?", "Et demain ?")
    assert payload["intent_context"]["intent"] == "weather"
    assert "PRÉVISIONS SIMULÉES" in payload["instructions"]


# La règle elle-même.

@pytest.mark.parametrize("message,own_subject,expected", [
    ("c est quoi le yassa", True, True),
    ("et a podor ?", True, False),            # relance : « et »
    ("ca coute combien a saly ?", True, False),  # renvoi : « ça »
    ("ajoute une journee au djoudj", True, False),  # retouche du plan
    ("Combien de temps faut-il pour la visite ?", False, False),  # aucun sujet propre
    ("recette thieboudienne", True, True),     # deux mots, mais un sujet propre
])
def test_starts_new_subject(message, own_subject, expected):
    from services.intelligence import starts_new_subject

    assert starts_new_subject(message, own_subject=own_subject) is expected
