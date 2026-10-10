"""Speech-to-text route registration."""

import io

import os

from flask import jsonify, request


def audio_filename(raw: bytes, declared: str = "") -> str:
    """Nom de fichier cohérent avec le vrai format de l'enregistrement.

    Le fournisseur de transcription déduit le format du nom du fichier : un enregistrement MP4/AAC
    (iPhone, Safari) nommé « .webm » est rejeté. On lit donc les premiers octets plutôt que de croire le nom
    envoyé par le navigateur (qui peut aussi venir d'une ancienne version du site gardée en mémoire).
    """
    head = bytes(raw[:12])
    if head[4:8] == b"ftyp":
        return "voice.m4a"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "voice.webm"
    if head[:4] == b"OggS":
        return "voice.ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "voice.wav"
    if head[:4] == b"fLaC":
        return "voice.flac"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "voice.mp3"
    return declared if declared in {"voice.webm", "voice.m4a", "voice.ogg", "voice.wav", "voice.mp3", "voice.flac"} else "voice.webm"


def register_stt_route(app, deps):
    origin_allowed = deps["origin_allowed"]
    valid_request_token = deps["valid_request_token"]
    valid_token = deps["valid_token"]
    CSRF_COOKIE = deps["CSRF_COOKIE"]
    CSRF_HEADER = deps["CSRF_HEADER"]
    CSRF_TTL = deps["CSRF_TTL"]
    client_ip = deps["client_ip"]
    abuse_key = deps["abuse_key"]
    abuse_blocked = deps["abuse_blocked"]
    allowed_request = deps["allowed_request"]
    record_abuse = deps["record_abuse"]
    stt_request_log = deps["stt_request_log"]
    stt_hourly_log = deps["stt_hourly_log"]
    STT_RATE_LIMIT = deps["STT_RATE_LIMIT"]
    STT_HOURLY_LIMIT = deps["STT_HOURLY_LIMIT"]
    SAFE_LANG = deps["SAFE_LANG"]
    MAX_MESSAGE_LENGTH = deps["MAX_MESSAGE_LENGTH"]
    sanitize_text = deps["sanitize_text"]
    public_error = deps["public_error"]
    _field = deps["_field"]
    client = deps["client"]

    @app.post("/stt")
    def stt():
        """Transcribe a short voice turn for hands-free conversation."""
        if not origin_allowed():
            return jsonify({"error": "Origine non autorisée."}), 403
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")
        if not valid_request_token(
            cookie_token,
            header_token,
            secret_key=app.config["SECRET_KEY"],
            ttl=CSRF_TTL,
            validator=valid_token,
        ):
            return jsonify({"error": "csrf"}), 403
        from services.voice_quality import transcription_prompt

        ip = client_ip()
        identity = abuse_key(ip)
        if abuse_blocked(ip) or abuse_blocked(identity):
            return jsonify({"error": "Trop de demandes vocales rapprochées. Réessaie dans quelques minutes."}), 429, {"Retry-After": "120"}
        if not allowed_request(ip, stt_request_log[ip], STT_RATE_LIMIT, 60, "stt") or not allowed_request(identity, stt_request_log[identity], STT_RATE_LIMIT, 60, "stt_identity"):
            record_abuse(ip, "stt_rate", 2)
            record_abuse(identity, "stt_identity_rate", 1)
            return jsonify({"error": "Trop de transcriptions vocales. Réessaie dans un instant."}), 429, {"Retry-After": "15"}
        if not allowed_request(ip, stt_hourly_log[ip], STT_HOURLY_LIMIT, 3600, "stt_hour") or not allowed_request(identity, stt_hourly_log[identity], STT_HOURLY_LIMIT, 3600, "stt_identity_hour"):
            record_abuse(ip, "stt_hourly", 3)
            record_abuse(identity, "stt_identity_hour", 1)
            return jsonify({"error": "Trop de transcriptions vocales sur une courte période. Réessaie plus tard."}), 429, {"Retry-After": "300"}
        upload = request.files.get("audio")
        if upload is None:
            return jsonify({"error": "Audio manquant."}), 400
        raw = upload.read(3 * 1024 * 1024 + 1)
        if not raw:
            return jsonify({"error": "Audio vide."}), 400
        if len(raw) > 3 * 1024 * 1024:
            return jsonify({"error": "Enregistrement trop long."}), 413
        language = str(request.form.get("language", "fr")).lower()[:8]
        if language not in SAFE_LANG:
            language = "fr"
        try:
            audio_file = io.BytesIO(raw)
            audio_file.name = audio_filename(raw)
            kwargs = {
                "model": os.getenv("STT_MODEL", "gpt-4o-transcribe"),
                "file": audio_file,
                "chunking_strategy": "auto",
            }
            # Le modèle de transcription ne connaît pas le wolof ni le pulaar : on le laisse
            # détecter la langue (comme realtime.py), le prompt garde le vocabulaire local.
            if language in {"fr", "en"}:
                kwargs["language"] = language
            voice_context = sanitize_text(request.form.get("context", ""), 1800).strip()
            base_prompt = transcription_prompt(language) + " Contexte : Sénégal, Dakar, AIBD, Gorée, Rufisque, Thiès, Saint-Louis, Saly, Casamance, FCFA, BCEAO."
            kwargs["prompt"] = base_prompt + (f" Contexte récent de la conversation : {voice_context}" if voice_context else "")
            result = client.audio.transcriptions.create(**kwargs)
            text = _field(result, "text", "") or ""
            text = sanitize_text(text, MAX_MESSAGE_LENGTH).strip()
            return jsonify({"text": text})
        except Exception as exc:
            app.logger.exception("Erreur /stt")
            return jsonify({"error": public_error(exc)}), 500
    