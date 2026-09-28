"""Text-to-speech route registration."""

import os

from flask import Response, jsonify, request


def register_tts_route(app, deps):
    require_json_post = deps["require_json_post"]
    client_ip = deps["client_ip"]
    abuse_key = deps["abuse_key"]
    abuse_blocked = deps["abuse_blocked"]
    allowed_request = deps["allowed_request"]
    record_abuse = deps["record_abuse"]
    tts_request_log = deps["tts_request_log"]
    tts_hourly_log = deps["tts_hourly_log"]
    TTS_RATE_LIMIT = deps["TTS_RATE_LIMIT"]
    TTS_HOURLY_LIMIT = deps["TTS_HOURLY_LIMIT"]
    SAFE_LANG = deps["SAFE_LANG"]
    MAX_TTS_LENGTH = deps["MAX_TTS_LENGTH"]
    sanitize_text = deps["sanitize_text"]
    client = deps["client"]

    def speech_ready_text(text: str) -> str:
        text = __import__("re").sub(r"https?://\S+|www\.\S+", "", text, flags=__import__("re").I)
        text = __import__("re").sub(r"\[([^\]\n]+)\]\((?:https?://|www\.)[^)]+\)", r"\1", text)
        text = __import__("re").sub(r"(^|\n)\s{0,3}#{1,6}\s*", r"\1", text)
        text = __import__("re").sub(r"(^|\n)\s*[-*•]+\s+", r"\1", text)
        text = __import__("re").sub(r"(^|\n)\s*\d+[.)]\s+", r"\1", text)
        text = __import__("re").sub(r"[*_~`]+", "", text)
        text = __import__("re").sub(r"\s+", " ", text).strip()
        return text[:MAX_TTS_LENGTH]

@app.post("/tts")
@require_json_post
def tts():
    ip = client_ip()
    identity = abuse_key(ip)
    if abuse_blocked(ip) or abuse_blocked(identity):
        return jsonify({"error": "Trop de demandes vocales rapprochées. Réessaie dans quelques minutes."}), 429, {"Retry-After": "120"}
    if not allowed_request(ip, tts_request_log[ip], TTS_RATE_LIMIT, 60, "tts") or not allowed_request(identity, tts_request_log[identity], TTS_RATE_LIMIT, 60, "tts_identity"):
        record_abuse(ip, "tts_rate", 2)
        record_abuse(identity, "tts_identity_rate", 1)
        return jsonify({"error": "Trop de demandes vocales. Réessaie dans un instant."}), 429
    if not allowed_request(ip, tts_hourly_log[ip], TTS_HOURLY_LIMIT, 3600, "tts_hour") or not allowed_request(identity, tts_hourly_log[identity], TTS_HOURLY_LIMIT, 3600, "tts_identity_hour"):
        record_abuse(ip, "tts_hourly", 3)
        record_abuse(identity, "tts_identity_hour", 1)
        return jsonify({"error": "Trop de demandes vocales sur une courte période. Réessaie plus tard."}), 429, {"Retry-After": "300"}
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Requête invalide."}), 400
    text = sanitize_text(data.get("text", ""), MAX_TTS_LENGTH)
    text = speech_ready_text(text)
    language = str(data.get("language", "fr")).lower()[:8]
    if language not in SAFE_LANG:
        language = "fr"
    if not text:
        return jsonify({"error": "Texte manquant."}), 400
    language_name = {
        "fr": "French",
        "en": "English",
        "wo": "Wolof",
        "ff": "Pulaar, a Fulah language of northern Senegal",
    }[language]
    try:
        voice_instructions = tts_instruction(language)
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=os.getenv("TTS_VOICE", "cedar"),
            input=text,
            instructions=voice_instructions,
            response_format="wav",
            speed=0.98,
        )
        return Response(speech.content, mimetype="audio/wav", headers={"Cache-Control": "no-store", "Content-Type": "audio/wav"})
    except Exception:
        app.logger.exception("Erreur /tts")

register_stt_route(app, {"origin_allowed": origin_allowed, "valid_request_token": valid_request_token, "valid_token": valid_token, "CSRF_COOKIE": CSRF_COOKIE, "CSRF_HEADER": CSRF_HEADER, "CSRF_TTL": CSRF_TTL, "client_ip": client_ip, "abuse_key": abuse_key, "abuse_blocked": abuse_blocked, "allowed_request": allowed_request, "record_abuse": record_abuse, "stt_request_log": stt_request_log, "stt_hourly_log": stt_hourly_log, "STT_RATE_LIMIT": STT_RATE_LIMIT, "STT_HOURLY_LIMIT": STT_HOURLY_LIMIT, "SAFE_LANG": SAFE_LANG, "MAX_MESSAGE_LENGTH": MAX_MESSAGE_LENGTH, "sanitize_text": sanitize_text, "public_error": public_error, "_field": _field, "client": client})