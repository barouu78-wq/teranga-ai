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


def test_infer_senegal_context_does_not_treat_duration_as_budget():
    from services.intelligence import infer_senegal_context

    context = infer_senegal_context([], "Je veux visiter Gorée pendant 4 jours")

    assert context["duration"] == "4 jours"
    assert context["budget"] == ""


def test_build_planner_data_converts_weeks_to_days():
    from services.intelligence import build_planner_data

    planner = build_planner_data({"duration": "4 semaines"})

    assert planner["duration_days"] == 28


def test_deep_reasoning_detects_comparison():
    from services.intelligence import should_use_deep_reasoning
    assert should_use_deep_reasoning({
        "query": "Compare Dakar et Saint-Louis pour un séjour",
        "intents": ["travel"],
        "constraints": [],
    }) is True


def test_deep_reasoning_detects_multiple_constraints():
    from services.intelligence import should_use_deep_reasoning
    assert should_use_deep_reasoning({
        "query": "Quel restaurant choisir ?",
        "intents": ["food"],
        "constraints": ["budget=20000", "famille"],
    }) is True


def test_deep_reasoning_avoids_simple_question():
    from services.intelligence import should_use_deep_reasoning
    assert should_use_deep_reasoning({
        "query": "Quelle est la capitale du Sénégal ?",
        "intents": ["culture"],
        "constraints": [],
    }) is False



def test_deep_reasoning_does_not_trigger_on_common_word_entre():
    from services.intelligence import should_use_deep_reasoning
    assert should_use_deep_reasoning({
        "query": "Quel est le prix entre Dakar et Thiès ?",
        "intents": ["price"],
        "constraints": [],
    }) is False


def test_deep_reasoning_detects_explicit_versus_comparison():
    from services.intelligence import should_use_deep_reasoning
    assert should_use_deep_reasoning({
        "query": "Dakar versus Saint-Louis pour 3 jours",
        "intents": ["travel"],
        "constraints": [],
    }) is True


def test_detect_location_resolves_structured_destination_highlights():
    assert detect_location("Je veux visiter Saly demain") == "saly"
    assert detect_location("Que faire au Cap Skirring ?") == "cap skirring"
    assert detect_location("Montre-moi Dindéfelo") == "dindefelo"


def test_language_detection_handles_natural_english_requests():
    assert detect_language("I want to visit Dakar") == "en"
    assert detect_language("Can you recommend a restaurant in Dakar?") == "en"


def test_intent_detection_does_not_match_transport_substrings_inside_business_words():
    assert detect_intent("Je veux lancer mon business") == "project"
    assert detect_intent("Quel bus prendre pour Dakar ?") == "transport"


def test_intent_engine_recognizes_project_career_education_and_finance():
    assert detect_intent("Je veux lancer mon business") == "project"
    assert detect_intent("Je cherche un emploi") == "career"
    assert detect_intent("Je veux trouver une formation") == "education"
    assert detect_intent("Comment obtenir un financement ?") == "finance"


def test_intent_context_marks_complex_project_request_for_deep_reasoning():
    result = build_intent_context(
        "Je veux lancer un petit commerce avec 150000 FCFA et trouver mes premiers clients."
    )
    assert result["intent"] == "project"
    assert result["needs_deep_reasoning"] is True

def test_follow_up_inherits_project_intent():
    result = build_intent_context(
        "Et pour le budget ?",
        history=[{"role": "user", "content": "Je veux lancer un commerce à Dakar."}],
    )
    assert result["intent"] == "project"
    assert result["location"] == "dakar"


def test_build_intent_context_reuses_precomputed_context(monkeypatch):
    import services.intelligence as intelligence

    def fail_if_called(*args, **kwargs):
        raise AssertionError("infer_senegal_context should not run twice")

    monkeypatch.setattr(intelligence, "infer_senegal_context", fail_if_called)
    monkeypatch.setattr(intelligence, "contextual_query", fail_if_called)
    result = intelligence.build_intent_context(
        "Et pour le budget ?",
        history=[{"role": "user", "content": "Je prépare un voyage à Dakar pendant 4 jours."}],
        resolved_context={"constraints": ["durée=4 jours"], "place": "dakar", "query": "dakar voyage 4 jours"},
    )

    assert result["intent"] == "trip_planning"
    assert result["context_source"] == "conversation"


def test_context_intents_do_not_match_transport_inside_business_words():
    from services.intelligence import infer_senegal_context

    context = infer_senegal_context([], "Je veux lancer mon business à Dakar avec 150000 FCFA.")

    assert "project" in context["intents"]
    assert "transport" not in context["intents"]


def test_project_budget_activates_agent_planner():
    from services.intelligence import infer_senegal_context, should_use_planner

    context = infer_senegal_context([], "Je veux lancer un commerce avec 150000 FCFA.")

    assert should_use_planner(context) is True


def test_intent_context_reuses_web_policy_decision(monkeypatch):
    import services.intelligence as intelligence

    calls = []
    monkeypatch.setattr(
        intelligence,
        "should_use_web",
        lambda message, context="": calls.append((message, context)) or True,
    )

    result = intelligence.build_intent_context("Quelle est l'histoire de Gorée ?")

    assert result["needs_web_search"] is True
    assert calls == [("Quelle est l'histoire de Gorée ?", "quelle est l'histoire de goree ?")]

def test_build_intent_context_exposes_small_structured_memory():
    result = build_intent_context(
        "Je prépare 4 jours à Gorée avec 100000 FCFA en famille.",
    )
    memory = result["memory"]
    assert memory["place"] == "goree"
    assert memory["budget"] == "100000 fcfa"
    assert memory["duration"] == "4 jours"
    assert memory["family"] is True
    assert len(memory["constraints"]) <= 8
    assert memory["source"] == "recent_conversation"


def test_project_request_activates_agent_planner():
    from services.intelligence import infer_senegal_context, should_use_planner

    context = infer_senegal_context(
        [],
        "Je veux lancer un commerce avec 150000 FCFA et trouver mes premiers clients.",
    )

    assert should_use_planner(context) is True


def test_career_request_activates_agent_planner():
    from services.intelligence import infer_senegal_context, should_use_planner

    context = infer_senegal_context(
        [],
        "Je cherche un emploi et je veux un plan en 3 étapes pour préparer ma candidature.",
    )

    assert should_use_planner(context) is True



def test_health_intent_and_context_are_recognized():
    from services.intelligence import build_intent_context, detect_intent, infer_senegal_context

    message = "Quels services de santé sont disponibles à Dakar ?"
    assert detect_intent(message) == "health"
    context = infer_senegal_context([], message)
    assert "health" in context["intents"]
    result = build_intent_context(message)
    assert result["intent"] == "health"
    assert result["domain"] == "health"
    assert result["needs_web_search"] is True


def test_generic_why_question_stays_on_fast_reasoning_path():
    from services.intelligence import should_use_deep_reasoning

    assert should_use_deep_reasoning({
        "query": "Pourquoi le thiéboudiène est-il populaire au Sénégal ?",
        "intents": ["culture"],
        "constraints": [],
    }) is False


def test_generic_how_question_stays_on_fast_reasoning_path():
    from services.intelligence import should_use_deep_reasoning

    assert should_use_deep_reasoning({
        "query": "Comment faire du thiéboudiène ?",
        "intents": ["food"],
        "constraints": [],
    }) is False


def test_multi_constraint_trip_request_still_uses_deep_reasoning():
    from services.intelligence import should_use_deep_reasoning

    assert should_use_deep_reasoning({
        "query": "Organise un séjour de 3 jours à Saly avec 150000 FCFA",
        "intents": ["travel"],
        "constraints": ["budget=150000 fcfa", "durée=3 jours"],
    }) is True


def test_project_budget_request_still_activates_planner():
    from services.intelligence import infer_senegal_context, should_use_planner

    context = infer_senegal_context([], "Je veux lancer un commerce avec 500000 FCFA.")

    assert should_use_planner(context) is True
