"""« Donner mon avis » : un bug, une idée ou une remarque des utilisateurs (site et appli Android).

Les avis sont gardés comme les demandes de partenariat (services/partner_requests.py : Redis, 200 au plus,
environ un an) et lus dans la page privée /stats-partenaires. Aucun outil extérieur : tout reste sur le site.
"""

from __future__ import annotations

import re
from html import escape

from flask import Response, jsonify, request

from services.site_layout import HEAD_ASSETS, asset_url, site_footer, site_header

AVIS_KEY = "teranga:avis"
AVIS_KINDS = {
    "bug": "Quelque chose ne marche pas",
    "idee": "Une idée d'amélioration",
    "autre": "Autre remarque",
}


def _clean(value, limit: int) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or "")).strip()
    return re.sub(r"\s{2,}", " ", text)[:limit]


def render_avis_page() -> str:
    options = "".join(
        f'<p><label><input type="radio" name="kind" value="{escape(key)}"{" checked" if key == "bug" else ""}> {escape(label)}</label></p>'
        for key, label in AVIS_KINDS.items()
    )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Donner mon avis | Teranga AI</title>
<meta name="description" content="Un bug, une idée ? Dites-le à l'équipe de Teranga AI en une minute.">
<meta name="robots" content="noindex,follow">{HEAD_ASSETS}</head>
<body>{site_header()}<main><article><h1>Donner mon avis</h1>
<p class="intro">Un bug, une réponse fausse, une idée ? Dites-le en une minute : chaque avis est lu et aide à améliorer Teranga AI.</p>
<form class="partner-form" data-endpoint="/api/avis" data-success="Merci ! Votre avis est bien reçu.">
<fieldset><legend>C'est à propos de…</legend>{options}</fieldset>
<p><label>Votre message<br><textarea name="message" rows="5" required minlength="5" maxlength="1000" placeholder="Ex. Le micro ne marche pas sur mon téléphone Samsung"></textarea></label></p>
<p><label>Téléphone, WhatsApp ou e-mail (facultatif, pour vous répondre)<br><input name="contact" maxlength="80" autocomplete="email"></label></p>
<p hidden><label>Site web<input name="website" tabindex="-1" autocomplete="off"></label></p>
<p class="muted">N'écrivez pas d'informations sensibles (santé, papiers, coordonnées bancaires). Votre avis est gardé environ un an, uniquement pour améliorer Teranga AI (<a href="/confidentialite">confidentialité</a>).</p>
<p><button class="cta primary" type="submit">Envoyer mon avis</button></p>
<p role="status" aria-live="polite"></p>
</form><script src="{asset_url('partner-form.js')}" defer></script>
</article></main>{site_footer()}</body></html>"""


def register_avis_routes(app, store, rate_guard=None, require_json_post=None):
    @app.get("/avis")
    def avis_page():
        return Response(render_avis_page(), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    def avis_post():
        if rate_guard is not None:
            blocked = rate_guard("avis")
            if blocked is not None:
                return blocked
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Requête invalide."}), 400
        if body.get("website"):  # champ piège invisible : les robots le remplissent
            return jsonify({"ok": True})
        entry = {
            "kind": _clean(body.get("kind"), 20),
            "message": _clean(body.get("message"), 1000),
            "contact": _clean(body.get("contact"), 80),
            # Envoyé depuis l'appli Android (TWA) ou depuis le navigateur : indiqué par static/partner-form.js.
            "where": "Appli Android" if str(body.get("appli", "")) == "1" else "Site web",
        }
        if entry["kind"] not in AVIS_KINDS:
            return jsonify({"error": "Choisissez le sujet de votre avis."}), 400
        if len(entry["message"]) < 5:
            return jsonify({"error": "Écrivez votre avis en quelques mots."}), 400
        entry["kind_label"] = AVIS_KINDS[entry["kind"]]
        store.add(entry)
        # Ni message ni contact dans les journaux : seulement de quoi savoir qu'un avis est arrivé.
        app.logger.warning("avis kind=%s where=%s", entry["kind"], entry["where"])
        return jsonify({"ok": True})

    if require_json_post is not None:
        app.post("/api/avis")(require_json_post(avis_post))
