"""Politique de confidentialité, signalement des réponses de l'IA et
vérification de l'application Android (Google Play).
"""

from __future__ import annotations

import json
import os
import re
from html import escape

from flask import Response, current_app, jsonify, redirect, request

from services.site_layout import HEAD_ASSETS, site_footer, site_header

_UPDATED = "16 novembre 2026"

_PRIVACY = {
    "fr": {
        "title": "Politique de confidentialité",
        "intro": "Teranga AI est un assistant sur le Sénégal, utilisable sans compte. Cette page explique quelles données sont traitées, pourquoi, et combien de temps.",
        "sections": [
            ("Ce que vous écrivez ou dites", "Vos questions (et, si vous utilisez la voix, l'enregistrement de votre voix) sont envoyées à nos fournisseurs d'intelligence artificielle, Anthropic (Claude) et OpenAI, uniquement pour produire la réponse. Nous ne les utilisons pas pour vous identifier ni pour de la publicité. N'écrivez pas d'informations sensibles (santé, papiers d'identité, coordonnées bancaires)."),
            ("Fichiers envoyés au chat", "Si vous joignez une photo, un PDF ou un fichier Word à une question, il est envoyé à nos fournisseurs d'intelligence artificielle (Anthropic pour une photo ou un PDF ; Anthropic ou OpenAI pour le texte d'un fichier Word), uniquement pour produire la réponse. Teranga AI ne l'enregistre pas : ni sur ses serveurs, ni dans ses journaux, ni dans l'historique, où seul le nom du fichier s'affiche. N'envoyez pas de pièce d'identité, de carte bancaire ni de mot de passe."),
            ("Historique de conversation", "L'historique est conservé dans votre appareil (stockage du navigateur ou de l'application), pas sur nos serveurs. Le bouton « Nouveau » l'efface ; vider les données du navigateur ou désinstaller l'application aussi."),
            ("Cookies techniques", "Un identifiant aléatoire (sans nom ni e-mail) et un jeton de sécurité servent à limiter les abus et à protéger les formulaires. Ils ne servent pas à la publicité."),
            ("Adresse IP et journaux", "Votre adresse IP est utilisée temporairement pour limiter le nombre de requêtes et bloquer les abus. Les journaux techniques du serveur sont conservés peu de temps pour corriger les erreurs."),
            ("Services tiers", "Pour certaines réponses, le site interroge des services externes : recherche web via OpenAI, photos (Google, Wikimédia Commons, Wikipédia), météo (Open-Meteo, à partir des coordonnées du lieu demandé, jamais de votre position), taux de change (BCEAO). Seule la question ou le nom du lieu leur est transmis."),
            ("Mesure d'audience", "Si elle est activée, la mesure d'audience est respectueuse de la vie privée : sans cookie publicitaire ni profilage."),
            ("Liens de réservation et partenaires", "Certains liens « Réserver » mènent vers des sites partenaires (activités, hébergements) qui peuvent nous verser une commission, sans surcoût pour vous. Nous comptons les clics sur ces liens sans enregistrer d'information vous concernant. Les adresses partenaires sont toujours signalées comme telles."),
            ("Demandes de partenariat", "Si un professionnel remplit le formulaire de la page des offres partenaires, son nom, son activité, sa ville, son contact et son message sont conservés au plus 200 demandes et environ un an, uniquement pour le recontacter."),
            ("Statistiques anonymes des sujets", "Pour savoir quels sujets enrichir en priorité, le site tient des compteurs anonymes. Pour chaque question posée à l'assistant, il ajoute 1 au compteur du jour d'un ou plusieurs sujets prédéfinis (santé, transport, pêche…) et note si l'assistant disposait, sur ce sujet, d'informations de notre base ou d'une recherche web. Ces compteurs ne contiennent ni le texte de votre question, ni votre adresse IP, ni votre identifiant, ni une empreinte de l'un d'eux : ils ne permettent pas de savoir qui a posé quelle question. Ils sont supprimés automatiquement après environ 90 jours. Sur la page « Mon CV », le site compte aussi, chaque mois, les étapes du formulaire « Mon CV » (premier champ touché, envoi…), sans enregistrer ce que vous écrivez ni d'information vous concernant."),
            ("Signalements", "Si vous signalez une réponse, la question et la réponse concernées sont enregistrées dans nos journaux pour améliorer l'assistant."),
            ("Vos droits", "Il n'y a pas de compte : nous ne conservons pas de profil vous concernant. Pour toute question ou demande liée à vos données, contactez-nous{contact}."),
        ],
        "ads": ("Publicité", "Quand elle est activée, une annonce Google AdSense s'affiche en bas de certaines pages de guide, jamais dans le chat. Google et ses partenaires peuvent utiliser des cookies pour diffuser et mesurer ces annonces, y compris selon vos visites sur d'autres sites. En Europe, votre consentement est demandé d'abord, par un message de Google ; sans votre accord, Google ne montre que des annonces non personnalisées ou limitées. Pour en savoir plus et faire vos choix : {partner_sites}."),
        "google_ads": ("Mesure des annonces Google Ads", "Quand elle est activée, une balise Google Ads mesure ce que font sur le site les visiteurs arrivés par nos annonces (par exemple, une page consultée), pour savoir quelles annonces sont utiles. Elle dépose des cookies Google et n'est chargée qu'après votre accord, donné dans le bandeau « Cookies publicitaires » ; sans accord, rien n'est envoyé à Google. Vous pouvez changer d'avis à tout moment{ads_choice}."),
        "ads_choice": "Modifier mon choix",
        "partner_sites": "comment Google utilise les données des sites partenaires",
        "updated": "Dernière mise à jour",
    },
    "en": {
        "title": "Privacy policy",
        "intro": "Teranga AI is an assistant about Senegal that works without an account. This page explains what data is processed, why, and for how long.",
        "sections": [
            ("What you type or say", "Your questions (and, if you use voice, your voice recording) are sent to our AI providers, Anthropic (Claude) and OpenAI, only to produce the answer. We do not use them to identify you or for advertising. Do not share sensitive information (health, ID documents, bank details)."),
            ("Files you send", "If you attach a photo, a PDF or a Word file to a question, it is sent to our AI providers (Anthropic for a photo or a PDF; Anthropic or OpenAI for the text of a Word file) only to produce the answer. Teranga AI does not store it: not on its servers, not in its logs, not in the history, where only the file name is shown. Do not send ID documents, bank cards or passwords."),
            ("Conversation history", "History is stored on your device (browser or app storage), not on our servers. The “New” button clears it; so does clearing browser data or uninstalling the app."),
            ("Technical cookies", "A random identifier (no name or email) and a security token are used to limit abuse and protect forms. They are not used for advertising."),
            ("IP address and logs", "Your IP address is used temporarily to rate-limit requests and block abuse. Server logs are kept briefly to fix errors."),
            ("Third-party services", "For some answers the site queries external services: web search via OpenAI, photos (Google, Wikimedia Commons, Wikipedia), weather (Open-Meteo, using the coordinates of the place asked about, never your location), exchange rates (BCEAO). Only the question or place name is sent."),
            ("Analytics", "When enabled, analytics are privacy-friendly: no advertising cookies and no profiling."),
            ("Booking links and partners", "Some “Book” links lead to partner sites (activities, accommodation) that may pay us a commission at no extra cost to you. We count clicks on these links without recording any information about you. Partner listings are always labelled as such."),
            ("Partnership requests", "If a business fills in the form on the partner offers page, its name, activity, town, contact and message are kept (at most 200 requests, about one year) only to get back to it."),
            ("Anonymous topic statistics", "To know which topics to improve first, the site keeps anonymous counters. For each question asked to the assistant, it adds 1 to the day's counter of one or more predefined topics (health, transport, fishing…) and notes whether the assistant had information from our database or a web search on that topic. These counters contain neither the text of your question, nor your IP address, nor your identifier, nor a fingerprint of any of them: they cannot tell who asked what. They are deleted automatically after about 90 days."),
            ("Reports", "If you report an answer, the question and answer are recorded in our logs to improve the assistant."),
            ("Your rights", "There are no accounts: we keep no profile about you. For any question or request about your data, contact us{contact}."),
        ],
        "ads": ("Advertising", "When enabled, a Google AdSense ad appears at the bottom of some guide pages, never in the chat. Google and its partners may use cookies to serve and measure these ads, including based on your visits to other sites. In Europe your consent is asked first, through a Google message; without it, Google only shows non-personalised or limited ads. To learn more and make your choices: {partner_sites}."),
        "google_ads": ("Google Ads measurement", "When enabled, a Google Ads tag measures what visitors who arrived through our ads do on the site (for example, a page viewed), to learn which ads are useful. It sets Google cookies and is only loaded after your consent, given in the “Advertising cookies” banner; without consent, nothing is sent to Google. You can change your mind at any time{ads_choice}."),
        "ads_choice": "Change my choice",
        "partner_sites": "how Google uses information from sites that use its services",
        "updated": "Last updated",
    },
}


def render_privacy(lang: str, contact_email: str = "", ads: bool = False, google_ads: bool = False) -> str:
    copy = _PRIVACY[lang]
    entries = list(copy["sections"])
    if ads:
        # Annonces Google allumées (services/adsense.py) : juste après la mesure d'audience.
        entries.insert(7, copy["ads"])
    if google_ads:
        # Balise Google Ads allumée (services/google_ads_tag.py) : le bouton rouvre le bandeau de consentement.
        entries.insert(8 if ads else 7, copy["google_ads"])
    ads_choice = (f' : <button type="button" class="btn" data-ads-consent hidden>{escape(copy["ads_choice"])}</button>'
                  if google_ads else "")
    partner_sites = (f'<a href="https://policies.google.com/technologies/partner-sites" rel="noopener">'
                     f'{escape(copy["partner_sites"])}</a>')
    contact = f' : <a href="mailto:{escape(contact_email)}">{escape(contact_email)}</a>' if contact_email else (" via la fiche de l'application sur Google Play" if lang == "fr" else " via the app's Google Play listing")
    sections = "".join(
        f"<section><h2>{escape(title)}</h2><p>{escape(text).replace('{contact}', contact).replace('{partner_sites}', partner_sites).replace('{ads_choice}', ads_choice)}</p></section>"
        for title, text in entries
    )
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(copy['title'])} | Teranga AI</title><meta name="robots" content="index,follow">{HEAD_ASSETS}</head>
<body>{site_header(lang=lang)}<main><article><div class="kicker">Teranga AI</div><h1>{escape(copy['title'])}</h1>
<p class="intro">{escape(copy['intro'])}</p>{sections}<p><small>{escape(copy['updated'])} : {_UPDATED}</small></p></article></main>{site_footer(lang)}</body></html>"""


# Mentions légales (loi pour la confiance dans l'économie numérique, article 6). Éditeur et contact donnés par le
# propriétaire le 23 novembre 2026 ; adresse de l'hébergeur : conditions d'utilisation de Render (render.com/terms).
_MENTIONS = (
    ("Éditeur", 'Teranga AI est édité par Oumar Ba. Contact : <a href="mailto:terangaais@gmail.com">terangaais@gmail.com</a>.'),
    ("Directeur de la publication", "Oumar Ba."),
    ("Hébergeur", 'Render Services, Inc., 525 Brannan Street, Suite 300, San Francisco, CA 94107, États-Unis '
                  '(<a href="https://render.com" rel="noopener">render.com</a>), téléphone : +1 415 319 8186.'),
    ("Réponses de l'assistant", "Les réponses sont produites par une intelligence artificielle à partir de repères "
     "vérifiés et, parfois, d'une recherche web. Elles peuvent contenir des erreurs : vérifiez auprès des sources "
     "officielles avant toute démarche importante. En cas d'urgence, consultez la page "
     '<a href="/urgences">Urgences</a>.'),
    ("Liens partenaires", "Certains liens mènent vers des sites partenaires qui peuvent verser une commission à "
     "Teranga AI, sans surcoût pour vous. Ils sont toujours marqués « Lien partenaire »."),
    ("Données personnelles", 'Voir la <a href="/confidentialite">politique de confidentialité</a>.'),
    ("Signaler un contenu", 'Pour signaler un contenu inexact ou illicite : '
     '<a href="mailto:terangaais@gmail.com">terangaais@gmail.com</a>.'),
)
_MENTIONS_UPDATED = "23 novembre 2026"


def render_mentions() -> str:
    # Textes fixes écrits ici (aucune donnée de visiteur) : le HTML des liens est voulu.
    sections = "".join(f"<section><h2>{escape(title)}</h2><p>{text}</p></section>" for title, text in _MENTIONS)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mentions légales | Teranga AI</title><meta name="robots" content="index,follow">{HEAD_ASSETS}</head>
<body>{site_header(lang="fr")}<main><article><div class="kicker">Teranga AI</div><h1>Mentions légales</h1>
{sections}<p><small>Dernière mise à jour : {_MENTIONS_UPDATED}</small></p></article></main>{site_footer("fr")}</body></html>"""


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
        return Response(render_privacy("fr", os.getenv("CONTACT_EMAIL", "").strip(), ads=bool((current_app.config.get("ADSENSE") or {}).get("slot")), google_ads=bool(current_app.config.get("GOOGLE_ADS"))), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/privacy")
    def privacy_en():
        return Response(render_privacy("en", os.getenv("CONTACT_EMAIL", "").strip(), ads=bool((current_app.config.get("ADSENSE") or {}).get("slot")), google_ads=bool(current_app.config.get("GOOGLE_ADS"))), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/mentions-legales")
    def mentions_legales():
        return Response(render_mentions(), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/legal")
    def legal_redirect():
        return redirect("/mentions-legales", code=301)

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
