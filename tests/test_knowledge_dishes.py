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


def test_people_named_in_the_question_come_first_and_alone():
    from services.senegal_knowledge import load_senegal_people

    people = load_senegal_people()
    context = format_senegal_knowledge(DATA, query="Qui était Seydina Limamou Laye ?", people=people)
    section = context.split("PERSONNALITÉS PERTINENTES :")[1]
    assert "Seydina Limamou Laye" in section and "Abdoulaye Wade" not in section
    assert "Youssou Ndour" in format_senegal_knowledge(DATA, query="Parle-moi de Youssou Ndour", people=people)


def test_fouta_history_dossier_is_injected_only_for_fouta_questions():
    for query in ("Raconte l'histoire du Fouta-Toro", "C'est quoi la révolution torodo ?", "Qui était l'almamy Abdoul Kader Kane ?"):
        assert "DOSSIER HISTORIQUE — Fouta-Toro" in format_senegal_knowledge(DATA, query=query)
    for query in ("Comment aller à Toronto ?", "Que voir à Dakar ?"):
        assert "DOSSIER HISTORIQUE" not in format_senegal_knowledge(DATA, query=query)


def test_each_kingdom_dossier_answers_its_own_questions():
    expected = {
        "Parle-moi de l'empire du Djolof": "Empire du Djolof",
        "Qui était Lat Dior ?": "Royaume du Cayor",
        "Que s'est-il passé à Nder en 1820 ?": "Royaume du Waalo",
        "La bataille de Fandane-Thiouthioune": "Royaume du Sine",
        "Le roi de Kahone": "Royaume du Saloum",
    }
    for query, title in expected.items():
        assert f"DOSSIER HISTORIQUE — {title}" in format_senegal_knowledge(DATA, query=query), query
    # Une question touristique sur le delta n'embarque pas un cours d'histoire.
    assert "DOSSIER HISTORIQUE" not in format_senegal_knowledge(DATA, query="Que faire dans le delta du Saloum ?")
