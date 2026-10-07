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
