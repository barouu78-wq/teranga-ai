"""Chat response orchestration extracted from the Flask application."""

import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from .backup_ai import claude_events, claude_is_primary, claude_response
from .model_params import clean_model_name, openai_complex_model, openai_model
from .orchestrator import build_agent_plan, run_enrichments

# Images et carte dépendent d'appels réseau lents (Google, Wikimedia) : elles
# sont lancées en parallèle de la génération du texte au lieu de l'attendre.
_ENRICHMENT_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="teranga-enrich")
ENRICHMENT_TIMEOUT = 12.0


def select_chat_model(payload, model, complex_model=None):
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
    complex_model=None,
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
    # L'application transmet les variables d'environnement telles quelles : un nom vide ou
    # invalide retombe sur la valeur configurée, puis sur le défaut (voir model_params.py).
    model = clean_model_name(model, openai_model())
    complex_model = clean_model_name(complex_model, openai_complex_model())

    # Le plan est déterministe pour une requête : calculé une fois, puis réutilisé
    # par create_response, model_kwargs et les enrichissements.
    plans = OrderedDict()

    def agent_plan(payload):
        key = id(payload)
        hit = plans.get(key)
        if hit is not None and hit[0] is payload:
            return hit[1]
        plan = build_agent_plan(
            payload,
            model=model,
            complex_model=complex_model,
        )
        plans[key] = (payload, plan)
        while len(plans) > 32:
            plans.popitem(last=False)
        return plan

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

    def claude_kwargs(payload):
        return {
            "system": payload.get("instructions", ""),
            "max_tokens": 4000,
            "timeout": 60.0,
            "web": bool(payload.get("use_web")),
        }

    def claude_stream(payload):
        """Flux Claude ; si Claude échoue avant d'écrire, OpenAI prend le relais."""
        wrote = False
        try:
            for event in claude_events(payload.get("input_text") or payload.get("message", ""), **claude_kwargs(payload)):
                if event.type == "response.output_text.delta":
                    wrote = True
                yield event
        except Exception:
            if wrote:
                raise
            if hasattr(logger, "exception"):
                logger.exception("chat_claude_primary_failed")
            yield from openai_response(payload, True)

    def create_response(payload, stream):
        if claude_is_primary():
            if hasattr(logger, "info"):
                logger.info("chat_ai_provider claude")
            if stream:
                return claude_stream(payload)
            try:
                return claude_response(payload.get("input_text") or payload.get("message", ""), **claude_kwargs(payload))
            except Exception:
                if hasattr(logger, "exception"):
                    logger.exception("chat_claude_primary_failed")
        return openai_response(payload, stream)

    def openai_response(payload, stream):
        plan = agent_plan(payload)
        # Secours = l'autre modèle configuré (et non des noms en dur).
        fallback_model = model if plan.model == complex_model else complex_model
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
            fallback_models=tuple(m for m in (fallback_model,) if m and m != plan.model),
        )

    def complete_enrichments(payload):
        started_at = time.perf_counter()
        plan = agent_plan(payload)
        result = run_enrichments(
            plan,
            message=payload.get("message", ""),
            contextual_query=payload.get("contextual_query") or payload.get("message", ""),
            fetch_images=fetch_topic_images,
            lookup_map=lookup_map,
            should_fetch_map=should_fetch_map,
            logger=logger,
        )
        if hasattr(logger, "info"):
            logger.info("chat_enrichment_ms %.2f", (time.perf_counter() - started_at) * 1000)
        return result

    def start_enrichments(payload):
        """Start image/map enrichment in the background; returns a future."""
        return _ENRICHMENT_EXECUTOR.submit(complete_enrichments, payload)

    def enrichment_result(future):
        try:
            return future.result(timeout=ENRICHMENT_TIMEOUT)
        except Exception:
            if hasattr(logger, "exception"):
                logger.exception("chat_enrichment_failed")
            return None, None

    def complete_reply(payload):
        enrichments = start_enrichments(payload)
        response = create_response(payload, stream=False)
        text = clean_answer(getattr(response, "output_text", "") or "")
        image, map_result = enrichment_result(enrichments)
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
        "complete_enrichments": complete_enrichments,
        "start_enrichments": start_enrichments,
        "enrichment_result": enrichment_result,
    }
