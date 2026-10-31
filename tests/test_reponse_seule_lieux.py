"""Teranga plus indépendant (V4, étape 1) : une question simple sur un lieu de la base reçoit la fiche du lieu,
tout de suite et sans appel à l'IA payante.

Choix du propriétaire du 31 octobre 2026 (« une version plus indépendante »). Banc V3 de 100 questions avant :
9 réponses prêtes, 91 vers l'IA ; « C'est quoi le Lac Rose ? » ou « Que voir à Saint-Louis ? » partaient au
modèle alors que les 98 lieux de data/senegal_knowledge.json ont chacun un résumé, une histoire et un accès.
La réponse reprend ces textes tels quels (aucun fait ajouté) et renvoie à la fiche /lieux/<id>.
Seules les questions qui demandent « ce qu'est » un lieu sont servies : transport, prix, horaires, hôtels,
« demain », itinéraires de plusieurs jours restent au modèle. Aucun appel réseau.
"""

import json

import pytest

from services.quick_answers import quick_answer

ASKED = [
    ("C'est quoi le Lac Rose ?", "lac-rose", "Lac Rose"),
    ("Raconte-moi l'histoire de l'île de Gorée", "goree", "Gorée"),
    ("Parle-moi de Gorée", "goree", "Gorée"),
    ("Que voir à Saint-Louis ?", "saint-louis", "Saint-Louis"),
    ("Visiter le parc du Niokolo-Koba", "niokolo-koba", "Niokolo-Koba"),
    ("Parle-moi de Lompoul", "desert-de-lompoul", "Lompoul"),
    ("Présente-moi Cap Skirring", "cap-skirring", "Cap Skirring"),
]

NOT_ASKED = [
    "Comment aller à Gorée ?",                       # transport
    "Gorée c'est ouvert aujourd'hui ?",              # horaires du jour
    "Prix de la chaloupe pour Gorée",                # prix
    "Hôtel pas cher au Lac Rose",                    # hébergement
    "Que voir à Gorée demain ?",                     # date
    "Que visiter à Dakar en deux jours ?",           # itinéraire
    "C'est quoi le Lac Rose et comment y aller ?",   # deux demandes
    "Que faire en Casamance ?",                      # aucun lieu de la base de ce nom
    # « Que faire à Dakar ? » : aucun lieu de ce nom, mais la région reçoit son guide (test_reponse_seule_regions.py).
    "Gorée ou Saint-Louis, lequel visiter ?",        # comparaison de deux lieux
    "C'est quoi le meilleur restaurant de Dakar ?",  # pas un lieu de la base
]


def _ask(message, language="fr", **raw):
    return quick_answer({"message": message, "language": language}, raw)


@pytest.mark.parametrize("question,place_id,name", ASKED)
def test_a_simple_question_on_a_known_place_gets_its_card(question, place_id, name):
    ready = _ask(question)
    assert ready is not None, question
    assert name in ready["reply"] and f"teranga-ai.fr/lieux/{place_id}" in ready["reply"]
    assert ready["theme"] == "voyage" and ready.get("place_id") == place_id
    assert "Comment y aller" in ready["reply"]  # l'accès de la fiche, tel quel


@pytest.mark.parametrize("question", NOT_ASKED)
def test_other_place_questions_stay_with_the_model(question):
    assert _ask(question) is None, question


def test_only_french_and_only_a_first_question():
    assert _ask("What is the Pink Lake?", language="en") is None
    history = [{"role": "user", "content": "Bonjour"}, {"role": "assistant", "content": "Bonjour !"},
               {"role": "user", "content": "C'est quoi le Lac Rose ?"}]
    assert _ask("C'est quoi le Lac Rose ?", history=history) is None  # une suite de conversation va au modèle


def test_the_reply_only_uses_the_texts_of_the_base():
    from services.senegal_knowledge import load_senegal_knowledge

    place = next(p for p in load_senegal_knowledge()["places"] if p["id"] == "lac-rose")
    reply = _ask("C'est quoi le Lac Rose ?")["reply"]
    assert place["summary"] in reply and place["access"] in reply


def test_chat_serves_the_card_without_calling_the_ai(monkeypatch):
    from latence_harness import finish, install_provider, post_chat

    provider = install_provider(monkeypatch, error="l'IA ne doit pas être appelée pour une fiche de lieu")
    response = post_chat("C'est quoi le Lac Rose ?")
    events = [json.loads(line) for line in finish(response).decode().splitlines() if line.strip()]
    assert response.status_code == 200 and provider.calls == []
    assert "Lac Rose" in "".join(event.get("d", "") for event in events)
    assert not any("error" in event for event in events)


@pytest.mark.parametrize("place_id", sorted({place_id for _, place_id, _ in ASKED}))
def test_the_linked_place_page_has_the_map_and_photos_it_promises(place_id):
    """La réponse renvoie à « la fiche du lieu, avec photos et carte » : la page existe et a les deux sections.
    Le chat, lui, n'ajoute pas de photos à ces questions, comme une réponse de l'IA (relecture Codex sur #554) :
    le plan de l'agent ne cherche des images que pour une demande de photos."""
    import os

    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    import app as app_module

    page = app_module.app.test_client().get(f"/lieux/{place_id}", base_url="https://teranga-ai.fr")
    html = page.get_data(as_text=True)
    assert page.status_code == 200, place_id
    assert "<h2>Carte</h2>" in html and "openstreetmap.org/export/embed.html" in html, place_id
    assert "<h2>Photos</h2>" in html and 'id="gallery"' in html, place_id
