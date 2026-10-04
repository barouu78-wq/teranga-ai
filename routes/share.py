"""Shared answers: /partage page and the token-opening API."""

import secrets

from flask import Response, jsonify, request

from services.shared_answers import MAX_TOKEN, open_token, render_share_page


def register_share_routes(app, site_url):
    @app.get("/partage")
    def shared_answer_page():
        nonce = secrets.token_urlsafe(16)
        # Lu par add_security_headers : le script de la page est autorisé par nonce.
        request._csp_nonce = nonce
        lang = "en" if request.args.get("lang") == "en" else "fr"
        return Response(render_share_page(site_url, nonce, lang), mimetype="text/html")

    @app.post("/api/share/open")
    def open_shared_answer():
        if request.content_length and request.content_length > MAX_TOKEN + 200:
            return jsonify({"error": "invalid"}), 413
        data = request.get_json(silent=True) or {}
        shared = open_token(app.config["SECRET_KEY"], data.get("token") if isinstance(data, dict) else "")
        if shared is None:
            return jsonify({"error": "invalid"}), 400
        return jsonify(shared), 200, {"Cache-Control": "no-store"}
