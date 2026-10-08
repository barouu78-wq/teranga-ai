"""Revenus : redirection des liens affiliés (/go) et page des offres partenaires."""

from __future__ import annotations

import hmac
import json
import os
import re
from html import escape
from urllib.parse import quote

from flask import Response, abort, jsonify, redirect, request

from services.click_stats import ClickStats
from services.partner_requests import KINDS, PartnerRequests

from services.monetization import affiliate_config, affiliate_target, clean_query
from services.site_layout import HEAD_ASSETS, asset_url, site_footer, site_header, social_meta

OFFERS = (
    (
        "Adresse partenaire",
        "Votre hôtel, restaurant, agence ou service de guide apparaît, avec la mention « Partenaire », "
        "sur les fiches des lieux de votre ville et dans les recommandations de l'assistant quand un "
        "visiteur cherche ce que vous proposez.",
    ),
    (
        "Bouton Teranga AI sur votre site",
        "Une ligne de code ajoute un bouton « Une question sur le Sénégal ? » à votre site : vos clients "
        "trouvent transports, météo, quartiers et visites sans quitter votre page. Version de base gratuite, "
        "version à vos couleurs avec vos adresses mises en avant sur demande.",
    ),
    (
        "Guide thématique sponsorisé",
        "Un guide dédié (gastronomie, plages, excursions, artisanat…) qui présente votre activité aux côtés "
        "de contenus utiles et vérifiés, clairement indiqué comme partenariat.",
    ),
)


def _contact_links(subject: str) -> str:
    links = []
    email = os.getenv("CONTACT_EMAIL", "").strip()
    if re.match(r"^[^@\s<>\"]+@[^@\s<>\"]+\.[a-z]{2,}$", email, re.I):
        links.append(f'<a class="cta primary" href="mailto:{escape(email)}?subject={quote(subject)}">Écrire à l\'équipe</a>')
    whatsapp = re.sub(r"\D", "", os.getenv("PARTNER_WHATSAPP", ""))
    if 8 <= len(whatsapp) <= 15:
        text = quote("Bonjour, je souhaite devenir partenaire de Teranga AI.")
        links.append(f'<a class="cta" href="https://wa.me/{whatsapp}?text={text}" target="_blank" rel="noopener">WhatsApp</a>')
    links.append('<a class="cta" href="/pour-les-entreprises">Le bouton pour votre site</a>')
    links.append('<a class="cta" href="/media-kit">Kit média</a>')
    return '<div class="actions">' + "".join(links) + "</div>"


def _contact_title() -> str:
    """« Nous contacter » seulement si un e-mail ou un WhatsApp est configuré ; sinon, les ressources utiles."""
    has_contact = bool(os.getenv("CONTACT_EMAIL", "").strip()) or len(re.sub(r"\D", "", os.getenv("PARTNER_WHATSAPP", ""))) >= 8
    return "Nous contacter" if has_contact else "Pour aller plus loin"


def _request_form() -> str:
    options = "".join(f'<option value="{escape(key)}">{escape(label)}</option>' for key, label in KINDS.items())
    return f"""<form id="partner-form" class="partner-form">
<p><label>Nom de l'établissement ou de l'activité<br><input name="name" required maxlength="80" autocomplete="organization"></label></p>
<p><label>Type d'activité<br><select name="kind" required>{options}</select></label></p>
<p><label>Ville ou lieu<br><input name="city" required maxlength="60" placeholder="Saint-Louis, Saly, Cap Skirring…"></label></p>
<p><label>Téléphone, WhatsApp ou e-mail<br><input name="contact" required maxlength="80" autocomplete="tel"></label></p>
<p><label>Votre message (facultatif)<br><textarea name="message" rows="3" maxlength="600"></textarea></label></p>
<p hidden><label>Site web<input name="website" tabindex="-1" autocomplete="off"></label></p>
<p class="muted">Ces informations servent uniquement à vous recontacter au sujet d'un partenariat.</p>
<p><button class="cta primary" type="submit">Envoyer la demande</button></p>
<p id="partner-form-status" role="status" aria-live="polite"></p>
</form><script src="{asset_url('partner-form.js')}" defer></script>"""


OFFERS_TITLE = "Devenir partenaire : hôtels, guides, restaurants | Teranga AI"
OFFERS_DESCRIPTION = "Faites connaître votre hôtel, restaurant, agence ou service de guide auprès des voyageurs qui préparent leur séjour au Sénégal avec Teranga AI."


def render_offers_page(site_url: str = "https://teranga-ai.fr") -> str:
    cards = "".join(
        f'<div class="card"><h3>{escape(title)}</h3><p>{escape(text)}</p></div>' for title, text in OFFERS
    )
    url = site_url.rstrip("/") + "/offres-partenaires"
    ld = json.dumps(
        {"@context": "https://schema.org", "@type": "WebPage", "name": OFFERS_TITLE, "url": url, "inLanguage": "fr",
         "description": OFFERS_DESCRIPTION, "isPartOf": {"@type": "WebSite", "name": "Teranga AI", "url": site_url.rstrip("/") + "/"}},
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(OFFERS_TITLE)}</title>
<meta name="description" content="{escape(OFFERS_DESCRIPTION)}">
<link rel="canonical" href="{escape(url)}">
<meta name="robots" content="index,follow">{social_meta(OFFERS_TITLE, OFFERS_DESCRIPTION, url, site_url)}{HEAD_ASSETS}
<script type="application/ld+json">{ld}</script></head>
<body>{site_header()}<main><article><div class="kicker">Professionnels du tourisme</div>
<h1>Devenir partenaire de Teranga AI</h1>
<p class="intro">Chaque jour, des voyageurs et des membres de la diaspora demandent à Teranga AI où dormir, quoi visiter et qui contacter au Sénégal. Soyez la réponse.</p>
<section><h2>Nos offres</h2><div class="grid">{cards}</div></section>
<section><h2>Nos engagements</h2><p>Les partenaires sont toujours signalés comme tels : l'assistant ne présente jamais une adresse payante comme un avis neutre. Nous ne publions ni faux avis ni faux chiffres d'audience. Tarifs de lancement sur demande, adaptés à la taille de votre activité.</p></section>
<section id="demande"><h2>Demander un partenariat</h2><p>Présentez votre activité en une minute : nous vous recontactons par téléphone, WhatsApp ou e-mail.</p>{_request_form()}</section>
<section><h2>{_contact_title()}</h2>{_contact_links("Partenariat Teranga AI")}</section>
</article></main>{site_footer()}</body></html>"""


KIND_LABELS = {"hotels": "🏨 Hôtels (Booking)", "activites": "🎟️ Activités (GetYourGuide)", "taxi": "🚕 Taxi"}


def _stats_token() -> str:
    """Mot de passe de la page des statistiques (STATS_TOKEN sur Render, 16 caractères minimum)."""
    token = os.getenv("STATS_TOKEN", "").strip()
    return token if len(token) >= 16 else ""


def _requests_section(requests: list[dict]) -> str:
    if not requests:
        return '<section><h2>Demandes de partenariat</h2><p class="muted">Aucune demande pour le moment.</p></section>'
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(item.get(key, '')))}</td>" for key in ("at", "name", "kind_label", "city", "contact", "message")) + "</tr>"
        for item in requests
    )
    return ("<section><h2>Demandes de partenariat</h2><table><thead><tr><th>Date</th><th>Nom</th><th>Activité</th>"
            f"<th>Ville</th><th>Contact</th><th>Message</th></tr></thead><tbody>{rows}</tbody></table></section>")


def render_stats_page(summary: list[dict] | None, error: str = "", requests: list[dict] | None = None) -> str:
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
            + _requests_section(requests or [])
            + "".join(blocks)
        )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Statistiques partenaires | Teranga AI</title><meta name="robots" content="noindex,nofollow">{HEAD_ASSETS}</head>
<body>{site_header()}<main><article>{body}</article></main>{site_footer()}</body></html>"""


def _clean(value, limit: int) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or "")).strip()
    return re.sub(r"\s{2,}", " ", text)[:limit]


def register_monetization_routes(app, redis_client=None, rate_guard=None, known_sources=(), require_json_post=None, site_url="https://teranga-ai.fr"):
    stats = ClickStats(redis_client, app.logger)
    partner_requests = PartnerRequests(redis_client, app.logger)
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
        return Response(render_stats_page(stats.summary(), requests=partner_requests.recent()), mimetype="text/html", headers=headers)

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
        return Response(render_offers_page(site_url), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    def partner_request():
        if rate_guard is not None:
            blocked = rate_guard("partner_request")
            if blocked is not None:
                return blocked
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Requête invalide."}), 400
        if body.get("website"):  # champ piège invisible : les robots le remplissent
            return jsonify({"ok": True})
        entry = {
            "name": _clean(body.get("name"), 80),
            "kind": _clean(body.get("kind"), 20),
            "city": _clean(body.get("city"), 60),
            "contact": _clean(body.get("contact"), 80),
            "message": _clean(body.get("message"), 600),
        }
        if entry["kind"] not in KINDS:
            return jsonify({"error": "Choisissez un type d'activité."}), 400
        if not entry["name"] or not entry["city"] or len(re.sub(r"\D", "", entry["contact"])) < 8 and "@" not in entry["contact"]:
            return jsonify({"error": "Indiquez le nom, la ville et un téléphone ou un e-mail valide."}), 400
        entry["kind_label"] = KINDS[entry["kind"]]
        partner_requests.add(entry)
        # Pas de coordonnées dans les journaux : seulement de quoi savoir qu'une demande est arrivée.
        app.logger.warning("partner-request kind=%s city=%r", entry["kind"], entry["city"])
        return jsonify({"ok": True})

    if require_json_post is not None:
        app.post("/api/partner-request")(require_json_post(partner_request))
