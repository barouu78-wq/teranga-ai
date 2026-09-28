"""Text-to-speech route registration."""

import os
import re

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
        text = re.sub(r'https?://\S+|www\.\S+', '', text, flags=re.I)
        text = re.sub(r'\[([^\]\n]+)\]\((?:https?://|www\.)[^)]+\)', r'\1', text)
        text = re.sub(r'(^|\n)\s{0,3}#{1,6}\s*', r'\1', text)
        text = re.sub(r'(^|\n)\s*[-*•]+\s+', r'\1', text)
        text = re.sub(r'(^|\n)\s*\d+[.)]\s+', r'\1', text)
        text = re.sub(r'[*_~]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
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
        text = speech_ready_text(sanitize_text(data.get("text", ""), MAX_TTS_LENGTH))
        language = str(data.get("language", "fr")).lower()[:8]
        if language not in SAFE_LANG:
            language = "fr"
        if not text:
            return jsonify({"error": "Texte manquant."}), 400
        try:
            from services.voice_quality import tts_instruction
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=os.getenv("TTS_VOICE", "cedar"),
                input=text,
                instructions=tts_instruction(language),
                response_format="wav",
                speed=0.98,
            )
            return Response(speech.content, mimetype="audio/wav", headers={"Cache-Control": "no-store", "Content-Type": "audio/wav"})
        except Exception:
            app.logger.exception("Erreur /tts")
            return jsonify({"error": "Impossible de générer la voix pour le moment."}), 502
