"""Politique de confidentialité, signalement des réponses de l'IA et
vérification de l'application Android (Google Play).
"""

from __future__ import annotations

import json
import os
import re
from html import escape

from flask import Response, jsonify, request

from services.site_layout import HEAD_ASSETS, site_footer, site_header

_UPDATED = "5 octobre 2026"

_PRIVACY = {
    "fr": {
        "title": "Politique de confidentialité",
        "intro": "Teranga AI est un assistant sur le Sénégal, utilisable sans compte. Cette page explique quelles données sont traitées, pourquoi, et combien de temps.",
        "sections": [
            ("Ce que vous écrivez ou dites", "Vos questions (et, si vous utilisez la voix, l'enregistrement de votre voix) sont envoyées à notre fournisseur d'intelligence artificielle, OpenAI, uniquement pour produire la réponse. Nous ne les utilisons pas pour vous identifier ni pour de la publicité. N'écrivez pas d'informations sensibles (santé, papiers d'identité, coordonnées bancaires)."),
            ("Historique de conversation", "L'historique est conservé dans votre appareil (stockage du navigateur ou de l'application), pas sur nos serveurs. Le bouton « Nouveau » l'efface ; vider les données du navigateur ou désinstaller l'application aussi."),
            ("Cookies techniques", "Un identifiant aléatoire (sans nom ni e-mail) et un jeton de sécurité servent à limiter les abus et à protéger les formulaires. Ils ne servent pas à la publicité."),
            ("Adresse IP et journaux", "Votre adresse IP est utilisée temporairement pour limiter le nombre de requêtes et bloquer les abus. Les journaux techniques du serveur sont conservés peu de temps pour corriger les erreurs."),
            ("Services tiers", "Pour certaines réponses, le site interroge des services externes : recherche web via OpenAI, photos (Google, Wikimédia Commons, Wikipédia), météo (Open-Meteo, à partir des coordonnées du lieu demandé, jamais de votre position), taux de change (BCEAO). Seule la question ou le nom du lieu leur est transmis."),
            ("Mesure d'audience", "Si elle est activée, la mesure d'audience est respectueuse de la vie privée : sans cookie publicitaire ni profilage."),
            ("Liens de réservation et partenaires", "Certains liens « Réserver » mènent vers des sites partenaires (activités, hébergements) qui peuvent nous verser une commission, sans surcoût pour vous. Nous comptons les clics sur ces liens sans enregistrer d'information vous concernant. Les adresses partenaires sont toujours signalées comme telles."),
            ("Demandes de partenariat", "Si un professionnel remplit le formulaire de la page des offres partenaires, son nom, son activité, sa ville, son contact et son message sont conservés au plus 200 demandes et environ un an, uniquement pour le recontacter."),
            ("Signalements", "Si vous signalez une réponse, la question et la réponse concernées sont enregistrées dans nos journaux pour améliorer l'assistant."),
            ("Vos droits", "Il n'y a pas de compte : nous ne conservons pas de profil vous concernant. Pour toute question ou demande liée à vos données, contactez-nous{contact}."),
        ],
        "updated": "Dernière mise à jour",
    },
    "en": {
        "title": "Privacy policy",
        "intro": "Teranga AI is an assistant about Senegal that works without an account. This page explains what data is processed, why, and for how long.",
        "sections": [
            ("What you type or say", "Your questions (and, if you use voice, your voice recording) are sent to our AI provider, OpenAI, only to produce the answer. We do not use them to identify you or for advertising. Do not share sensitive information (health, ID documents, bank details)."),
            ("Conversation history", "History is stored on your device (browser or app storage), not on our servers. The “New” button clears it; so does clearing browser data or uninstalling the app."),
            ("Technical cookies", "A random identifier (no name or email) and a security token are used to limit abuse and protect forms. They are not used for advertising."),
            ("IP address and logs", "Your IP address is used temporarily to rate-limit requests and block abuse. Server logs are kept briefly to fix errors."),
            ("Third-party services", "For some answers the site queries external services: web search via OpenAI, photos (Google, Wikimedia Commons, Wikipedia), weather (Open-Meteo, using the coordinates of the place asked about, never your location), exchange rates (BCEAO). Only the question or place name is sent."),
            ("Analytics", "When enabled, analytics are privacy-friendly: no advertising cookies and no profiling."),
            ("Booking links and partners", "Some “Book” links lead to partner sites (activities, accommodation) that may pay us a commission at no extra cost to you. We count clicks on these links without recording any information about you. Partner listings are always labelled as such."),
            ("Partnership requests", "If a business fills in the form on the partner offers page, its name, activity, town, contact and message are kept (at most 200 requests, about one year) only to get back to it."),
            ("Reports", "If you report an answer, the question and answer are recorded in our logs to improve the assistant."),
            ("Your rights", "There are no accounts: we keep no profile about you. For any question or request about your data, contact us{contact}."),
        ],
        "updated": "Last updated",
    },
}


def render_privacy(lang: str, contact_email: str = "") -> str:
    copy = _PRIVACY[lang]
    contact = f' : <a href="mailto:{escape(contact_email)}">{escape(contact_email)}</a>' if contact_email else (" via la fiche de l'application sur Google Play" if lang == "fr" else " via the app's Google Play listing")
    sections = "".join(
        f"<section><h2>{escape(title)}</h2><p>{escape(text).replace('{contact}', contact)}</p></section>"
        for title, text in copy["sections"]
    )
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(copy['title'])} | Teranga AI</title><meta name="robots" content="index,follow">{HEAD_ASSETS}</head>
<body>{site_header(lang=lang)}<main><article><div class="kicker">Teranga AI</div><h1>{escape(copy['title'])}</h1>
<p class="intro">{escape(copy['intro'])}</p>{sections}<p><small>{escape(copy['updated'])} : {_UPDATED}</small></p></article></main>{site_footer(lang)}</body></html>"""


# Application Android (paquet PWABuilder). Ces valeurs sont publiques : le
# fichier assetlinks.json est fait pour être lu par tous. ANDROID_CERT_SHA256
# (variable d'environnement) peut AJOUTER des empreintes, jamais en retirer.
ANDROID_APP_PACKAGE = "fr.teranga_ai"
ANDROID_CERT_SHA256 = (
    # Clé de signature Google Play (Play App Signing) : celle des installations depuis le Play Store.
    "01:D3:EB:74:F8:1B:EC:B2:AB:1A:BD:89:BC:34:E9:1F:0A:4B:72:5C:E7:31:E7:6F:98:2E:BF:EA:0B:4D:7F:59",
    # Clé d'importation (signing.keystore PWABuilder) : APK installé à la main pour les tests.
    "C9:09:F5:A8:01:5A:EE:64:BC:71:51:95:78:79:95:67:D8:83:2B:9E:69:9A:3F:70:26:01:BC:CD:99:F1:5B:BB",
)


REPORT_REASONS = {"inappropriate", "wrong", "offensive", "dangerous", "other"}
_SHA256_RE = re.compile(r"^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$")


def asset_links(package: str, fingerprints: str) -> list:
    prints = []
    for item in str(fingerprints or "").split(","):
        value = item.strip().upper().removeprefix("SHA256:").strip()
        # Une empreinte mal copiée ferait échouer la vérification Android sans erreur visible.
        if _SHA256_RE.match(value) and value not in prints:
            prints.append(value)
    if not package or not prints:
        return []
    return [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {"namespace": "android_app", "package_name": package, "sha256_cert_fingerprints": prints},
    }]


def register_legal_routes(app, deps):
    require_json_post = deps["require_json_post"]
    rate_guard = deps.get("rate_guard")
    sanitize = deps["sanitize_text"]

    @app.get("/confidentialite")
    def privacy_fr():
        return Response(render_privacy("fr", os.getenv("CONTACT_EMAIL", "").strip()), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/privacy")
    def privacy_en():
        return Response(render_privacy("en", os.getenv("CONTACT_EMAIL", "").strip()), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/.well-known/assetlinks.json")
    def android_asset_links():
        # Prouve à Android que l'application Google Play appartient à ce site
        # (application « TWA » qui affiche teranga-ai.fr en plein écran).
        links = asset_links(
            os.getenv("ANDROID_APP_PACKAGE", "").strip() or ANDROID_APP_PACKAGE,
            ",".join(ANDROID_CERT_SHA256) + "," + os.getenv("ANDROID_CERT_SHA256", ""),
        )
        if not links:
            return Response("[]", status=404, mimetype="application/json")
        return Response(json.dumps(links), mimetype="application/json", headers={"Cache-Control": "public, max-age=3600"})

    @app.post("/api/report")
    @require_json_post
    def report_answer():
        if rate_guard is not None:
            blocked = rate_guard("report")
            if blocked is not None:
                return blocked
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Requête invalide."}), 400
        reason = str(body.get("reason") or "inappropriate")
        if reason not in REPORT_REASONS:
            reason = "other"  # pas de texte libre dans les journaux
        question = sanitize(body.get("question", ""), max_len=500)
        reply = sanitize(body.get("reply", ""), max_len=1500)
        if not reply:
            return jsonify({"error": "Réponse manquante."}), 400
        app.logger.warning("ai-report reason=%s question=%r reply=%r", reason, question, reply)
        return jsonify({"ok": True})
