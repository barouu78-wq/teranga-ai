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
    "fr": (("/a-propos", "À propos"), ("/pour-les-entreprises", "Entreprises"), ("/partenaires", "Partenaires"), ("/presse", "Presse"), ("/media-kit", "Kit média")),
    "en": (("/a-propos", "About"), ("/pour-les-entreprises", "Business"), ("/partenaires", "Partners"), ("/presse", "Press"), ("/media-kit", "Media kit")),
}


def _ui_lang(lang: str) -> str:
    return "en" if str(lang or "").lower().startswith(("en", "es", "de", "it")) else "fr"


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

    app.jinja_env.globals.update(
        site_head=Markup(HEAD_ASSETS),
        site_header=lambda current="", lang="fr": Markup(site_header(current, lang)),
        site_footer=lambda lang="fr": Markup(site_footer(lang)),
    )
