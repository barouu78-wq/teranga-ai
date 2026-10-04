from threading import Barrier

from services.orchestrator import AgentPlan, build_agent_plan, run_enrichments


def test_map_is_not_selected_for_simple_question():
    plan = build_agent_plan(
        {
            "intent_context": {"intent": "general_information", "location": None},
            "message": "Quelle est la capitale du Sénégal ?",
        },
        model="gpt-5.6-luna",
    )
    assert plan.use_map is False
    assert plan.steps == ("prepare_context", "generate_response", "finalize")


def test_map_is_not_selected_for_substring_match():
    plan = build_agent_plan(
        {
            "intent_context": {"intent": "general_information", "location": "dakar"},
            "message": "Parle-moi de la routeur de Dakar.",
        },
        model="gpt-5.6-luna",
    )
    assert plan.use_map is False


def test_map_is_selected_for_standalone_route_hint():
    plan = build_agent_plan(
        {
            "intent_context": {"intent": "general_information", "location": "dakar"},
            "message": "Quelle route prendre pour Dakar ?",
        },
        model="gpt-5.6-luna",
    )
    assert plan.use_map is True


def test_map_is_selected_for_transport():
    plan = build_agent_plan(
        {"intent_context": {"intent": "transport", "location": "dakar"}, "message": "Comment aller à Dakar ?"},
        model="gpt-5.6-luna",
    )
    assert plan.use_map is True


def test_image_failure_does_not_block_map():
    calls = []

    def fetch_images(_):
        raise RuntimeError("image unavailable")

    def lookup_map(query, enabled):
        calls.append((query, enabled))
        return {"query": query}

    image, map_result = run_enrichments(
        AgentPlan(model="gpt-5.6-luna", use_images=True, use_map=True),
        message="Gorée",
        contextual_query="Gorée",
        fetch_images=fetch_images,
        lookup_map=lookup_map,
        should_fetch_map=lambda _: True,
    )
    assert image is None
    assert map_result == {"query": "Gorée"}
    assert calls == [("Gorée", True)]


def test_selected_enrichments_run_in_parallel():
    barrier = Barrier(2)

    def fetch_images(_):
        barrier.wait(timeout=2)
        return ["image"]

    def lookup_map(*_):
        barrier.wait(timeout=2)
        return {"map": True}

    image, map_result = run_enrichments(
        AgentPlan(model="gpt-5.6-luna", use_images=True, use_map=True),
        message="Dakar",
        contextual_query="Dakar",
        fetch_images=fetch_images,
        lookup_map=lookup_map,
        should_fetch_map=lambda _: True,
    )
    assert image == ["image"]
    assert map_result == {"map": True}


def test_map_failure_does_not_block_image():
    def fetch_images(message):
        return ["image"]

    def lookup_map(*_):
        raise RuntimeError("map unavailable")

    image, map_result = run_enrichments(
        AgentPlan(model="gpt-5.6-luna", use_images=True, use_map=True),
        message="Gorée",
        contextual_query="Gorée",
        fetch_images=fetch_images,
        lookup_map=lookup_map,
        should_fetch_map=lambda _: True,
    )
    assert image == ["image"]
    assert map_result is None


def test_planner_still_routes_to_stronger_model_and_map():
    plan = build_agent_plan(
        {
            "planner": True,
            "deep_reasoning": False,
            "use_web": True,
            "intent_context": {"intent": "trip_planning", "needs_images": False},
            "message": "Prépare un itinéraire",
        },
        model="gpt-5.6-luna",
        complex_model="gpt-5.6-sol",
    )
    assert plan.model == "gpt-5.6-sol"
    assert plan.use_map is True


def test_planner_exposes_explicit_build_plan_step():
    plan = build_agent_plan(
        {
            "planner": True,
            "use_web": False,
            "intent_context": {"intent": "project", "needs_images": False},
            "message": "Organise mon projet",
        },
        model="gpt-5.6-luna",
    )
    assert "build_plan" in plan.steps
    assert plan.steps.index("build_plan") < plan.steps.index("generate_response")


def test_planner_exposes_workflow_type_from_intent():
    plan = build_agent_plan(
        {
            "planner": True,
            "intent_context": {"intent": "career", "needs_images": False},
            "message": "Organise ma recherche d emploi",
        },
        model="gpt-5.6-luna",
    )
    assert plan.workflow == "career"


def test_non_planner_keeps_general_workflow():
    plan = build_agent_plan(
        {
            "planner": False,
            "intent_context": {"intent": "finance", "needs_images": False},
            "message": "Quel est le taux ?",
        },
        model="gpt-5.6-luna",
    )
    assert plan.workflow == "general"


def test_planner_normalizes_trip_workflow_case_and_whitespace():
    plan = build_agent_plan(
        {"planner": True, "intent_context": {"intent": "  TRIP_PLANNING  "}},
        model="gpt-5.6-luna",
    )
    assert plan.workflow == "travel"


def test_planner_normalizes_trip_workflow_to_travel():
    plan = build_agent_plan(
        {"planner": True, "intent_context": {"intent": "trip_planning"}},
        model="gpt-5.6-luna",
    )
    assert plan.workflow == "travel"


def test_planner_rejects_unknown_workflow_values():
    plan = build_agent_plan(
        {"planner": True, "intent_context": {"intent": "unknown_internal_intent"}},
        model="gpt-5.6-luna",
    )
    assert plan.workflow == "general"


def test_static_question_routes_to_local_knowledge():
    plan = build_agent_plan(
        {"intent_context": {"intent": "culture", "location": "goree"}, "message": "Quelle est l'histoire de Gorée ?"},
        model="gpt-5.6-luna",
    )
    assert plan.source_strategy == "local"
    assert plan.action_strategy == "answer"


def test_dynamic_restaurant_request_routes_to_web_and_action():
    plan = build_agent_plan(
        {"use_web": True, "intent_context": {"intent": "restaurant", "location": "dakar", "has_context": True}, "message": "Où manger ce soir ?"},
        model="gpt-5.6-luna",
    )
    assert plan.source_strategy == "hybrid"
    assert plan.action_strategy == "act"


def test_photo_request_routes_to_images_without_forcing_web_strategy():
    plan = build_agent_plan(
        {"use_web": False, "intent_context": {"intent": "photos", "location": "goree", "needs_images": True}, "message": "Montre-moi Gorée"},
        model="gpt-5.6-luna",
    )
    assert plan.use_images is True
    assert plan.source_strategy == "local"


def test_followup_preserves_hybrid_context_when_web_is_required():
    plan = build_agent_plan(
        {"use_web": True, "intent_context": {"intent": "restaurant", "location": "dakar", "has_context": True}, "message": "Et demain ?"},
        model="gpt-5.6-luna",
    )
    assert plan.source_strategy == "hybrid"
    assert plan.action_strategy == "act"


def test_action_plan_prepares_trip_action():
    plan = build_agent_plan(
        {
            "planner": True,
            "use_web": True,
            "intent_context": {"intent": "trip_planning", "location": "goree"},
            "message": "Prépare mon voyage à Gorée",
        },
        model="gpt-5.6-luna",
    )
    assert plan.action_strategy == "act"
    assert plan.action == "prepare_trip_plan"
    assert "prepare_action" in plan.steps


def test_action_plan_prepares_project_action():
    plan = build_agent_plan(
        {
            "planner": True,
            "intent_context": {"intent": "project", "location": "dakar"},
            "message": "Organise mon projet à Dakar",
        },
        model="gpt-5.6-luna",
    )
    assert plan.action_strategy == "act"
    assert plan.action == "prepare_project_plan"


def test_action_plan_does_not_claim_action_for_static_question():
    plan = build_agent_plan(
        {
            "intent_context": {"intent": "culture", "location": "goree"},
            "message": "Quelle est l'histoire de Gorée ?",
        },
        model="gpt-5.6-luna",
    )
    assert plan.action_strategy == "answer"
    assert plan.action == "answer"
    assert "prepare_action" not in plan.steps



def test_external_action_is_prepared_until_confirmation():
    payload = {
        "planner": True,
        "use_web": True,
        "intent_context": {"intent": "restaurant", "location": "dakar"},
        "message": "Réserve une table à Dakar",
    }
    plan = build_agent_plan(payload, model="gpt-5.6-luna")
    from services.orchestrator import build_action_request
    request = build_action_request(payload, plan)
    assert request["enabled"] is True
    assert request["execution_mode"] == "prepare"
    assert request["requires_confirmation"] is True


def test_confirmed_action_can_enter_execution_mode():
    payload = {
        "planner": True,
        "use_web": True,
        "action_confirmed": True,
        "intent_context": {"intent": "restaurant", "location": "dakar"},
        "message": "Réserve une table à Dakar",
    }
    plan = build_agent_plan(payload, model="gpt-5.6-luna")
    from services.orchestrator import build_action_request
    request = build_action_request(payload, plan)
    assert request["execution_mode"] == "execute"
    assert request["requires_confirmation"] is False
    assert request["confirmed"] is True


def test_static_answer_has_no_action_contract():
    payload = {
        "intent_context": {"intent": "culture", "location": "goree"},
        "message": "Quelle est l'histoire de Gorée ?",
    }
    plan = build_agent_plan(payload, model="gpt-5.6-luna")
    from services.orchestrator import build_action_request
    request = build_action_request(payload, plan)
    assert request["enabled"] is False
    assert request["execution_mode"] == "answer"
    assert request["requires_confirmation"] is False
