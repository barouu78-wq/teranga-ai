from services.chat_service import build_chat_service


def test_chat_service_uses_available_fallback_for_default_model():
    captured = []

    def create_openai_response(client, payload, *, build_kwargs, model, logger, stream, fallback_models):
        captured.append(fallback_models)
        return object()

    service = build_chat_service(
        client=object(),
        model="gpt-5.6-luna",
        logger=object(),
        build_model_kwargs=lambda *args, **kwargs: {},
        reasoning_effort="low",
        search_context_size="low",
        preferred_domains=(),
        create_openai_response=create_openai_response,
        clean_answer=lambda value: value,
        extract_sources=lambda value: [],
        fetch_topic_images=lambda value: None,
        lookup_map=lambda query, enabled: None,
        should_fetch_map=lambda query: False,
    )

    service["create_response"]({}, False)

    assert captured == [("gpt-5.6-sol",)]
