from services.orchestrator import AgentPlan, build_agent_plan, run_enrichments


def test_agent_plan_routes_complex_requests_to_stronger_model():
    plan = build_agent_plan(
        {
            "planner": True,
            "deep_reasoning": False,
            "use_web": True,
            "intent_context": {"needs_images": False},
            "message": "Prépare un itinéraire",
            "contextual_query": "Dakar 4 jours",
        },
        model="gpt-5.6-luna",
        complex_model="gpt-5.6-sol",
    )

    assert isinstance(plan, AgentPlan)
    assert plan.model == "gpt-5.6-sol"
    assert plan.use_web is True
    assert plan.steps == (
        "prepare_context",
        "web_retrieval",
        "generate_response",
        "map_enrichment",
        "finalize",
    )


def test_agent_plan_keeps_simple_requests_on_fast_model():
    plan = build_agent_plan(
        {
            "planner": False,
            "deep_reasoning": False,
            "use_web": False,
            "intent_context": {"needs_images": False},
            "message": "Quelle est la capitale du Sénégal ?",
        },
        model="gpt-5.6-luna",
    )

    assert plan.model == "gpt-5.6-luna"
    assert plan.steps == ("prepare_context", "generate_response", "map_enrichment", "finalize")


def test_agent_plan_disables_image_enrichment_for_planner_requests():
    plan = build_agent_plan(
        {
            "planner": True,
            "deep_reasoning": True,
            "use_web": False,
            "intent_context": {"needs_images": True},
            "message": "Prépare un voyage",
        },
        model="gpt-5.6-luna",
    )

    assert plan.use_images is False


def test_run_enrichments_only_calls_selected_tools():
    calls = []

    def fetch_images(message):
        calls.append(("images", message))
        return ["image"]

    def lookup_map(query, enabled):
        calls.append(("map", query, enabled))
        return {"query": query}

    plan = AgentPlan(
        model="gpt-5.6-luna",
        use_images=True,
        use_map=True,
        steps=("generate_response", "image_enrichment", "map_enrichment", "finalize"),
    )

    image, map_result = run_enrichments(
        plan,
        message="Gorée",
        contextual_query="Gorée",
        fetch_images=fetch_images,
        lookup_map=lookup_map,
        should_fetch_map=lambda query: True,
    )

    assert image == ["image"]
    assert map_result == {"query": "Gorée"}
    assert calls == [("images", "Gorée"), ("map", "Gorée", True)]


def test_run_enrichments_has_no_side_effect_when_disabled():
    calls = []

    plan = AgentPlan(model="gpt-5.6-luna")

    result = run_enrichments(
        plan,
        message="Bonjour",
        contextual_query="Bonjour",
        fetch_images=lambda _: calls.append("images"),
        lookup_map=lambda *_: calls.append("map"),
        should_fetch_map=lambda _: True,
    )

    assert result == (None, None)
    assert calls == []
