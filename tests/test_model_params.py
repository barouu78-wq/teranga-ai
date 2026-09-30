from services.model_params import build_model_kwargs


def test_build_model_kwargs_keeps_fast_chat_defaults():
    result = build_model_kwargs(
        {"use_web": False, "planner": False, "instructions": "i", "input_text": "q"},
        model="gpt-test",
        reasoning_effort=lambda web, planner: "low",
        search_context_size=lambda domain, planner: "medium",
        preferred_domains=lambda domain: (),
        stream=True,
    )
    assert result["model"] == "gpt-test"
    assert result["max_output_tokens"] == 400
    assert result["reasoning"] == {"effort": "low"}
    assert "tools" not in result


def test_build_model_kwargs_adds_web_tool_and_domains():
    result = build_model_kwargs(
        {
            "use_web": True,
            "planner": False,
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
    assert result["max_output_tokens"] == 600
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
