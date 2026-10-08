from pathlib import Path

import pytest

from services.model_params import (
    DEFAULT_OPENAI_COMPLEX_MODEL,
    DEFAULT_OPENAI_MODEL,
    build_model_kwargs,
    clean_model_name,
    openai_complex_model,
    openai_model,
    openai_trip_model,
)


def _kwargs(payload, model="gpt-test", override=None):
    return build_model_kwargs(
        payload,
        model=model,
        reasoning_effort=lambda web, planner: "low",
        search_context_size=lambda domain, planner: "medium",
        preferred_domains=lambda domain: (),
        stream=True,
        reasoning_override=override,
    )


def test_build_model_kwargs_keeps_fast_chat_defaults():
    result = _kwargs({
        "use_web": False, "planner": False, "deep_reasoning": False,
        "instructions": "i", "input_text": "q",
    })
    assert result["model"] == "gpt-test"
    assert result["max_output_tokens"] == 800
    assert result["prompt_cache_key"] == "teranga-chat-v1"
    assert result["reasoning"] == {"effort": "low"}
    assert "tools" not in result


def test_build_model_kwargs_uses_medium_for_complex_model():
    result = _kwargs({
        "use_web": False, "planner": False, "deep_reasoning": True,
        "instructions": "i", "input_text": "q",
    })
    assert result["reasoning"] == {"effort": "medium"}


def test_build_model_kwargs_uses_medium_for_planner_model():
    result = _kwargs({
        "use_web": True, "planner": True, "deep_reasoning": False,
        "instructions": "i", "input_text": "q",
        "intent_context": {"domain": "travel"},
    })
    assert result["reasoning"] == {"effort": "medium"}
    assert result["max_output_tokens"] == 1200


def test_build_model_kwargs_keeps_luna_fast_even_for_complex_payload():
    result = _kwargs({
        "use_web": False, "planner": True, "deep_reasoning": True,
        "instructions": "i", "input_text": "q",
    }, model="gpt-5.6-luna")
    assert result["reasoning"] == {"effort": "low"}


def test_build_model_kwargs_respects_explicit_reasoning_override():
    result = _kwargs({
        "use_web": False, "planner": True, "deep_reasoning": True,
        "instructions": "i", "input_text": "q",
    }, override="low")
    assert result["reasoning"] == {"effort": "low"}


def test_build_model_kwargs_adds_web_tool_and_domains():
    result = build_model_kwargs(
        {
            "use_web": True,
            "planner": False,
            "deep_reasoning": False,
            "instructions": "i",
            "input_text": "q",
            "intent_context": {"domain": "weather"},
        },
        model="gpt-test",
        reasoning_effort=lambda web, planner: "low",
        search_context_size=lambda domain, planner: "high",
        preferred_domains=lambda domain: ("anacim.sn", "meteo.sn"),
        stream=False,
    )
    assert result["max_output_tokens"] == 1200
    assert result["tools"] == [{
        "type": "web_search",
        "search_context_size": "high",
        "filters": {"allowed_domains": ["anacim.sn", "meteo.sn"]},
    }]


def test_build_model_kwargs_applies_senegal_transport_sources():
    from services.web_policy import preferred_domains
    result = build_model_kwargs(
        {
            "use_web": True,
            "planner": False,
            "deep_reasoning": False,
            "instructions": "i",
            "input_text": "q",
            "intent_context": {"domain": "transport"},
        },
        model="gpt-test",
        reasoning_effort=lambda web, planner: "low",
        search_context_size=lambda domain, planner: "low",
        preferred_domains=preferred_domains,
        stream=False,
    )
    assert result["tools"][0]["filters"]["allowed_domains"][:2] == ["transports.gouv.sn", "gov.sn"]


def test_build_model_kwargs_applies_senegal_food_sources():
    from services.web_policy import preferred_domains
    result = build_model_kwargs(
        {
            "use_web": True,
            "planner": False,
            "deep_reasoning": False,
            "instructions": "i",
            "input_text": "q",
            "intent_context": {"domain": "food"},
        },
        model="gpt-test",
        reasoning_effort=lambda web, planner: "low",
        search_context_size=lambda domain, planner: "low",
        preferred_domains=preferred_domains,
        stream=False,
    )
    assert result["tools"][0]["filters"]["allowed_domains"][:2] == ["agriculture.gouv.sn", "tourisme.gouv.sn"]


# --- Noms des modèles : valeurs par défaut inchangées, réglables par l'environnement ---

_MODEL_VARIABLES = ("OPENAI_MODEL", "OPENAI_COMPLEX_MODEL", "OPENAI_TRIP_MODEL")


@pytest.fixture
def clean_env(monkeypatch):
    for name in _MODEL_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_model_defaults_are_the_historical_names(clean_env):
    assert DEFAULT_OPENAI_MODEL == "gpt-5.6-luna"
    assert DEFAULT_OPENAI_COMPLEX_MODEL == "gpt-5.6-sol"
    assert openai_model() == "gpt-5.6-luna"
    assert openai_complex_model() == "gpt-5.6-sol"
    assert openai_trip_model() == ""


def test_model_names_follow_the_environment(clean_env):
    clean_env.setenv("OPENAI_MODEL", " mon-modele-rapide ")
    clean_env.setenv("OPENAI_COMPLEX_MODEL", "mon-modele-complexe")
    clean_env.setenv("OPENAI_TRIP_MODEL", "ft:mon-modele:org::abc123")
    assert openai_model() == "mon-modele-rapide"
    assert openai_complex_model() == "mon-modele-complexe"
    assert openai_trip_model() == "ft:mon-modele:org::abc123"


@pytest.mark.parametrize("value", ["", "   ", "deux mots", "a;b", "$(ls)", "../x", "-debut", "x" * 101, "modèle", "a\nb"])
def test_empty_or_invalid_model_name_falls_back_to_the_default(clean_env, value):
    clean_env.setenv("OPENAI_MODEL", value)
    clean_env.setenv("OPENAI_COMPLEX_MODEL", value)
    clean_env.setenv("OPENAI_TRIP_MODEL", value)
    assert openai_model() == "gpt-5.6-luna"
    assert openai_complex_model() == "gpt-5.6-sol"
    assert openai_trip_model() == ""


def test_clean_model_name_ignores_non_strings():
    assert clean_model_name(None, "defaut") == "defaut"
    assert clean_model_name(42, "defaut") == "defaut"
    assert clean_model_name("  ok-1.2  ", "defaut") == "ok-1.2"


def test_reasoning_effort_compares_with_the_configured_fast_model(clean_env):
    payload = {"use_web": False, "planner": True, "deep_reasoning": True, "instructions": "i", "input_text": "q"}
    clean_env.setenv("OPENAI_MODEL", "mon-modele-rapide")
    assert _kwargs(payload, model="mon-modele-rapide")["reasoning"] == {"effort": "low"}
    assert _kwargs(payload, model="gpt-5.6-luna")["reasoning"] == {"effort": "medium"}


def test_orchestrator_escalates_from_the_configured_fast_model(clean_env):
    from services.orchestrator import build_agent_plan

    payload = {"planner": True, "intent_context": {"intent": "trip_planning"}, "message": "Prépare un itinéraire"}
    # Sans variable : mêmes noms qu'avant.
    assert build_agent_plan(payload, model="gpt-5.6-luna").model == "gpt-5.6-sol"
    assert build_agent_plan(payload, model="un-autre-modele").model == "un-autre-modele"
    # Avec variables : le modèle configuré monte vers le modèle complexe configuré.
    clean_env.setenv("OPENAI_MODEL", "mon-modele-rapide")
    clean_env.setenv("OPENAI_COMPLEX_MODEL", "mon-modele-complexe")
    assert build_agent_plan(payload, model="mon-modele-rapide").model == "mon-modele-complexe"
    assert build_agent_plan(payload, model="gpt-5.6-luna").model == "gpt-5.6-luna"
    # Un modèle complexe vide, passé explicitement, désactive toujours la montée.
    assert build_agent_plan(payload, model="mon-modele-rapide", complex_model="").model == "mon-modele-rapide"


def _build_service(captured, **kwargs):
    from services.chat_service import build_chat_service

    def create_openai_response(client, payload, *, build_kwargs, model, logger, stream, fallback_models):
        captured.append((model, fallback_models))
        return object()

    return build_chat_service(
        client=object(),
        logger=object(),
        build_model_kwargs=lambda *args, **kw: {},
        reasoning_effort="low",
        search_context_size="low",
        preferred_domains=(),
        create_openai_response=create_openai_response,
        clean_answer=lambda value: value,
        extract_sources=lambda value: [],
        fetch_topic_images=lambda value: None,
        lookup_map=lambda query, enabled: None,
        should_fetch_map=lambda query: False,
        **kwargs,
    )


def test_chat_service_replaces_empty_or_invalid_names_by_the_defaults(clean_env):
    captured = []
    service = _build_service(captured, model="", complex_model="nom invalide !")
    service["create_response"]({}, False)
    service["create_response"]({"planner": True}, False)
    assert captured == [
        ("gpt-5.6-luna", ("gpt-5.6-sol",)),
        ("gpt-5.6-sol", ("gpt-5.6-luna",)),
    ]


def test_chat_service_without_complex_model_uses_the_configured_one(clean_env):
    clean_env.setenv("OPENAI_COMPLEX_MODEL", "mon-modele-complexe")
    captured = []
    service = _build_service(captured, model="gpt-5.6-luna")
    service["create_response"]({}, False)
    assert captured == [("gpt-5.6-luna", ("mon-modele-complexe",))]


def test_trip_planner_model_chain_keeps_its_history_and_honours_the_variables(clean_env):
    from services.trip_planner import _trip_models

    assert _trip_models() == ["gpt-5.6-luna", "gpt-5.6-sol"]
    clean_env.setenv("OPENAI_TRIP_MODEL", "modele-voyage")
    clean_env.setenv("OPENAI_MODEL", "mon-modele-rapide")
    clean_env.setenv("OPENAI_COMPLEX_MODEL", "mon-modele-complexe")
    assert _trip_models() == [
        "modele-voyage", "mon-modele-rapide", "gpt-5.6-luna", "mon-modele-complexe", "gpt-5.6-sol",
    ]


def test_model_names_are_written_in_one_place_only():
    """Un nom de modèle écrit en dur ailleurs ignorerait OPENAI_MODEL et OPENAI_COMPLEX_MODEL."""
    services = Path(__file__).resolve().parents[1] / "services"
    offenders = [
        path.name for path in sorted(services.glob("*.py"))
        if path.name != "model_params.py" and "gpt-5.6" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
