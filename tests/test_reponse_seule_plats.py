"""Teranga répond seul à « C'est quoi le yassa ? », depuis les plats de sa base vérifiée.

Décision du propriétaire du 19 octobre 2026 : plus d'indépendance pour Teranga. La description vient telle quelle de
data/senegal_knowledge.json (19 plats, en-cas, desserts et boissons). Une recette, un prix, une adresse, une
comparaison ou une conversation déjà commencée vont au modèle.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from services.quick_answers import quick_answer

ASKED = (
    ("C'est quoi le yassa ?", "Yassa"),
    ("Qu'est-ce que le mafé ?", "Mafé"),
    ("c est quoi le thieb", "Ceebu jën (thiéboudienne)"),
    ("C'est quoi le thiéboudienne ?", "Ceebu jën (thiéboudienne)"),
    ("C'est quoi l'attaya ?", "Attaya"),
    ("le bissap c'est quoi ?", "Bissap"),
    ("C'est quoi le café Touba ?", "Café Touba"),
    ("Définition du thiakry", "Thiakry (dégué)"),
)
NOT_ASKED = (
    "Recette du yassa ?",
    "Où manger un bon thiéboudienne à Dakar ?",
    "Combien coûte un plat de mafé ?",
    "C'est quoi la différence entre le yassa et le mafé ?",
    "C'est quoi le meilleur plat du Sénégal ?",
    "Le yassa est-il épicé ?",
    "C'est quoi le gingembre ?",
    "yassa",
)


def _ask(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


@pytest.mark.parametrize("message, name", ASKED)
def test_dish_question_gets_the_verified_description(message, name):
    answer = _ask(message)
    assert answer is not None, message
    reply = answer["reply"]
    assert reply.startswith(name), reply
    assert "teranga-ai.fr/specialites-senegal" in reply


def test_description_is_copied_as_is_from_the_knowledge_base():
    import json
    from pathlib import Path

    data = json.loads((Path(__file__).resolve().parent.parent / "data" / "senegal_knowledge.json").read_text("utf-8"))
    yassa = next(dish for dish in data["dishes"] if dish["name"] == "Yassa")
    reply = _ask("C'est quoi le yassa ?")["reply"]
    assert yassa["text"] in reply
    assert yassa["where"] in reply


@pytest.mark.parametrize("message", NOT_ASKED)
def test_other_questions_about_food_go_to_the_model(message):
    assert _ask(message) is None


def test_context_and_other_languages_go_to_the_model():
    message = "C'est quoi le yassa ?"
    earlier = [{"role": "user", "content": "Je suis à Ziguinchor"}, {"role": "assistant", "content": "Bienvenue !"}]
    assert _ask(message, raw={"history": earlier + [{"role": "user", "content": message}]}) is None
    assert _ask(message, raw={"context_place": "Ziguinchor"}) is None
    assert _ask(message, language="en") is None
    assert _ask(message, language="wo") is None
