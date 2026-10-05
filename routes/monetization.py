"""Revenus : redirection des liens affiliés (/go) et page des offres partenaires."""

from __future__ import annotations

import os
import re
from html import escape
from urllib.parse import quote

from flask import Response, abort, redirect, request

from services.monetization import affiliate_config, affiliate_target, clean_query
from services.site_layout import HEAD_ASSETS, site_footer, site_header

OFFERS = (
    (
        "📍 Adresse partenaire",
        "Votre hôtel, restaurant, agence ou service de guide apparaît, avec la mention « Partenaire », "
        "sur les fiches des lieux de votre ville et dans les recommandations de l'assistant quand un "
        "visiteur cherche ce que vous proposez.",
    ),
    (
        "💬 Bouton Teranga AI sur votre site",
        "Une ligne de code ajoute un bouton « Une question sur le Sénégal ? » à votre site : vos clients "
        "trouvent transports, météo, quartiers et visites sans quitter votre page. Version de base gratuite, "
        "version à vos couleurs avec vos adresses mises en avant sur demande.",
    ),
    (
        "🧭 Guide thématique sponsorisé",
        "Un guide dédié (gastronomie, plages, excursions, artisanat…) qui présente votre activité aux côtés "
        "de contenus utiles et vérifiés, clairement indiqué comme partenariat.",
    ),
)


def _contact_links(subject: str) -> str:
    links = []
    email = os.getenv("CONTACT_EMAIL", "").strip()
    if re.match(r"^[^@\s<>\"]+@[^@\s<>\"]+\.[a-z]{2,}$", email, re.I):
        links.append(f'<a class="cta primary" href="mailto:{escape(email)}?subject={quote(subject)}">✉️ Écrire à l\'équipe</a>')
    whatsapp = re.sub(r"\D", "", os.getenv("PARTNER_WHATSAPP", ""))
    if 8 <= len(whatsapp) <= 15:
        text = quote("Bonjour, je souhaite devenir partenaire de Teranga AI.")
        links.append(f'<a class="cta" href="https://wa.me/{whatsapp}?text={text}" target="_blank" rel="noopener">💬 WhatsApp</a>')
    links.append('<a class="cta" href="/pour-les-entreprises">Le bouton pour votre site</a>')
    return '<div class="actions">' + "".join(links) + "</div>"


def render_offers_page() -> str:
    cards = "".join(
        f'<div class="card"><h3>{escape(title)}</h3><p>{escape(text)}</p></div>' for title, text in OFFERS
    )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Devenir partenaire : hôtels, guides, restaurants | Teranga AI</title>
<meta name="description" content="Faites connaître votre hôtel, restaurant, agence ou service de guide auprès des voyageurs qui préparent leur séjour au Sénégal avec Teranga AI.">
<meta name="robots" content="index,follow">{HEAD_ASSETS}</head>
<body>{site_header()}<main><article><div class="kicker">Professionnels du tourisme</div>
<h1>Devenir partenaire de Teranga AI</h1>
<p class="intro">Chaque jour, des voyageurs et des membres de la diaspora demandent à Teranga AI où dormir, quoi visiter et qui contacter au Sénégal. Soyez la réponse.</p>
<section><h2>Nos offres</h2><div class="grid">{cards}</div></section>
<section><h2>Nos engagements</h2><p>Les partenaires sont toujours signalés comme tels : l'assistant ne présente jamais une adresse payante comme un avis neutre. Nous ne publions ni faux avis ni faux chiffres d'audience. Tarifs de lancement sur demande, adaptés à la taille de votre activité.</p></section>
<section><h2>Nous contacter</h2><p>Présentez votre activité, votre ville et ce que vous proposez aux visiteurs.</p>{_contact_links("Partenariat Teranga AI")}</section>
</article></main>{site_footer()}</body></html>"""


def register_monetization_routes(app):
    @app.get("/go/<kind>")
    def affiliate_redirect(kind):
        query = clean_query(request.args.get("q", ""))
        target = affiliate_target(kind, query, affiliate_config())
        if not target:
            abort(404)
        source = re.sub(r"[^a-z0-9-]", "", str(request.args.get("from", "")).lower())[:60]
        # Comptage des clics, sans donnée personnelle (ni IP ni identifiant).
        app.logger.info("affiliate-click kind=%s from=%s q=%r", kind, source or "-", query)
        response = redirect(target, code=302)
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/offres-partenaires")
    def partner_offers():
        return Response(render_offers_page(), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})
