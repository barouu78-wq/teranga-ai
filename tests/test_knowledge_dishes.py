from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge

DATA = load_senegal_knowledge()


def test_every_dish_and_phrase_is_complete():
    assert len(DATA["dishes"]) >= 15 and len(DATA["wolof_phrases"]) >= 12
    for dish in DATA["dishes"]:
        assert dish["name"] and dish["kind"] in {"plat", "en-cas", "dessert", "boisson"} and len(dish["text"]) > 40
    for phrase in DATA["wolof_phrases"]:
        assert phrase["wo"] and phrase["fr"] and phrase["en"]


def test_dish_found_by_any_usual_spelling():
    for query in ("C'est quoi le thiéboudienne ?", "un bon tiep", "le ceebu jën de Saint-Louis"):
        assert "Ceebu jën" in format_senegal_knowledge(DATA, query=query)
    context = format_senegal_knowledge(DATA, query="Je veux un café Touba et un bissap")
    assert "Café Touba" in context and "Bissap" in context


def test_dishes_are_not_injected_by_unrelated_words():
    assert "PLATS ET BOISSONS" not in format_senegal_knowledge(DATA, query="Où acheter du pain à Dakar ?")
    assert "PLATS ET BOISSONS" not in format_senegal_knowledge(DATA, query="Quelle est la meilleure plage ?")


def test_wolof_phrases_only_when_wolof_is_asked():
    assert "Jërëjëf = Merci" in format_senegal_knowledge(DATA, query="Comment dire merci en wolof ?")
    assert "PHRASES WOLOF" not in format_senegal_knowledge(DATA, query="Comment aller à Gorée ?")
