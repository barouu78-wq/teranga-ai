"""Repères pratiques : bons sujets détectés, aucun faux déclenchement courant."""

from services.practical_facts import matching_topics, practical_context


def test_topics_detected():
    assert matching_topics("Quels sont les numéros d'urgence ?") == ["urgences"]
    assert "argent" in matching_topics("Combien vaut 100 euros en FCFA ?")
    assert matching_topics("Comment créer une entreprise au Sénégal ?") == ["entreprise"]
    assert matching_topics("Quel type de prise électrique ?") == ["electricite"]
    assert "655,957" in practical_context("100 euros en francs CFA")


def test_no_false_triggers_on_common_phrases():
    for question in ("Une question sur le Sénégal", "Parle-moi de Gorée", "Créer un itinéraire",
                     "Un vol pour Dakar", "Raconte l'histoire de Saint-Louis"):
        assert practical_context(question) == "", question


def test_land_and_selling_topics():
    assert "titre foncier" in practical_context("Je vis en France, comment acheter un terrain au Sénégal ?")
    assert "WhatsApp Business" in practical_context("Comment vendre sur WhatsApp ?")
    for question in ("Construire un itinéraire", "Les clients de mon hôtel"):
        assert "titre foncier" not in practical_context(question) and "WhatsApp Business" not in practical_context(question)



def test_no_false_triggers_inside_words():
    # « visiTER », « goûTER », « FRANCais », « ATMosphère », « HEUREux », « enVISAge », « BUSiness ».
    for question in ("Je veux visiter la Casamance", "Que goûter à Dakar ?", "Je parle français",
                     "Quelle est l'atmosphère à Saint-Louis ?", "Je suis heureux de venir", "J'envisage de venir"):
        assert practical_context(question) == "", question
    assert matching_topics("Comment créer mon business ?") == ["entreprise"]
