"""Text-to-speech route registration."""

import os
import re

import httpx
from flask import Response, jsonify, request

from services.latency import LatencyTrace

# Délai propre à la voix. Sans lui, /tts héritait des 50 s du client OpenAI (app.py) avec une nouvelle tentative :
# une lecture a échoué après 130,8 s le 13 octobre 2026. 5 s pour se connecter, 30 s au plus sans recevoir d'octet
# (le son arrive en flux : c'est l'attente entre deux morceaux, pas la durée totale), sans nouvelle tentative.
TTS_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
TTS_CHUNK_BYTES = 4096  # ≈ 1 s de MP3 : le premier morceau part sans attendre


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
        # Liens Markdown d'abord (on garde le texte), puis les adresses nues.
        text = re.sub(r'\[([^\]\n]+)\]\((?:https?://|www\.)[^)]+\)', r'\1', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text, flags=re.I)
        text = re.sub(r'(^|\n)\s{0,3}#{1,6}\s*', r'\1', text)
        text = re.sub(r'(^|\n)\s*[-*•]+\s+', r'\1', text)
        text = re.sub(r'(^|\n)\s*\d+[.)]\s+', r'\1', text)
        text = re.sub(r'[*_~]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:MAX_TTS_LENGTH]

    def tts_body(trace):
        ip = client_ip()
        identity = abuse_key(ip)
        if abuse_blocked(ip) or abuse_blocked(identity):
            return jsonify({"error": "Trop de demandes vocales rapprochées. Réessaie dans quelques minutes."}), 429, {"Retry-After": "120"}
        if not allowed_request(ip, tts_request_log[ip], TTS_RATE_LIMIT, 60, "tts") or not allowed_request(identity, tts_request_log[identity], TTS_RATE_LIMIT, 60, "tts_identity"):
            record_abuse(ip, "tts_rate", 2)
            record_abuse(identity, "tts_identity_rate", 1)
            return jsonify({"error": "Trop de demandes vocales. Réessaie dans un instant."}), 429, {"Retry-After": "8"}
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
        # Le son part vers le navigateur dès ses premiers octets (MP3, compressé) au lieu d'attendre toute la
        # génération en WAV (11 à 18 s mesurées sur Render) : le navigateur commence à lire pendant la suite.
        upstream = None
        try:
            from services.voice_quality import tts_instruction
            trace.model = "gpt-4o-mini-tts"
            trace.begin("fournisseur")
            upstream = client.with_options(max_retries=0).audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice=os.getenv("TTS_VOICE", "cedar"),
                input=text,
                instructions=tts_instruction(language),
                response_format="mp3",
                speed=0.98,
                timeout=TTS_TIMEOUT,
            )
            chunks = upstream.__enter__().iter_bytes(TTS_CHUNK_BYTES)
            first = next((chunk for chunk in chunks if chunk), b"")
            if not first:
                raise RuntimeError("voix vide")
        except Exception:
            trace.end("fournisseur")
            if upstream is not None:
                upstream.__exit__(None, None, None)
            app.logger.exception("Erreur /tts")
            return jsonify({"error": "Impossible de générer la voix pour le moment."}), 502
        # premier_mot_ms de la ligne de latence = premier octet de son envoyé ; fournisseur_ms = toute la génération.
        trace.first_word()
        trace.begin("fournisseur")

        def audio():
            try:
                yield first
                for chunk in chunks:
                    if chunk:
                        yield chunk
                trace.ok()
            except Exception:
                # Coupure en plein flux : le début déjà envoyé se lit, la ligne de latence dit « erreur », et l'erreur
                # remonte pour que la connexion soit coupée sans fin de flux propre : le navigateur voit l'échec et ne
                # garde pas en cache un son tronqué.
                trace.status = "erreur"
                app.logger.exception("Erreur /tts (flux)")
                raise
            finally:
                trace.end("fournisseur")
                upstream.__exit__(None, None, None)

        return Response(audio(), mimetype="audio/mpeg", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.post("/tts")
    @require_json_post
    def tts():
        # Une ligne de journal « latence » par requête : des nombres, jamais le texte lu à voix haute.
        return LatencyTrace("tts").run(app, tts_body)
