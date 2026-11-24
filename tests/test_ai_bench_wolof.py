"""Banc d'essai : les noms wolof de Dakar (« Dakaar », « Ndakaaru »).

Le site propose lui-même ces questions en wolof (suggestions de static/home.js) : « Lan mooy tàkk-tàkk Dakaar
tey? », « Nettali ma taariixu Ndakaaru… ». Sans ces noms, le contexte envoyé au modèle ne recevait ni la région
de Dakar ni ses lieux, alors que la même question écrite « Dakar » les recevait.

Comme sur le site, la question en cours est aussi le dernier élément de `history`. Aucun appel réseau.
"""

import pytest

import services.weather as weather
from app import SENEGAL_KNOWLEDGE, app, parse_chat_payload
from services.intelligence import detect_location, infer_senegal_context
from services.senegal_knowledge import format_senegal_knowledge


@pytest.fixture(autouse=True)
def _pas_de_meteo(monkeypatch):
    def _hors_ligne(*_args, **_kwargs):
        raise RuntimeError("météo hors ligne pendant le banc")

    monkeypatch.setattr(weather, "fetch_forecast", _hors_ligne)


def _payload(question, language="wo", previous=()):
    history = [{"role": "user", "content": text} for text in previous] + [{"role": "user", "content": question}]
    with app.test_request_context(
        "/chat", method="POST", json={"message": question, "language": language, "history": history}
    ):
        payload, error = parse_chat_payload()
    assert error is None
    return payload


def _context(payload, question):
    return payload["instructions"].replace(question, " ")


# Questions réelles : suggestions wolof du site, puis fautes, anglais et français mêlés.
DAKAAR = [
    ("wo", "Lan mooy tàkk-tàkk Dakaar tey?"),
    ("wo", "Nettali ma taariixu Ndakaaru, te won ma dëkk bi."),
    ("wo", "naka laa demee dakaar"),
    ("wo", "NDAKAARU"),
    ("en", "what to see in dakaar"),
    ("fr", "je suis a ndakaaru demain, quoi visiter"),
]


@pytest.mark.parametrize("language,question", DAKAAR, ids=[q for _, q in DAKAAR])
def test_wolof_name_of_dakar_is_dakar(language, question):
    payload = _payload(question, language)
    context = _context(payload, question)
    assert payload["intent_context"]["location"] == "dakar"
    assert "CONTEXTE RÉGIONAL PERTINENT" in context and "- Dakar:" in context
    assert "Corniche de Dakar" in context


def test_dakaar_gets_the_same_places_as_dakar():
    wolof_question = "Nettali ma taariixu Ndakaaru, te won ma dëkk bi."
    french_question = "Nettali ma taariixu Dakar, te won ma dëkk bi."
    wolof = _context(_payload(wolof_question), wolof_question)
    french = _context(_payload(french_question), french_question)
    places = lambda text: text.split("LIEUX PERTINENTS :", 1)[1].split("\n\n", 1)[0] if "LIEUX PERTINENTS :" in text else ""
    assert places(wolof) and places(wolof) == places(french)


def test_food_question_in_dakaar_names_dakar_region():
    question = "Fan laa wara lekk ci Dakaar: Plateau, Medina, Almadies, Ngor, Ouakam?"
    assert "- Dakar:" in _context(_payload(question), question)


def test_follow_up_keeps_dakaar_as_the_place():
    payload = _payload("Et pour manger ?", "fr", previous=("Lan mooy tàkk-tàkk Dakaar tey?",))
    assert payload["intent_context"]["location"] == "dakar"


def test_detection_helpers_know_the_wolof_names():
    assert detect_location("Ndakaaru") == "dakar"
    assert detect_location("dem naa Dakaar") == "dakar"
    assert infer_senegal_context([], "dem naa Dakaar")["place"] == "dakar"
    assert "- Dakar:" in format_senegal_knowledge(SENEGAL_KNOWLEDGE, "taariixu ndakaaru")


# Cas voisins (sans nom wolof de Dakar) : le lieu détecté ne change pas.
NEIGHBOURS = [
    ("wo", "Naka nga def?", None),
    ("wo", "Jërëjëf", None),
    ("wo", "Naka laa demee Gorée ?", "goree"),
    ("wo", "Lan mooy thiéboudienne ?", None),
    ("fr", "Que voir à Saint-Louis ?", "saint-louis"),
    ("en", "is the dakar rally still in senegal", "dakar"),
]


@pytest.mark.parametrize("language,question,location", NEIGHBOURS, ids=[q for _, q, _ in NEIGHBOURS])
def test_neighbours_keep_their_location(language, question, location):
    assert _payload(question, language)["intent_context"]["location"] == location


# Banc réel du 22 novembre 2026 (langues-5, « Ana yoonu Tubaa ? ») : « Tubaa » n'était pas reconnu, le modèle n'a
# reçu aucun repère sur Touba et a inventé une région (« Mbàkke-Kajoor »). Noms wolof sourcés : Touba « Tuubaa »
# (souvent écrit « Tubaa ») et Saint-Louis « Ndar » (en.wikipedia.org, articles Grand Magal of Touba et
# Saint-Louis, Senegal ; sites.bu.edu/ria/wolof, unité 3).
AUTRES_VILLES = [
    ("wo", "Ana yoonu Tubaa ?", "Touba", "Diourbel"),
    ("wo", "Naka laa demee Tuubaa ?", "Touba", "Diourbel"),
    ("wo", "Lan laa mën a seet ci Ndar ?", "Saint-Louis", "Saint-Louis"),
    ("fr", "je vais a ndar demain", "Saint-Louis", "Saint-Louis"),
]


@pytest.mark.parametrize("language,question,lieu,region", AUTRES_VILLES, ids=[q for _, q, _, _ in AUTRES_VILLES])
def test_wolof_names_of_touba_and_saint_louis_bring_their_facts(language, question, lieu, region):
    context = _context(_payload(question, language), question)
    lieux = context.split("LIEUX PERTINENTS :", 1)[1].split("\n\n", 1)[0] if "LIEUX PERTINENTS :" in context else ""
    assert lieu in lieux, lieux[:300]
    assert f"- {region}:" in context


def test_tuubaa_is_not_dakar():
    assert _payload("Ana yoonu Tubaa ?")["intent_context"]["location"] != "dakar"
    assert _payload("Lan laa mën a seet ci Ndar ?")["intent_context"]["location"] == "saint-louis"


# Relecture Codex (#659) : « ndar » ne doit être reconnu que comme mot entier, jamais dans « standard ».
@pytest.mark.parametrize("question", ["Quelle est le standard au Sénégal ?", "Quel est le standard de vie à Dakar ?",
                                      "un standard téléphonique pour mon entreprise"])
def test_ndar_inside_a_word_is_not_saint_louis(question):
    assert detect_location(question) != "saint-louis"
    assert _payload(question, "fr")["intent_context"]["location"] != "saint-louis"
    assert "- Saint-Louis:" not in format_senegal_knowledge(SENEGAL_KNOWLEDGE, question)
