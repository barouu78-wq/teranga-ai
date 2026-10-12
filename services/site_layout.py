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


# Le lion du logo : même dessin que le symbole #sn-lion de templates/home.html (tests/test_design_lion_baobab.py).
LION_SVG = (
    '<path d="M50,21 Q52,14.9 68.6,9.7 Q68.6,21.8 63.8,23.9 Q68.2,19.2 85.4,21.2 Q80.5,32.2 75.3,32.2 Q81.2,29.6 96.1,38.5 Q87.1,46.6 82.3,44.5 Q88.8,44.5 98.9,58.7 Q87.4,62.4 83.8,58.6 Q89.7,61.2 93.1,78.2 Q81.1,76.9 79.4,72 Q83.7,76.8 80,93.8 Q69.5,87.7 70,82.5 Q72,88.6 61.6,102.6 Q54.5,92.8 57.1,88.3 Q56.4,94.7 41.2,103.2 Q38.7,91.4 42.9,88.3 Q39.7,93.8 22.4,95.5 Q24.9,83.7 30,82.5 Q24.8,86.3 8.3,80.7 Q15.4,71 20.6,72 Q14.2,73.3 1.4,61.6 Q11.9,55.5 16.2,58.6 Q9.9,57.2 3,41.2 Q15,40 17.7,44.5 Q12.5,40.7 12.6,23.3 Q24.1,27.1 24.7,32.2 Q21.5,26.7 28.8,10.8 Q37.7,19 36.2,23.9 Q35.5,17.5 48.6,6 Q53.4,17.1 50,21 Z" fill="#b8741a"/>'
    '<path d="M57.2,26.9 Q60.2,22.1 76.1,22.1 Q73.1,32.2 69.4,33.5 Q74.3,30.6 88.4,38 Q81.1,45.5 77.2,44.9 Q82.9,44.7 91.9,57.8 Q81.9,61.1 78.8,58.7 Q83.9,61.1 85.8,77 Q75.4,75.2 73.7,71.7 Q77.2,76.2 71.5,91.1 Q63.1,84.7 63.3,80.8 Q64.2,86.4 52.2,96.9 Q47.8,87.4 49.8,84 Q48,89.4 32.5,93.2 Q33,82.7 36.3,80.6 Q32.2,84.5 16.8,80.7 Q22.1,71.6 26,71.3 Q20.6,72.9 8.6,62.3 Q17.6,56.8 21.2,58.3 Q15.6,57.2 10,42.2 Q20.5,41.5 23,44.5 Q18.6,40.9 20.5,25.1 Q30.1,29.3 31,33.1 Q28.7,27.9 37.8,14.8 Q44.3,23 43.3,26.8 Q43.7,21.1 57.9,13.7 Q59.9,24.1 57.2,26.9 Z" fill="#d99a2b"/>'
    '<path d="M52.5,31.1 Q54.3,27.6 66.3,25 Q65.9,33 65.5,36.4 Q69,34.4 80.5,38.8 Q75.9,45.3 73.7,47.9 Q77.6,48.1 84.9,58 Q77.6,60.9 74.3,62 Q77.5,64.3 78.3,76.6 Q70.5,75.1 67.2,74.2 Q68.6,77.8 62.7,88.6 Q57,83.1 54.6,80.6 Q53.9,84.4 43,90.3 Q41.2,82.6 40.6,79.2 Q37.9,82 25.6,81.1 Q28.2,73.6 29.6,70.4 Q25.7,71.3 15.9,63.9 Q22.2,59 25,57.1 Q21.3,55.8 17,44.2 Q24.9,43.5 28.4,43.4 Q26,40.3 28.6,28.3 Q35.7,31.9 38.7,33.7 Q38.3,29.8 47,21.1 Q51,28 52.5,31.1 Z" fill="#ecbd55"/>'
    '<circle cx="32" cy="34" r="7" fill="#f3d49a"/>'
    '<circle cx="32" cy="34" r="3.4" fill="#36210f" opacity=".5"/>'
    '<circle cx="68" cy="34" r="7" fill="#f3d49a"/>'
    '<circle cx="68" cy="34" r="3.4" fill="#36210f" opacity=".5"/>'
    '<path d="M50,29 C64,29 72,40 72,54 C72,66 63,75 56,81 Q50,85 44,81 C37,75 28,66 28,54 C28,40 36,29 50,29 Z" fill="#f3d49a"/>'
    '<path d="M45.5,31 Q50,29.5 54.5,31 L55,57 Q50,59 45,57 Z" fill="#fbe9c2"/>'
    '<path d="M33,45 L46,48.5 L45.5,50.5 L34,48 Z" fill="#36210f"/>'
    '<path d="M67,45 L54,48.5 L54.5,50.5 L66,48 Z" fill="#36210f"/>'
    '<path d="M35,50.5 Q40.5,48.5 46,52.5 Q40.5,55 35,50.5 Z" fill="#d18d1f" stroke="#36210f" stroke-width="1.3" stroke-linejoin="round"/>'
    '<path d="M65,50.5 Q59.5,48.5 54,52.5 Q59.5,55 65,50.5 Z" fill="#d18d1f" stroke="#36210f" stroke-width="1.3" stroke-linejoin="round"/>'
    '<circle cx="41.5" cy="51.6" r="1.7" fill="#36210f"/>'
    '<circle cx="58.5" cy="51.6" r="1.7" fill="#36210f"/>'
    '<ellipse cx="44.5" cy="68" rx="7" ry="5.8" fill="#fbe9c2"/>'
    '<ellipse cx="55.5" cy="68" rx="7" ry="5.8" fill="#fbe9c2"/>'
    '<path d="M44.5,59.5 L55.5,59.5 Q57.5,60.5 55.6,63 L51.2,67 Q50,68 48.8,67 L44.4,63 Q42.5,60.5 44.5,59.5 Z" fill="#36210f"/>'
    '<path d="M50,67.5 L50,71 M50,71 Q47,74.5 43.5,72.5 M50,71 Q53,74.5 56.5,72.5" stroke="#36210f" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
    '<path d="M46,77.5 Q50,80 54,77.5" stroke="#36210f" stroke-width="1.2" fill="none" stroke-linecap="round" opacity=".45"/>'
)
_MARK = f'<svg viewBox="0 5 100 100" aria-hidden="true">{LION_SVG}</svg>'

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
