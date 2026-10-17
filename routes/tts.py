"""Text-to-speech route registration."""

import os
import re

import httpx
from flask import Response, jsonify, request

from services.latency import LatencyTrace

# Délai propre à la voix. Sans lui, /tts héritait des 50 s du client OpenAI (app.py) avec une nouvelle tentative :
# une lecture a échoué après 130,8 s le 13 octobre 2026. Les lectures réussies mesurées (11-13 octobre) ont toutes
# duré moins de 27 s : 30 s les laisse passer et rend la main bien plus tôt en cas de panne. En flux, la limite de
# lecture vaut entre deux morceaux (httpx) : un fournisseur muet 30 s est abandonné, une longue voix ne l'est pas.
TTS_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

# Voix en flux (conversation vocale) : le fichier WAV entier faisait attendre toute la génération avant le moindre
# son (médiane 15,3 s, p95 21,9 s, lignes « latence route=tts » du 11 au 13 octobre 2026). Avec {"flux": true}, la
# route demande le format « pcm » au fournisseur et relaie chaque morceau dès qu'il arrive. Même texte, mêmes
# consignes, un seul appel : seul le format change, donc pas le coût pour un même texte.
# Format « pcm » d'OpenAI : 16 bits signés, petit-boutiste, mono, 24 000 Hz (source : SDK openai,
# openai/helpers/local_audio_player.py, SAMPLE_RATE = 24000 et lecture en int16). La page lit la même valeur
# (VOICE_PCM_RATE, templates/home.html) : un test vérifie qu'elles restent égales.
TTS_PCM_RATE = 24000
TTS_PCM_MIMETYPE = "audio/pcm"
TTS_STREAM_CHUNK = 4800  # octets lus à la fois chez le fournisseur : 0,1 s de son


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
        flux = data.get("flux") is True
        trace.mode = "flux" if flux else "fichier"
        try:
            from services.voice_quality import tts_instruction
            trace.model = "gpt-4o-mini-tts"
            # Les mêmes réglages en flux et en fichier : seul response_format change.
            params = {
                "model": "gpt-4o-mini-tts",
                "voice": os.getenv("TTS_VOICE", "cedar"),
                "input": text,
                "instructions": tts_instruction(language),
                "speed": 0.98,
                "timeout": TTS_TIMEOUT,
            }
            if flux:
                return stream_speech(trace, params)
            with trace.stage("fournisseur"):
                speech = client.audio.speech.create(response_format="wav", **params)
            return Response(speech.content, mimetype="audio/wav", headers={"Cache-Control": "no-store", "Content-Type": "audio/wav"})
        except Exception:
            app.logger.exception("Erreur /tts")
            return jsonify({"error": "Impossible de générer la voix pour le moment."}), 502

    def stream_speech(trace, params):
        """Relaie le son du fournisseur morceau par morceau. La réponse ne part qu'avec le premier son : une panne
        avant (refus, délai, son vide) reste un 502 lisible, comme en fichier."""
        upstream = client.audio.speech.with_streaming_response.create(response_format="pcm", **params)
        with trace.stage("fournisseur"):
            provider = upstream.__enter__()
            try:
                chunks = provider.iter_bytes(TTS_STREAM_CHUNK)
                first = next((chunk for chunk in chunks if chunk), b"")
                if not first:
                    raise RuntimeError("le fournisseur n'a renvoyé aucun son")
            except BaseException:
                upstream.__exit__(None, None, None)
                raise
        trace.first_sound()
        closed = []

        def close_provider():
            # Une seule fermeture : à la fin du flux, ou dès que le visiteur coupe (« Arrêter »). Le fournisseur
            # cesse alors d'envoyer du son que personne n'écoute.
            if not closed:
                closed.append(True)
                upstream.__exit__(None, None, None)

        def relay():
            try:
                yield first
                for chunk in chunks:
                    if chunk:
                        yield chunk
                trace.ok()
            except Exception:
                trace.status = "erreur"
                app.logger.exception("Erreur /tts (flux coupé)")
            finally:
                close_provider()

        response = Response(relay(), mimetype=TTS_PCM_MIMETYPE, headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
        response.call_on_close(close_provider)  # réponse fermée avant d'avoir été lue : le finally ne passerait pas
        return response

    @app.post("/tts")
    @require_json_post
    def tts():
        # Une ligne de journal « latence » par requête : des nombres, jamais le texte lu à voix haute.
        return LatencyTrace("tts").run(app, tts_body)
