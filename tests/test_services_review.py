"""Régressions trouvées par la revue de code de services/."""

from services.intelligence import build_intent_context, infer_senegal_context
from services.senegal_knowledge import _knowledge_domain, classify_domain
from services.text import clean_answer
from services.youth_projects import detect_project_category


def test_links_keep_their_underscores():
    text = clean_answer("Voir https://fr.wikipedia.org/wiki/Île_de_Gorée et _italique_ et **gras**.")
    assert text == "Voir https://fr.wikipedia.org/wiki/Île_de_Gorée et italique et gras."


def test_a_clear_question_keeps_its_own_intent():
    history = [{"role": "user", "content": "Quel temps fait-il à Dakar ?"}]
    assert build_intent_context("Où manger à Dakar ?", history)["intent"] == "restaurant"


def test_counts_and_ages_are_not_budgets():
    assert infer_senegal_context([], "Un séjour pour 2 adultes")["budget"] == ""
    assert infer_senegal_context([], "J'ai 25 ans")["budget"] == ""
    assert infer_senegal_context([], "budget 300000 pour 5 jours")["budget"].strip() == "300000"
    assert "fcfa" in infer_senegal_context([], "avec 200 000 FCFA")["budget"]


def test_the_most_recent_place_wins():
    history = [{"role": "user", "content": "Que voir à Gorée ?"}]
    assert infer_senegal_context(history, "Et à Dakar, où manger ?")["place"] == "dakar"
    assert infer_senegal_context([], "Toubab Dialaw")["place"] != "touba"


def test_domains_ignore_accents_and_partial_words():
    assert classify_domain("ou trouver un hopital") == "health"
    assert _knowledge_domain("je cherche une ecole") == "education"
    assert _knowledge_domain("teranga") == "general" and _knowledge_domain("le plateau") == "general"
    assert _knowledge_domain("les plages de saly") == "travel"


def test_project_category_uses_whole_words():
    assert detect_project_category("Je suis artisan couturier") == "craft"
    assert detect_project_category("vendre des oeuvres d art") == "creative"
