from services.model_params import build_model_kwargs


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
