"""Branded error pages (404, 500) in the site's design."""

from __future__ import annotations

import difflib
import re
from html import escape
from urllib.parse import quote

from services.site_layout import HEAD_ASSETS, site_footer, site_header


def _page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="noindex"><title>{escape(title)} | Teranga AI</title>{HEAD_ASSETS}</head>'
        "<body>" + site_header() + f"<main><article>{body}</article></main>" + site_footer() + "</body></html>"
    )


def place_suggestions(path: str, places, limit: int = 3) -> list[dict]:
    """Fiches proches d'une URL /lieux/<id> mal tapée (« gore » → Gorée)."""
    if not path.startswith("/lieux/"):
        return []
    wanted = path[len("/lieux/"):].strip("/").lower()
    by_id = {str(p.get("id")): p for p in places or [] if p.get("id")}
    names = {str(p.get("name", "")).lower(): pid for pid, p in by_id.items()}
    ids = difflib.get_close_matches(wanted, list(by_id), n=limit, cutoff=0.6)
    for name in difflib.get_close_matches(wanted.replace("-", " "), list(names), n=limit, cutoff=0.6):
        if names[name] not in ids:
            ids.append(names[name])
    return [by_id[pid] for pid in ids[:limit]]


# Adresses que l'on tape naturellement (ou héritées d'autres sites) → la vraie page.
ALIASES = {
    "/index.html": "/", "/index.php": "/", "/accueil": "/", "/home": "/", "/fr": "/",
    "/en": "/en/senegal-travel-guide", "/es": "/es/senegal-travel-guide",
    "/de": "/de/senegal-travel-guide", "/it": "/it/senegal-travel-guide",
    "/planificateur": "/trip-planner", "/planner": "/trip-planner", "/itineraire": "/trip-planner",
    "/devenir-partenaire": "/offres-partenaires", "/partenariat": "/offres-partenaires",
    "/contact": "/offres-partenaires", "/offres": "/offres-partenaires",
    "/urgence": "/urgences", "/sos": "/urgences",
    "/fetes": "/calendrier-fetes-senegal", "/calendrier": "/calendrier-fetes-senegal",
    "/kit-media": "/media-kit", "/kitmedia": "/media-kit",
    "/regions": "/regions-senegal", "/places": "/lieux", "/explore": "/explorer",
    "/sitemap": "/sitemap.xml",
    "/apple-touch-icon.png": "/icon-192.png", "/apple-touch-icon-precomposed.png": "/icon-192.png",
}


def redirect_target(path: str, exists) -> str:
    """Page existante la plus proche d'une adresse introuvable, ou "".

    Barres « / » en trop, majuscules et alias connus. `exists(chemin)` dit si une
    route y répond. Le résultat commence toujours par un seul « / » : jamais de
    redirection vers un autre site (« //exemple.com »).
    """
    if "\\" in (path or ""):  # « /\exemple.com » : les navigateurs le lisent comme « //exemple.com »
        return ""
    clean = "/" + re.sub(r"/{2,}", "/", path or "").strip("/")
    for candidate in (clean, clean.lower()):
        candidate = ALIASES.get(candidate, candidate)
        if candidate != path and candidate.startswith("/") and not candidate.startswith("//") and exists(candidate):
            return candidate
    return ""


def render_not_found(path: str = "", places=None) -> str:
    suggestions = place_suggestions(path, places)
    hint = ""
    if suggestions:
        links = " · ".join(
            f'<a href="/lieux/{quote(str(p["id"]))}">{escape(str(p.get("name", "")))}</a>' for p in suggestions
        )
        hint = f"<p>Vouliez-vous dire : {links} ?</p>"
    return _page(
        "Page introuvable",
        '<div class="kicker">Erreur 404</div><h1>Page introuvable</h1>'
        "<p class=\"muted\">Cette adresse n’existe pas ou a changé.</p>" + hint +
        '<div class="actions"><a class="cta" href="/">Poser une question à Teranga AI</a>'
        '<a class="cta" href="/lieux">Voir les lieux du Sénégal</a>'
        '<a class="cta" href="/regions-senegal">Les 14 régions</a></div>',
    )


def render_server_error() -> str:
    return _page(
        "Erreur temporaire",
        '<div class="kicker">Erreur 500</div><h1>Un problème temporaire est survenu</h1>'
        '<p class="muted">Réessaie dans quelques instants. Si le problème continue, reviens à l’accueil.</p>'
        '<div class="actions"><a class="cta" href="/">Retour à l’accueil</a></div>',
    )
