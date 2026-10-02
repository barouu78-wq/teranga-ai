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
