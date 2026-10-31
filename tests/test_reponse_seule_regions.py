"""Teranga plus indépendant (V4, étape 2) : une question simple sur une des 14 régions reçoit le guide de la région,
tout de suite et sans appel à l'IA payante.

Go du propriétaire du 31 octobre 2026, après l'étape 1 (fiches des lieux, #554). « Que faire à Dakar ? » partait au
modèle : Dakar n'est pas un lieu de la base, mais une région, avec son dossier dans data/senegal_knowledge.json
(identité, géographie, incontournables, plats, conseil pratique). La réponse reprend ces textes tels quels (aucun
fait ajouté) et renvoie au guide /regions/<slug>, qui liste les lieux de la région.
Une ville qui porte le nom de sa région (« Que voir à Thiès ? ») garde la fiche du lieu : la région se demande
avec le mot « région ». L'histoire (aucun texte d'histoire dans le dossier d'une région), le transport, les dates,
les itinéraires et la Casamance (qui n'est pas une région de la base) restent au modèle. Aucun appel réseau.
"""

import json
import os

import pytest

from services.quick_answers import quick_answer
from services.senegal_knowledge import load_senegal_knowledge

ASKED = [
    ("Que faire à Dakar ?", "dakar"),
    ("Que visiter à Dakar ?", "dakar"),
    ("C'est quoi la région de Thiès ?", "thies"),
    ("Parle-moi de la région de Saint-Louis", "saint-louis"),
    ("Que voir dans la région de Kédougou ?", "kedougou"),
    ("Présente-moi Diourbel", "diourbel"),
    ("Que visiter à Matam ?", "matam"),
    ("Découvrir la région de Ziguinchor", "ziguinchor"),
]

NOT_ASKED = [
    "Que visiter à Dakar en deux jours ?",                 # itinéraire
    "Que faire à Dakar ce soir ?",                         # moment précis
    "Que faire à Dakar avec des enfants ?",                # demande précisée
    "Comment aller à Dakar ?",                             # transport
    "Où manger à Dakar ?",                                 # adresses
    "Raconte-moi l'histoire de Dakar",                     # aucun texte d'histoire dans le dossier de la région
    "Que faire à Dakar ou à Thiès ?",                      # deux régions
    "Que voir dans la région de Thiès et de Fatick ?",     # deux régions
    "Que faire en Casamance ?",                            # pas une région de la base
]


def _ask(message, language="fr", **raw):
    return quick_answer({"message": message, "language": language}, raw)


def _region(region_id):
    return next(r for r in load_senegal_knowledge()["regions"] if r["id"] == region_id)


@pytest.mark.parametrize("question,region_id", ASKED)
def test_a_simple_question_on_a_region_gets_its_guide(question, region_id):
    ready = _ask(question)
    assert ready is not None, question
    assert ready.get("region_id") == region_id and ready["theme"] == "voyage"
    assert _region(region_id)["name"] in ready["reply"]
    assert f"teranga-ai.fr/regions/{region_id}" in ready["reply"]


@pytest.mark.parametrize("question", NOT_ASKED)
def test_other_region_questions_stay_with_the_model(question):
    assert _ask(question) is None, question


def test_a_city_named_like_its_region_keeps_the_place_card():
    ready = _ask("Que voir à Thiès ?")
    assert ready is not None and ready.get("place_id") == "thies" and not ready.get("region_id")


def test_only_french_and_only_a_first_question():
    assert _ask("What to do in Dakar?", language="en") is None
    history = [{"role": "user", "content": "Bonjour"}, {"role": "assistant", "content": "Bonjour !"},
               {"role": "user", "content": "Que faire à Dakar ?"}]
    assert _ask("Que faire à Dakar ?", history=history) is None  # une suite de conversation va au modèle


@pytest.mark.parametrize("region", load_senegal_knowledge()["regions"], ids=lambda r: r["id"])
def test_every_region_reply_only_uses_the_texts_of_the_base(region):
    reply = _ask(f"Parle-moi de la région de {region['name']}")
    assert reply is not None, region["name"]
    reply = reply["reply"]
    dossier = region["regional_dossier"]
    for text in (dossier["identity"], dossier["geography"]):
        assert text in reply, (region["id"], text)
    assert ", ".join(region["highlights"]) in reply
    assert ", ".join(region.get("foods") or dossier["foods"]) in reply
    assert "à vérifier avant de partir" in reply
    # « practical » est une consigne pour l'IA (« doivent être datées selon la campagne… »), jamais montrée au lecteur.
    assert dossier["practical"] not in reply


@pytest.mark.parametrize("region", load_senegal_knowledge()["regions"], ids=lambda r: r["id"])
def test_the_linked_region_guide_lists_the_places_of_the_region(region):
    """La réponse renvoie au « guide de la région, avec ses lieux à visiter » : la page existe et les liste."""
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    import app as app_module

    page = app_module.app.test_client().get(f"/regions/{region['id']}", base_url="https://teranga-ai.fr")
    assert page.status_code == 200, region["id"]
    assert "Lieux à visiter dans la région" in page.get_data(as_text=True), region["id"]


def test_chat_serves_the_guide_without_calling_the_ai(monkeypatch):
    from latence_harness import finish, install_provider, post_chat

    provider = install_provider(monkeypatch, error="l'IA ne doit pas être appelée pour le guide d'une région")
    response = post_chat("Que faire à Dakar ?")
    events = [json.loads(line) for line in finish(response).decode().splitlines() if line.strip()]
    assert response.status_code == 200 and provider.calls == []
    assert "Dakar" in "".join(event.get("d", "") for event in events)
    assert not any("error" in event for event in events)
