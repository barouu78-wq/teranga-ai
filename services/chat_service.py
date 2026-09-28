"""Chat response orchestration extracted from the Flask application."""


def build_chat_service(
    *,
    client,
    model,
    logger,
    build_model_kwargs,
    reasoning_effort,
    search_context_size,
    preferred_domains,
    create_openai_response,
    clean_answer,
    extract_sources,
    fetch_topic_images,
    lookup_map,
    should_fetch_map,
    reasoning_override=None,
):
    def model_kwargs(payload, stream):
        return build_model_kwargs(
            payload,
            model=model,
            reasoning_effort=reasoning_effort,
            search_context_size=search_context_size,
            preferred_domains=preferred_domains,
            stream=stream,
            reasoning_override=reasoning_override,
        )

    def create_response(payload, stream):
        fallback_model = "gpt-5.6-sol" if model == "gpt-5.6-luna" else "gpt-5.6-luna"
        return create_openai_response(
            client,
            payload,
            build_kwargs=model_kwargs,
            model=model,
            logger=logger,
            stream=stream,
            fallback_models=(fallback_model,),
        )

    def complete_reply(payload):
        response = create_response(payload, stream=False)
        text = clean_answer(getattr(response, "output_text", "") or "")
        try:
            image = fetch_topic_images(payload.get("message", ""))
        except Exception:
            logger.exception("Erreur récupération images; réponse texte conservée")
            image = None
        map_query = payload.get("contextual_query") or payload.get("message", "")
        return (
            text,
            extract_sources(response),
            image,
            lookup_map(map_query, should_fetch_map(map_query)),
        )

    return {
        "model_kwargs": model_kwargs,
        "create_response": create_response,
        "complete_reply": complete_reply,
    }
