"""Shared header/footer for secondary pages (same design as the home page)."""

from __future__ import annotations

from html import escape

_STATIC_DIR = None
_VERSIONS: dict[str, tuple[int, str]] = {}


def asset_version(name: str) -> str:
    """Empreinte courte du fichier static/<name>, recalculée seulement s'il change."""
    import hashlib
    from pathlib import Path

    global _STATIC_DIR
    if _STATIC_DIR is None:
        _STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
    path = _STATIC_DIR / name
    try:
        mtime = path.stat().st_mtime_ns
        cached = _VERSIONS.get(name)
        if cached and cached[0] == mtime:
            return cached[1]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    except OSError:
        return ""
    _VERSIONS[name] = (mtime, digest)
    return digest


def asset_url(name: str) -> str:
    """/static/<name>?v=<empreinte> : chaque déploiement change l'URL des fichiers
    modifiés, le navigateur et le service worker chargent donc la bonne version."""
    digest = asset_version(name)
    return f"/static/{name}?v={digest}" if digest else f"/static/{name}"


HEAD_ASSETS = f'<link rel="stylesheet" href="{asset_url("site.css")}"><script src="{asset_url("theme.js")}"></script>'

def social_meta(title: str, description: str, url: str, site_url: str, og_type: str = "website") -> str:
    """Balises Open Graph et Twitter : aperçu des liens partagés (WhatsApp, Facebook, X…)."""
    t, d, u = escape(title), escape(description), escape(url)
    return (
        f'<meta property="og:site_name" content="Teranga AI"><meta property="og:type" content="{escape(og_type)}">'
        f'<meta property="og:title" content="{t}"><meta property="og:description" content="{d}">'
        f'<meta property="og:url" content="{u}"><meta property="og:image" content="{escape(site_url.rstrip("/"))}/og.png">'
        '<meta name="twitter:card" content="summary_large_image">'
    )


_MARK = (
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 21V9M5 13c3-.8 4.2-4 7-4s4 3.2 7 4" '
    'stroke="#f6e7c2" stroke-width="1.8" stroke-linecap="round"/><circle cx="17" cy="5" r="1.8" fill="#e2b34a"/></svg>'
)

_NAV = {
    "fr": (("/explorer", "Explorer"), ("/lieux", "Lieux"), ("/trip-planner?lang=fr", "Planifier"), ("/regions-senegal", "Régions")),
    "en": (("/explorer", "Explore"), ("/lieux", "Places"), ("/trip-planner?lang=en", "Plan a trip"), ("/en/senegal-travel-guide", "Guide")),
}
_CTA = {"fr": "Poser une question", "en": "Ask Teranga AI"}
_FOOTER = {
    "fr": (("/a-propos", "À propos"), ("/pour-les-entreprises", "Entreprises"), ("/offres-partenaires", "Devenir partenaire"), ("/calendrier-fetes-senegal", "Fêtes"), ("/urgences", "Urgences"), ("/presse", "Presse"), ("/media-kit", "Kit média"), ("/confidentialite", "Confidentialité")),
    "en": (("/a-propos", "About"), ("/pour-les-entreprises", "Business"), ("/offres-partenaires", "Become a partner"), ("/calendrier-fetes-senegal", "Festivals"), ("/urgences", "Emergency"), ("/presse", "Press"), ("/media-kit", "Media kit"), ("/privacy", "Privacy")),
}


def _ui_lang(lang: str) -> str:
    return "en" if str(lang or "").lower().startswith(("en", "es", "de", "it")) else "fr"


# Ambiances régionales des pages lieux et régions (couleurs et bande décorée).
_AMBIANCES = {
    "saint-louis": "saint-louis",
    "ziguinchor": "casamance", "kolda": "casamance", "sedhiou": "casamance",
}


def region_ambiance(region: str) -> str:
    """« saint-louis », « casamance » ou « » selon la région."""
    import unicodedata

    key = "".join(ch for ch in unicodedata.normalize("NFD", str(region or "").lower()) if unicodedata.category(ch) != "Mn")
    return _AMBIANCES.get(key.strip(), "")


def body_tag(region: str = "") -> str:
    ambiance = region_ambiance(region)
    return f'<body data-ambiance="{ambiance}">' if ambiance else "<body>"


def site_header(current: str = "", lang: str = "fr") -> str:
    ui = _ui_lang(lang)
    current_attr = ' aria-current="page"'
    links = "".join(
        f'<a href="{escape(href)}"{current_attr if current and href.split("?")[0] == current else ""}>{escape(label)}</a>'
        for href, label in _NAV[ui]
    )
    return (
        '<header class="site-header">'
        f'<a class="site-brand" href="/"><span class="site-mark">{_MARK}</span><strong>Teranga <em>AI</em></strong></a>'
        f'<div class="site-nav">{links}<a class="site-cta" href="/">{escape(_CTA[ui])}</a></div>'
        "</header>"
    )


def site_footer(lang: str = "fr") -> str:
    ui = _ui_lang(lang)
    links = "".join(f'<a href="{escape(href)}">{escape(label)}</a>' for href, label in _FOOTER[ui])
    langs = "Français · English · Wolof"
    return f'<footer class="site-footer"><span>Teranga AI · {langs}</span><nav aria-label="Liens">{links}</nav></footer>'


def register_layout_globals(app) -> None:
    """Expose the shared header/footer to Jinja templates."""
    from markupsafe import Markup

    # Le HTML vient de constantes du code ; les libellés et liens passent par escape() ci-dessus.
    app.jinja_env.globals.update(
        site_head=Markup(HEAD_ASSETS),  # nosec B704
        site_header=lambda current="", lang="fr": Markup(site_header(current, lang)),  # nosec B704
        site_footer=lambda lang="fr": Markup(site_footer(lang)),  # nosec B704
    )
