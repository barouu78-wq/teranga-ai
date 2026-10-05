"""Banc d'essai Fouta et questions pratiques : le contexte du modèle contient les faits utiles."""

import pytest

from app import app, parse_chat_payload

BENCH = [
    ("fr", "Comment dire bonjour en pulaar ?", ["Jam waali", "PHRASES PULAAR"]),
    ("fr", "Merci en pulaar", ["A jaraama"]),
    ("fr", "Que manger au Fouta ?", ["lacciri", "kosam"]),
    ("fr", "Parle-moi de la culture du Fouta", ["pekaan", "yela"]),
    ("fr", "Pourquoi beaucoup de gens du Fouta émigrent ?", ["associations villageoises"]),
    ("fr", "Comment aller à Matam ?", ["route nationale 2"]),
    ("fr", "Histoire des almamys du Fouta", ["1776", "Abdoul Kader Kane"]),
    ("fr", "Qui est Cheikh Hamidou Kane ?", ["Aventure ambiguë"]),
    ("fr", "Qui est El Hadji Omar Tall ?", ["Halwar"]),
    ("fr", "Les Toucouleurs c'est qui ?", ["Haalpulaar"]),
    ("fr", "Le festival Les Blues du Fleuve", ["Baaba Maal"]),
    ("en", "Tell me about Fouta Toro culture", ["pekaan"]),
    ("fr", "Quel est le numéro des pompiers au Sénégal ?", ["18", "1515"]),
    ("fr", "Quels sont les pays voisins du Sénégal ?", ["Mauritanie", "Guinée-Bissau"]),
    ("fr", "Quel type de prise électrique au Sénégal ?", ["230 V"]),
    ("fr", "Quel est l'indicatif téléphonique du Sénégal ?", ["+221"]),
]


@pytest.mark.parametrize("lang,question,expected", BENCH, ids=[q for _, q, _ in BENCH])
def test_fouta_and_practical_context_has_the_facts(lang, question, expected):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    context = payload["instructions"].replace(question, " ").casefold()
    missing = [fact for fact in expected if fact.casefold() not in context]
    assert not missing, f"Faits absents du contexte : {missing}"


def test_peul_alone_does_not_pull_the_fouta_society_dossier():
    # Les Peuls vivent dans tout le pays (Kolda, Ferlo…) : pas d'amalgame avec le Fouta.
    with app.test_request_context("/chat", method="POST", json={"message": "Les Peuls de Kolda", "language": "fr"}):
        payload, _ = parse_chat_payload()
    assert "Le Fouta aujourd'hui" not in payload["instructions"]
    assert "PHRASES PULAAR" in payload["instructions"]
