"""Chat response orchestration extracted from the Flask application."""

from .orchestrator import build_agent_plan, run_enrichments


def select_chat_model(payload, model, complex_model="gpt-5.6-sol"):
    """Return the model selected by the bounded agent plan."""
    return build_agent_plan(
        payload,
        model=model,
        complex_model=complex_model,
    ).model


def build_chat_service(
    *,
    client,
    model,
    complex_model="gpt-5.6-sol",
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
    def agent_plan(payload):
        return build_agent_plan(
            payload,
            model=model,
            complex_model=complex_model,
        )

    def model_kwargs(payload, stream):
        plan = agent_plan(payload)
        return build_model_kwargs(
            payload,
            model=plan.model,
            reasoning_effort=reasoning_effort,
            search_context_size=search_context_size,
            preferred_domains=preferred_domains,
            stream=stream,
            reasoning_override=reasoning_override,
        )

    def create_response(payload, stream):
        plan = agent_plan(payload)
        fallback_model = (
            "gpt-5.6-luna"
            if plan.model == complex_model
            else "gpt-5.6-sol"
            if plan.model == "gpt-5.6-luna"
            else "gpt-5.6-luna"
        )
        if hasattr(logger, "info"):
            logger.info(
                "chat_agent_plan model=%s steps=%s planner=%s deep_reasoning=%s web=%s images=%s map=%s",
                plan.model,
                ",".join(plan.steps),
                plan.planner,
                plan.deep_reasoning,
                plan.use_web,
                plan.use_images,
                plan.use_map,
            )
        return create_openai_response(
            client,
            payload,
            build_kwargs=model_kwargs,
            model=plan.model,
            logger=logger,
            stream=stream,
            fallback_models=(fallback_model,),
        )

    def complete_reply(payload):
        response = create_response(payload, stream=False)
        text = clean_answer(getattr(response, "output_text", "") or "")
        plan = agent_plan(payload)
        try:
            image, map_result = run_enrichments(
                plan,
                message=payload.get("message", ""),
                contextual_query=payload.get("contextual_query") or payload.get("message", ""),
                fetch_images=fetch_topic_images,
                lookup_map=lookup_map,
                should_fetch_map=should_fetch_map,
            )
        except Exception:
            logger.exception("Erreur enrichissement agent; réponse texte conservée")
            image, map_result = None, None
        return (
            text,
            extract_sources(response),
            image,
            map_result,
        )

    return {
        "model_kwargs": model_kwargs,
        "create_response": create_response,
        "complete_reply": complete_reply,
    }
