        "intent_context": intent_context,
        "contextual_query": enriched_context,
    }, None


def create_response(payload, stream):
    fallback_model = "gpt-5.6-luna" if MODEL == "gpt-6-luna" else "gpt-6-luna"
    return _create_openai_response(
        client,
        payload,
        build_kwargs=model_kwargs,
        model=MODEL,
        logger=app.logger,
        stream=stream,
        fallback_models=(fallback_model,),
    )


def model_kwargs(payload, stream):
    return build_model_kwargs(
        payload,
        model=MODEL,
        reasoning_effort=reasoning_effort,
        search_context_size=search_context_size,
        preferred_domains=preferred_domains,
        stream=stream,
        reasoning_override=os.getenv("OPENAI_REASONING_EFFORT") or None,
    )


