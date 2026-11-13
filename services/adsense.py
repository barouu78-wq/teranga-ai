"""Annonces Google AdSense, éteintes par défaut.

Allumées seulement si ADSENSE_CLIENT (« ca-pub- » suivi de 16 chiffres) et ADSENSE_SLOT (numéro du bloc
d'annonces créé dans AdSense) sont définis sur Render. Une seule annonce par page, marquée « Publicité », à la fin
des pages de guide (maquette validée par le propriétaire le 13 novembre 2026) ; jamais sur l'accueil (chat), le
planificateur, les urgences, la confidentialité, les pages partenaires, les réponses partagées ni les pages
privées.

Google ne prend en charge qu'une CSP « stricte » (nonce + 'strict-dynamic') : ses domaines changent. Cette CSP ne
s'applique qu'aux pages qui portent une annonce (services/http_headers.py, ads=True), et seuls nos propres
scripts y reçoivent le nonce : ceux du site (/static/), ceux d'une origine déjà autorisée (mesure d'audience), et
les scripts en ligne d'une page qui les autorisait déjà sans nonce ('unsafe-inline').
"""

from __future__ import annotations

import re
import secrets
from html import escape

_CLIENT = re.compile(r"ca-pub-\d{16}")
_SLOT = re.compile(r"\d{6,20}")
# Identifiant de Google dans ads.txt (registre IAB), le même pour tous les éditeurs AdSense.
GOOGLE_ADS_TXT_ID = "f08c47fec0942fa0"
SCRIPT_URL = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client="

# Pages sans annonce : l'outil (chat, planificateur), les urgences, les pages légales et commerciales, les réponses
# partagées (contenu des visiteurs), la page hors connexion.
EXCLUDED_PATHS = frozenset({
    "/", "/trip-planner", "/urgences", "/confidentialite", "/privacy", "/offres-partenaires", "/partenaires",
    "/partners", "/pour-les-entreprises", "/media-kit", "/presse", "/a-propos", "/partage", "/offline",
})
EXCLUDED_PREFIXES = ("/stats-", "/go/", "/api/")
_LABELS = {"fr": "Publicité", "en": "Advertisement", "es": "Publicidad", "de": "Anzeige", "it": "Pubblicità"}
_SCRIPT_TAG = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)


def adsense_config(client: object, slot: object) -> dict[str, str] | None:
    """Valide la configuration ; None (publicité éteinte) si l'identifiant du compte manque ou si un identifiant n'a
    pas le bon format. Le compte seul (sans bloc d'annonces) publie /ads.txt, dont Google a besoin pour vérifier le
    site avant d'accepter le compte ; aucune annonce ne s'affiche tant que ADSENSE_SLOT n'est pas défini."""
    client, slot = str(client or "").strip(), str(slot or "").strip()
    if not _CLIENT.fullmatch(client) or (slot and not _SLOT.fullmatch(slot)):
        return None
    return {"client": client, "slot": slot}


def ads_txt(config: dict[str, str] | None) -> str:
    """Ligne du fichier /ads.txt (vide si la publicité est éteinte)."""
    if not config:
        return ""
    return f"google.com, {config['client'].removeprefix('ca-')}, DIRECT, {GOOGLE_ADS_TXT_ID}\n"


def page_takes_ad(path: str) -> bool:
    return path not in EXCLUDED_PATHS and not path.startswith(EXCLUDED_PREFIXES)


def _add_nonce(body: str, nonce: str, inline_allowed: bool, trusted_origins: tuple[str, ...]) -> str:
    def replace(match):
        attributes = match.group(1)
        lowered = attributes.lower()
        if "nonce=" in lowered or "application/ld+json" in lowered:
            return match.group(0)
        src = re.search(r"""\bsrc\s*=\s*["']([^"']*)["']""", attributes, re.IGNORECASE)
        if src:
            url = src.group(1)
            ours = url.startswith("/static/") or any(url.startswith(origin + "/") for origin in trusted_origins if origin)
        else:
            ours = inline_allowed
        return f'<script{attributes} nonce="{nonce}">' if ours else match.group(0)

    return _SCRIPT_TAG.sub(replace, body)


def inject_adsense(response, config: dict[str, str] | None, path: str = "", nonce: str = "",
                   trusted_origins: tuple[str, ...] = ()):
    """Ajoute l'annonce en fin de page de guide. Renvoie (réponse, nonce) ; nonce vide si aucune annonce."""
    if not config or not config.get("slot") or not page_takes_ad(path) or response.direct_passthrough or response.is_streamed:
        return response, ""
    if response.status_code != 200 or response.mimetype != "text/html":
        return response, ""
    body = response.get_data(as_text=True)
    main_end = body.rfind("</main>")
    if "</head>" not in body.lower() or main_end == -1 or 'class="site-footer"' not in body[main_end:]:
        return response, ""
    # Une page déjà protégée par un nonce n'acceptait pas les scripts en ligne sans nonce : ça ne change pas.
    inline_allowed = not nonce
    nonce = nonce or secrets.token_urlsafe(16)
    lang = re.search(r'<html[^>]*\blang="([a-z]{2})', body)
    label = _LABELS.get(lang.group(1) if lang else "fr", _LABELS["fr"])
    client, slot = escape(config["client"]), escape(config["slot"])
    ad = (
        f'<aside class="ad-slot" aria-label="{label}"><p class="ad-label">{label}</p>'
        f'<ins class="adsbygoogle" data-ad-client="{client}" data-ad-slot="{slot}" data-ad-format="auto" '
        'data-full-width-responsive="true"></ins>'
        f'<script nonce="{nonce}">(window.adsbygoogle=window.adsbygoogle||[]).push({{}});</script></aside>'
    )
    body = _add_nonce(body, nonce, inline_allowed, trusted_origins)
    # Dans la carte de l'article quand elle ferme <main> (comme sur la maquette), sinon juste avant </main>.
    main_end = body.rfind("</main>")
    before = body[:main_end].rstrip()
    insert_at = len(before) - len("</article>") if before.endswith("</article>") else main_end
    body = body[:insert_at] + ad + body[insert_at:]
    loader = f'<script async src="{SCRIPT_URL}{client}" crossorigin="anonymous" nonce="{nonce}"></script>'
    head_end = body.lower().find("</head>")
    body = body[:head_end] + loader + body[head_end:]
    response.set_data(body)
    return response, nonce
