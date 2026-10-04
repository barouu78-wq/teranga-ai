"""Chat route registration."""

import json
import re
import time

from flask import Response, jsonify, request, stream_with_context

from services.places import mentioned_places
from services.shared_answers import sign_answer


def register_chat_route(app, deps):
    require_json_post = deps["require_json_post"]
    client_ip = deps["client_ip"]
    abuse_key = deps["abuse_key"]
    abuse_blocked = deps["abuse_blocked"]
    allowed_request = deps["allowed_request"]
    record_abuse = deps["record_abuse"]
    request_log = deps["request_log"]
    chat_hourly_log = deps["chat_hourly_log"]
    RATE_LIMIT = deps["RATE_LIMIT"]
    RATE_WINDOW = deps["RATE_WINDOW"]
    CHAT_HOURLY_LIMIT = deps["CHAT_HOURLY_LIMIT"]
    web_request_log = deps["web_request_log"]
    WEB_RATE_LIMIT = deps["WEB_RATE_LIMIT"]
    WEB_RATE_WINDOW = deps["WEB_RATE_WINDOW"]
    parse_chat_payload = deps["parse_chat_payload"]
    complete_reply = deps["complete_reply"]
    create_response = deps["create_response"]
    run_chat_enrichments = deps.get("run_chat_enrichments")
    start_chat_enrichments = deps.get("start_chat_enrichments")
    chat_enrichment_result = deps.get("chat_enrichment_result")
    extract_sources = deps["extract_sources"]
    event_delta = deps["event_delta"]
    clean_answer = deps["clean_answer"]
    fetch_topic_images = deps["fetch_topic_images"]
    public_error = deps["public_error"]
    share_secret = deps.get("share_secret", "")
    knowledge_places = deps.get("knowledge_places") or []
    field = deps["field"]
    logger = deps.get("logger", app.logger)

    @app.post("/chat")
    @require_json_post
    def chat():
        ip = client_ip()
        identity = abuse_key(ip)
        if abuse_blocked(ip) or abuse_blocked(identity):
            return jsonify({"error": "Trop de demandes rapprochées. Réessaie dans quelques minutes."}), 429, {"Retry-After": "120"}
        if not allowed_request(ip, request_log[ip], RATE_LIMIT, RATE_WINDOW, "chat"):
            record_abuse(ip, "chat_rate", 2)
            return jsonify({"error": "Trop de demandes. Attends quelques secondes puis réessaie."}), 429, {"Retry-After": "8"}
        if not allowed_request(ip, chat_hourly_log[ip], CHAT_HOURLY_LIMIT, 3600, "chat_hour") or not allowed_request(identity, chat_hourly_log[identity], CHAT_HOURLY_LIMIT, 3600, "chat_identity"):
            record_abuse(ip, "chat_hourly", 3)
            record_abuse(identity, "chat_identity_hour", 1)
            return jsonify({"error": "Trop de demandes sur une courte période. Réessaie plus tard."}), 429, {"Retry-After": "300"}

        parse_started_at = time.perf_counter()
        payload, error = parse_chat_payload()
        logger.info("chat_payload_ms %.2f", (time.perf_counter() - parse_started_at) * 1000)
        if error:
            return error
        if payload["use_web"]:
            web_identity = abuse_key(client_ip())
            if abuse_blocked(web_identity):
                return jsonify({"error": "Trop de recherches rapprochées. Réessaie dans quelques minutes."}), 429, {"Retry-After": "120"}
            if not allowed_request(web_identity, web_request_log[web_identity], WEB_RATE_LIMIT, WEB_RATE_WINDOW, "web"):
                record_abuse(web_identity, "web_rate", 2)
                return jsonify({"error": "Trop de recherches web rapprochées. Réessaie dans un instant."}), 429, {"Retry-After": "20"}

        photo_only = bool(payload.get("photo_only"))
        photo_query = str(payload.get("photo_query") or payload.get("message", ""))
        if photo_only:
            language = payload.get("language", "fr")

            def photo_lead(image):
                # Le texte nomme le sujet réellement cherché et ne promet jamais
                # des photos absentes.
                subject = str(((image or [{}])[0] or {}).get("search_query") or "").strip()
                # « Saly Sénégal » est une précision de recherche, pas le sujet.
                subject = re.sub(r"\s+s[ée]n[ée]gal$", "", subject, flags=re.I) or subject
                if language == "en":
                    if image:
                        return f"Here are some photos for “{subject}”." if subject else "Here are some photos."
                    return "I couldn't find a reliable photo for this request. Try naming a specific place, for example Gorée, Saint-Louis or Lompoul."
                if image:
                    return f"Voici quelques photos pour « {subject} »." if subject else "Voici quelques photos."
                return "Je n'ai pas trouvé de photo fiable pour cette demande. Essaie en précisant un lieu, par exemple Gorée, Saint-Louis ou Lompoul."

            if request.headers.get("X-Teranga-Mode", "").lower() == "json":
                try:
                    image = fetch_topic_images(photo_query)
                    return jsonify({"reply": photo_lead(image), "sources": [], "image": image, "map": None})
                except Exception as exc:
                    logger.exception("Erreur photo-only /chat")
                    return jsonify({"error": public_error(exc, payload.get("language", "fr"))}), 503, {"Retry-After": "10"}

            def generate_photo_only():
                try:
                    image = fetch_topic_images(photo_query)
                    yield json.dumps({"d": photo_lead(image)}, ensure_ascii=False) + "\n"
                    if image:
                        yield json.dumps({"img": image}, ensure_ascii=False) + "\n"
                    yield json.dumps({"done": True}) + "\n"
                except Exception as exc:
                    logger.exception("Erreur stream photo-only /chat")
                    yield json.dumps({"error": public_error(exc, payload.get("language", "fr"))}, ensure_ascii=False) + "\n"

            return Response(stream_with_context(generate_photo_only()), mimetype="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})

        if request.headers.get("X-Teranga-Mode", "").lower() == "json":
            try:
                reply, sources, image, maps = complete_reply(payload)
                if not reply:
                    reply = "Je n'ai pas réussi à répondre. Réessaie."
                share = sign_answer(share_secret, payload.get("message", ""), reply, sources, payload.get("language", "fr"))
                return jsonify({"reply": reply, "share": share, "places": mentioned_places(payload.get("message", ""), knowledge_places), "sources": sources, "image": image, "map": maps, "itinerary_edit": payload.get("trip_edit_proposal"), "ux": payload.get("ux_hints"), "action": payload.get("action_request")})
            except Exception as exc:
                logger.exception("Erreur JSON /chat")
                return jsonify({"error": public_error(exc, payload.get("language", "fr"))}), 503, {"Retry-After": "10"}

        def generate():
            started_at = time.perf_counter()
            model_started_at = time.perf_counter()
            first_output_logged = False
            yielded = False
            sources = []
            answer_parts = []
            # Les enrichissements (images, carte) tournent pendant que le modèle écrit.
            enrichments = (
                start_chat_enrichments(payload)
                if start_chat_enrichments and chat_enrichment_result
                else None
            )
            try:
                stream = create_response(payload, stream=True)
                logger.info("chat_model_startup_ms %.2f", (time.perf_counter() - model_started_at) * 1000)
                for event in stream:
                    etype = getattr(event, "type", "") or ""
                    if etype == "response.failed":
                        failed = getattr(event, "response", None)
                        failure = field(failed, "error", None)
                        message = field(failure, "message", None) or field(failure, "code", None) or "La réponse IA a échoué."
                        raise RuntimeError(f"OpenAI response.failed: {message}")
                    if "annotation" in etype or "web_search" in etype or "output_item" in etype or etype.endswith(".completed"):
                        extra = extract_sources(event)
                        if extra:
                            sources = extra
                    delta = event_delta(event)
                    if delta:
                        if not first_output_logged:
                            first_output_logged = True
                            logger.info("chat_ttfb_ms %.2f", (time.perf_counter() - started_at) * 1000)
                        yielded = True
                        answer_parts.append(delta)
                        yield json.dumps({"d": delta}, ensure_ascii=False) + "\n"
                    elif etype == "response.completed":
                        if not first_output_logged:
                            first_output_logged = True
                            logger.info("chat_ttfb_ms %.2f", (time.perf_counter() - started_at) * 1000)
                        text = ""
                        resp = getattr(event, "response", None)
                        if resp is not None:
                            text = getattr(resp, "output_text", "") or ""
                            sources = extract_sources(resp, event) or sources
                        if text and not yielded:
                            yielded = True
                            answer_parts.append(clean_answer(text))
                            yield json.dumps({"d": answer_parts[-1]}, ensure_ascii=False) + "\n"
                if not yielded:
                    reply, sources, image, maps = complete_reply(payload)
                    if reply:
                        answer_parts.append(reply)
                        yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
                else:
                    if enrichments is not None:
                        image, maps = chat_enrichment_result(enrichments)
                    elif run_chat_enrichments:
                        image, maps = run_chat_enrichments(payload)
                    else:
                        image = None
                        maps = None
                if sources:
                    yield json.dumps({"s": sources}, ensure_ascii=False) + "\n"
                if image:
                    yield json.dumps({"img": image}, ensure_ascii=False) + "\n"
                if maps:
                    yield json.dumps({"map": maps}, ensure_ascii=False) + "\n"
                if payload.get("trip_edit_proposal"):
                    yield json.dumps({"itinerary_edit": payload["trip_edit_proposal"]}, ensure_ascii=False) + "\n"
                if payload.get("ux_hints"):
                    yield json.dumps({"ux": payload["ux_hints"]}, ensure_ascii=False) + "\n"
                if payload.get("action_request"):
                    yield json.dumps({"action": payload["action_request"]}, ensure_ascii=False) + "\n"
                # Lieux de la base cités dans la question : lien vers leur fiche /lieux.
                places = mentioned_places(payload.get("message", ""), knowledge_places)
                if places:
                    yield json.dumps({"places": places}, ensure_ascii=False) + "\n"
                share = sign_answer(share_secret, payload.get("message", ""), clean_answer("".join(answer_parts)), sources, payload.get("language", "fr"))
                if share:
                    yield json.dumps({"share": share}) + "\n"
                yield json.dumps({"done": True}) + "\n"
            except Exception as exc:
                logger.exception("Erreur stream /chat")
                yield json.dumps({"error": public_error(exc, payload.get("language", "fr"))}, ensure_ascii=False) + "\n"

        return Response(stream_with_context(generate()), mimetype="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})
