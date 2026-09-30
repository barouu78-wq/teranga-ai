from services.chat_service import select_chat_model


def test_simple_chat_stays_on_luna():
    assert select_chat_model({"planner": False}, "gpt-5.6-luna") == "gpt-5.6-luna"


def test_planner_chat_uses_stronger_model():
    assert select_chat_model({"planner": True}, "gpt-5.6-luna") == "gpt-5.6-sol"


def test_custom_complex_model_can_be_selected():
    assert select_chat_model({"planner": True}, "gpt-5.6-luna", "gpt-5.6-terra") == "gpt-5.6-terra"


def test_existing_non_luna_model_is_not_overridden():
    assert select_chat_model({"planner": True}, "custom-model", "gpt-5.6-sol") == "custom-model"


def test_create_response_uses_selected_model():
    from services.chat_service import build_chat_service

    calls = []

    class FakeResponse:
        output_text = "ok"

    class FakeLogger:
        def info(self, *args, **kwargs):
            pass
        def warning(self, *args, **kwargs):
            pass

    def fake_create(client, payload, *, build_kwargs, model, logger, stream, fallback_models):
        calls.append({"model": model, "kwargs_model": build_kwargs(payload, stream)["model"]})
        return FakeResponse()

    service = build_chat_service(
        client=object(),
        model="gpt-5.6-luna",
        complex_model="gpt-5.6-sol",
        logger=FakeLogger(),
        build_model_kwargs=lambda payload, **kwargs: {"model": kwargs["model"]},
        reasoning_effort=lambda use_web, planner: "low",
        search_context_size=lambda domain, planner: "low",
        preferred_domains=lambda domain: (),
        create_openai_response=fake_create,
        clean_answer=lambda text: text,
        extract_sources=lambda response: [],
        fetch_topic_images=lambda message: None,
        lookup_map=lambda query, enabled: None,
        should_fetch_map=lambda query: False,
    )

    service["create_response"]({"planner": True}, stream=False)

    assert calls == [{"model": "gpt-5.6-sol", "kwargs_model": "gpt-5.6-sol"}]
