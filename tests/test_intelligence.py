from services.intelligence import (
    build_intent_context,
    detect_intent,
    detect_location,
    detect_language,
)


def test_trip_planning_context():
    result = build_intent_context(
        "Je pars à Dakar vendredi, fais-moi un itinéraire de 4 jours."
    )
    assert result["intent"] == "trip_planning"
    assert result["location"] == "dakar"
    assert result["needs_web_search"] is True
    assert result["needs_images"] is False


def test_goree_photo_context():
    result = build_intent_context("Montre-moi les photos de Gorée.")
    assert result["intent"] == "photos"
    assert result["location"] == "goree"
    assert result["needs_images"] is True


def test_weather_context():
    assert detect_intent("Quelle météo à Dakar demain ?") == "weather"
    assert detect_location("Quelle météo à Dakar demain ?") == "dakar"


def test_language_contract():
    assert detect_language("Bonjour, je veux visiter Dakar") == "fr"
    assert detect_language("Hello, I want to travel to Dakar") == "en"
    assert detect_language("Je veux visiter Dakar à pied") == "fr"
    assert detect_language("Hol no mbada") == "ff"


def test_context_history_is_flagged_without_changing_query():
    result = build_intent_context(
        "Et demain ?",
        history=[{"role": "user", "content": "Je suis à Dakar"}],
    )
    assert result["has_context"] is True
    assert result["query"] == "Et demain ?"


def test_follow_up_inherits_previous_location():
    result = build_intent_context(
        "Et demain ?",
        history=[{"role": "user", "content": "Quelle météo à Dakar aujourd'hui ?"}],
    )
    assert result["intent"] == "weather"
    assert result["location"] == "dakar"
    assert result["needs_web_search"] is True
    assert result["context_source"] == "conversation"


def test_follow_up_photo_inherits_previous_location():
    result = build_intent_context(
        "Montre-moi ça.",
        history=[{"role": "user", "content": "Parle-moi de Gorée."}],
    )
    assert result["intent"] == "photos"
    assert result["location"] == "goree"
    assert result["needs_images"] is True
    assert result["context_source"] == "conversation"


def test_contextual_query_keeps_recent_user_turns():
    from services.intelligence import contextual_query
    result = contextual_query(
        [{"role": "assistant", "content": "ignore"}, {"role": "user", "content": "Dakar"}, {"role": "user", "content": "Météo demain ?"}],
        "Et le soir ?",
    )
    assert result == "Dakar | Météo demain ? | Et le soir ?"


def test_senegal_context_extracts_planning_constraints():
    from services.intelligence import infer_senegal_context, should_use_planner, build_planner_data
    context = infer_senegal_context(
        [{"role": "user", "content": "Je veux visiter Gorée"}],
        "4 jours avec 100000 FCFA en famille",
    )
    assert context["place"] == "goree"
    assert context["duration"] == "4 jours"
    assert context["budget"] == "100000 fcfa"
    assert "famille" in context["constraints"]
    assert should_use_planner(context)
    planner = build_planner_data(context)
    assert planner["duration_days"] == 4
    assert planner["budget_fcfa"] == 100000


def test_build_conversation_sanitizes_and_marks_history_untrusted():
    from services.conversation import build_conversation
    result = build_conversation(
        [{"role": "user", "content": "Bonjour\u200b"}, {"role": "assistant", "content": "Salut"}],
        "Et Dakar ?",
        max_history_items=12,
        max_history_item_length=1400,
        max_history_chars=10000,
    )
    assert "<historique_non_fiable>" in result
    assert "Utilisateur: Bonjour" in result
    assert "Teranga AI: Salut" in result
    assert "<demande_utilisateur>\nEt Dakar ?" in result



def test_build_intent_context_uses_recent_turns_for_domain_and_web_policy():
    from services.intelligence import build_intent_context

    result = build_intent_context(
        "Et demain ?",
        [{"role": "user", "content": "Quelle météo à Dakar ?"}],
    )

    assert result["intent"] == "weather"
    assert result["location"] == "dakar"
    assert result["context_source"] == "conversation"
    assert result["needs_web_search"] is True




def test_infer_senegal_context_prefers_currency_amount_over_duration_number():
    from services.intelligence import infer_senegal_context

    context = infer_senegal_context(
        [],
        "Je prévois 100000 FCFA pour 4 jours à Gorée.",
    )

    assert context["budget"] == "100000 fcfa"
    assert context["duration"] == "4 jours"


def test_infer_senegal_context_extracts_traveler_counts_for_planner():
    from services.intelligence import infer_senegal_context, build_planner_data

    context = infer_senegal_context(
        [{"role": "user", "content": "On part 4 jours à Gorée avec 2 adultes et 2 enfants pour 120000 FCFA"}],
        "Et plutôt en famille ?",
    )

    assert context["adults"] == 2
    assert context["children"] == 2
    assert "adultes=2" in context["constraints"]
    assert "enfants=2" in context["constraints"]

    planner = build_planner_data(context)
    assert planner["adults"] == 2
    assert planner["children"] == 2
    assert planner["family"] is True


def test_infer_senegal_context_keeps_place_and_budget_from_recent_turn():
    from services.intelligence import infer_senegal_context

    result = infer_senegal_context(
        [{"role": "user", "content": "Je prépare 4 jours à Gorée avec 100000 FCFA"}],
        "Et en famille ?",
    )

    assert result["place"] == "goree"
    assert result["budget"] == "100000 fcfa"
    assert result["duration"] == "4 jours"
    assert "famille" in result["constraints"]
    assert result["context_source"] == "conversation"
