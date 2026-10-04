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


def _service(fetch_images, create_openai_response):
    return build_chat_service(
        client=object(),
        model="gpt-5.6-luna",
        logger=object(),
        build_model_kwargs=lambda *args, **kwargs: {},
        reasoning_effort=lambda *args: "low",
        search_context_size=lambda *args: "low",
        preferred_domains=lambda *args: (),
        create_openai_response=create_openai_response,
        clean_answer=lambda value: value,
        extract_sources=lambda value: [],
        fetch_topic_images=fetch_images,
        lookup_map=lambda query, enabled: None,
        should_fetch_map=lambda query: False,
    )


PHOTO_PAYLOAD = {
    "message": "Quelles photos de Dakar ?",
    "contextual_query": "Dakar",
    "intent_context": {"intent": "photos", "needs_images": True, "location": "dakar"},
}


def test_complete_reply_fetches_images_while_model_answers():
    import threading

    image_started = threading.Event()

    def fetch_images(message):
        image_started.set()
        return "img"

    class Response:
        output_text = "Réponse"

    def create_openai_response(*args, **kwargs):
        # The image lookup must already be running while the model works.
        assert image_started.wait(timeout=2)
        return Response()

    text, sources, image, maps = _service(fetch_images, create_openai_response)["complete_reply"](PHOTO_PAYLOAD)
    assert (text, image) == ("Réponse", "img")


def test_enrichment_failure_does_not_break_reply():
    def fetch_images(message):
        raise RuntimeError("image backend down")

    service = _service(fetch_images, lambda *a, **k: object())
    future = service["start_enrichments"](PHOTO_PAYLOAD)
    assert service["enrichment_result"](future) == (None, None)


def test_chat_route_starts_enrichments_before_streaming():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "routes" / "chat.py").read_text(encoding="utf-8")
    assert source.index("start_chat_enrichments(payload)") < source.index("create_response(payload, stream=True)")
