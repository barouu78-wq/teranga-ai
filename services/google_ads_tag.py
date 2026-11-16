"""Balise Google Ads (mesure des conversions des campagnes), éteinte par défaut.

Allumée seulement si GOOGLE_ADS_TAG_ID (« AW- » suivi de chiffres) est défini sur Render. Décision du propriétaire
du 16 novembre 2026 : mesurer ce que deviennent les visiteurs venus des annonces Google Ads.

Le site n'injecte que son propre contrôleur (/static/google-ads-consent.js). Aucun script Google n'est chargé avant un
« Accepter » explicite du visiteur (CNIL : les cookies publicitaires demandent un accord préalable, « Refuser » aussi
visible que « Accepter »). Après accord, le mode consentement v2 de Google est déclaré (refus par défaut, puis accord).
Les origines Google ne sont ajoutées à la CSP que si la balise est allumée, et jamais sur les pages privées.
"""

from __future__ import annotations

import re
from html import escape

from services.analytics import PRIVATE_PREFIXES

_TAG_ID = re.compile(r"AW-\d{6,15}")
# Origines dont gtag.js a besoin (script et envois) d'après la documentation CSP de Google Ads.
GOOGLE_ADS_ORIGINS = (
    "https://www.googletagmanager.com",
    "https://www.googleadservices.com",
    "https://googleads.g.doubleclick.net",
    "https://www.google.com",
)


def google_ads_config(tag_id: object) -> dict[str, object] | None:
    """Valide l'identifiant ; None (balise éteinte) s'il manque ou n'a pas le bon format."""
    value = str(tag_id or "").strip().upper()
    if not _TAG_ID.fullmatch(value):
        return None
    return {"tag_id": value, "origins": GOOGLE_ADS_ORIGINS}


def google_ads_tag(config: dict[str, object] | None) -> str:
    if not config:
        return ""
    return f'<script src="/static/google-ads-consent.js" defer data-tag-id="{escape(str(config["tag_id"]), quote=True)}"></script>'


def inject_google_ads(response, config: dict[str, object] | None, path: str = ""):
    """Insère le contrôleur de consentement avant </head> d'une page HTML (jamais sur les pages privées)."""
    if not config or response.direct_passthrough or response.is_streamed or path.startswith(PRIVATE_PREFIXES):
        return response
    if response.status_code != 200 or response.mimetype != "text/html":
        return response
    body = response.get_data(as_text=True)
    index = body.lower().rfind("</head>")
    if index < 0:
        return response
    response.set_data(body[:index] + google_ads_tag(config) + body[index:])
    return response
