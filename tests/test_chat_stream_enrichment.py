from services.chat_service import build_chat_service


def test_stream_enrichments_follow_agent_plan():
    calls = []

    def fetch_images(message):
        calls.append(("image", message))
        return "img"

    def lookup_map(query, enabled):
        calls.append(("map", query, enabled))
        return "map"

    service = build_chat_service(
        client=object(),
        model="gpt-5.6-luna",
        logger=object(),
        build_model_kwargs=lambda *args, **kwargs: {},
        reasoning_effort=lambda *args: "low",
        search_context_size=lambda *args: "low",
        preferred_domains=lambda *args: (),
        create_openai_response=lambda *args, **kwargs: object(),
        clean_answer=lambda value: value,
        extract_sources=lambda value: [],
        fetch_topic_images=fetch_images,
        lookup_map=lookup_map,
        should_fetch_map=lambda query: True,
    )

    payload = {
        "message": "Quelles photos de Dakar ?",
        "contextual_query": "Dakar",
        "intent_context": {"intent": "photos", "needs_images": True, "location": "dakar"},
    }
    image, maps = service["complete_enrichments"](payload)

    assert image == "img"
    assert maps is None
    assert calls == [("image", "Quelles photos de Dakar ?")]


def test_stream_enrichments_skip_unselected_tools():
    calls = []

    service = build_chat_service(
        client=object(),
        model="gpt-5.6-luna",
        logger=object(),
        build_model_kwargs=lambda *args, **kwargs: {},
        reasoning_effort=lambda *args: "low",
        search_context_size=lambda *args: "low",
        preferred_domains=lambda *args: (),
        create_openai_response=lambda *args, **kwargs: object(),
        clean_answer=lambda value: value,
        extract_sources=lambda value: [],
        fetch_topic_images=lambda message: calls.append("image"),
        lookup_map=lambda query, enabled: calls.append("map"),
        should_fetch_map=lambda query: True,
    )

    payload = {
        "message": "Explique-moi la culture sénégalaise.",
        "intent_context": {"intent": "culture", "needs_images": False, "location": None},
    }
    image, maps = service["complete_enrichments"](payload)

    assert image is None
    assert maps is None
    assert calls == []
