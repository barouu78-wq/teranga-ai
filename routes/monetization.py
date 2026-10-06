"""Revenus : redirection des liens affiliés (/go) et page des offres partenaires."""

from __future__ import annotations

import hmac
import os
import re
from html import escape
from urllib.parse import quote

from flask import Response, abort, redirect, request

from services.click_stats import ClickStats

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


KIND_LABELS = {"hotels": "🏨 Hôtels (Booking)", "activites": "🎟️ Activités (GetYourGuide)", "taxi": "🚕 Taxi"}


def _stats_token() -> str:
    """Mot de passe de la page des statistiques (STATS_TOKEN sur Render, 16 caractères minimum)."""
    token = os.getenv("STATS_TOKEN", "").strip()
    return token if len(token) >= 16 else ""


def render_stats_page(summary: list[dict] | None, error: str = "") -> str:
    if summary is None:
        body = f"""<h1>Statistiques partenaires</h1>
<p class="intro">Clics des visiteurs vers les partenaires, par mois. Page privée.</p>
{f'<p class="muted">{escape(error)}</p>' if error else ''}
<form method="post"><label>Mot de passe <input type="password" name="cle" autocomplete="current-password" required></label>
<button class="cta primary" type="submit">Voir les chiffres</button></form>"""
    else:
        blocks = []
        for month in summary:
            kinds = " · ".join(f"{escape(KIND_LABELS.get(k, k))} : <strong>{n}</strong>" for k, n in sorted(month["by_kind"].items()))
            rows = "".join(
                f"<tr><td>{escape(KIND_LABELS.get(kind, kind))}</td><td>{escape(source)}</td><td>{n}</td></tr>"
                for kind, source, n in month["rows"][:50]
            )
            table = (
                f"<table><thead><tr><th>Lien</th><th>Page d'origine</th><th>Clics</th></tr></thead><tbody>{rows}</tbody></table>"
                if rows else '<p class="muted">Aucun clic ce mois-ci.</p>'
            )
            blocks.append(f"<section><h2>{escape(month['month'])} — {month['total']} clic(s)</h2><p>{kinds}</p>{table}</section>")
        body = (
            "<h1>Statistiques partenaires</h1>"
            '<p class="intro">Chiffres réels, sans donnée personnelle : à montrer aux partenaires pour négocier.</p>'
            + "".join(blocks)
        )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Statistiques partenaires | Teranga AI</title><meta name="robots" content="noindex,nofollow">{HEAD_ASSETS}</head>
<body>{site_header()}<main><article>{body}</article></main>{site_footer()}</body></html>"""


def register_monetization_routes(app, redis_client=None, rate_guard=None, known_sources=()):
    stats = ClickStats(redis_client, app.logger)
    # Seules les pages d'origine connues (fiches de lieux) sont comptées à part :
    # une valeur inventée ne crée pas de nouvelle ligne dans les statistiques.
    sources = {str(item) for item in known_sources if item}

    @app.route("/stats-partenaires", methods=["GET", "POST"])
    def partner_stats():
        token = _stats_token()
        if not token:
            abort(404)  # page désactivée tant que STATS_TOKEN n'est pas défini
        headers = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
        if request.method == "GET":
            return Response(render_stats_page(None), mimetype="text/html", headers=headers)
        if rate_guard is not None and rate_guard("stats_login") is not None:
            return Response(render_stats_page(None, "Trop d'essais. Réessaie dans quelques minutes."),
                            status=429, mimetype="text/html", headers=headers)
        given = str(request.form.get("cle", ""))
        if not hmac.compare_digest(given.encode("utf-8"), token.encode("utf-8")):
            app.logger.warning("stats-partenaires: mot de passe refusé")
            return Response(render_stats_page(None, "Mot de passe incorrect."), status=403, mimetype="text/html", headers=headers)
        return Response(render_stats_page(stats.summary()), mimetype="text/html", headers=headers)

    @app.get("/go/<kind>")
    def affiliate_redirect(kind):
        query = clean_query(request.args.get("q", ""))
        target = affiliate_target(kind, query, affiliate_config())
        if not target:
            abort(404)
        source = re.sub(r"[^a-z0-9-]", "", str(request.args.get("from", "")).lower())[:60]
        # Comptage des clics, sans donnée personnelle (ni IP ni identifiant).
        app.logger.info("affiliate-click kind=%s from=%s q=%r", kind, source or "-", query)
        # Compté au plus quelques fois par visiteur et par minute : les chiffres
        # montrés aux partenaires ne peuvent pas être gonflés par un script.
        if rate_guard is None or rate_guard("affiliate_count") is None:
            stats.record(kind, source if source in sources else "-")
        response = redirect(target, code=302)
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/offres-partenaires")
    def partner_offers():
        return Response(render_offers_page(), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})
