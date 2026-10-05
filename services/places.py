"""Indexable place pages (/lieux/<id>) built from the Senegal knowledge base."""

from __future__ import annotations

import json
from html import escape
from urllib.parse import quote

from services.seo import REGION_SEO_NAMES, region_slug
from services.site_layout import HEAD_ASSETS, asset_url, site_footer, site_header

TYPE_LABELS = {
    "heritage": "Patrimoine",
    "natural_site": "Site naturel",
    "cultural_site": "Site culturel",
    "religious_site": "Lieu religieux",
    "locality": "Localité",
    "beach": "Plage",
    "coastal_site": "Littoral",
    "island": "Île",
    "monument": "Monument",
    "museum": "Musée",
}

def place_index(places) -> dict[str, dict]:
    return {str(place.get("id")): place for place in places or [] if place.get("id")}


def place_url(site_url: str, place: dict) -> str:
    return f"{site_url.rstrip('/')}/lieux/{quote(str(place.get('id', '')))}"


def _coords(place):
    try:
        lat = float(place.get("latitude"))
        lon = float(place.get("longitude"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _head(title, description, url, site_url, ld):
    ld_json = json.dumps(ld, ensure_ascii=True).replace("<", "\\u003c")
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="robots" content="index,follow"><meta name="description" content="{escape(description)}">'
        f'<link rel="canonical" href="{escape(url)}"><meta property="og:site_name" content="Teranga AI">'
        f'<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(description)}">'
        f'<meta property="og:type" content="article"><meta property="og:url" content="{escape(url)}">'
        f'<meta property="og:image" content="{escape(site_url)}/og.png"><meta name="twitter:card" content="summary_large_image">'
        f'<title>{escape(title)}</title><script type="application/ld+json">{ld_json}</script>'
        f"{HEAD_ASSETS}</head>"
    )


def render_place_page(place: dict, places, site_url: str, nonce: str = "") -> str:
    site_url = site_url.rstrip("/")
    name = str(place.get("name", ""))
    region = str(place.get("region", ""))
    locality = str(place.get("locality", "") or region)
    summary = str(place.get("summary", ""))
    history = str(place.get("history", ""))
    type_label = TYPE_LABELS.get(str(place.get("type", "")), "Lieu")
    url = place_url(site_url, place)
    title = f"{name} ({region}) : histoire, que voir, carte | Teranga AI"
    description = (summary + " " + (f"Région {region}." if region else "")).strip()[:300]
    coords = _coords(place)
    what_to_see = [item.strip() for item in str(place.get("what_to_see", "")).split(";") if item.strip()]

    attraction = {
        "@type": "TouristAttraction",
        "name": name,
        "description": summary,
        "url": url,
        "address": {"@type": "PostalAddress", "addressLocality": locality, "addressRegion": region, "addressCountry": "SN"},
    }
    if coords:
        attraction["geo"] = {"@type": "GeoCoordinates", "latitude": coords[0], "longitude": coords[1]}
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            attraction,
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Accueil", "item": site_url + "/"},
                {"@type": "ListItem", "position": 2, "name": "Lieux du Sénégal", "item": site_url + "/lieux"},
                {"@type": "ListItem", "position": 3, "name": name, "item": url},
            ]},
        ],
    }

    sections = []
    if history:
        sections.append(f"<section><h2>Histoire et contexte</h2><p>{escape(history)}</p></section>")
    if what_to_see:
        items = "".join(f"<li>{escape(item)}</li>" for item in what_to_see)
        sections.append(f"<section><h2>Que voir</h2><ul>{items}</ul></section>")
    sections.append(
        '<section><h2>Photos</h2><div class="gallery" id="gallery" '
        f'data-query="{escape(str((place.get("image_queries") or [name])[0]))}"></div>'
        '<div class="credit" id="gallery-credit"></div></section>'
    )
    if coords:
        lat, lon = coords
        delta = 0.08
        bbox = f"{lon - delta:.4f},{lat - delta:.4f},{lon + delta:.4f},{lat + delta:.4f}"
        sections.append(
            "<section><h2>Carte</h2>"
            f'<iframe title="Carte de {escape(name)}" loading="lazy" referrerpolicy="no-referrer" '
            f'src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;layer=mapnik&amp;marker={lat:.4f},{lon:.4f}"></iframe>'
            f'<p class="muted"><a href="https://www.openstreetmap.org/?mlat={lat:.4f}&amp;mlon={lon:.4f}#map=12/{lat:.4f}/{lon:.4f}" '
            'target="_blank" rel="noopener noreferrer">Ouvrir dans OpenStreetMap</a> · '
            f'<a href="https://www.google.com/maps/search/?api=1&amp;query={lat:.5f},{lon:.5f}" target="_blank" rel="noopener noreferrer">Google Maps</a></p>'
            "</section>"
        )
    sections.append(
        "<section><h2>Infos pratiques</h2><p>Horaires, tarifs, accès et conditions de visite peuvent changer. "
        "Demandez à Teranga AI une information à jour pour votre date de visite et vérifiez-la auprès des sources officielles.</p></section>"
    )
    nearby = [
        other for other in places or []
        if other is not place and other.get("id") and other.get("region") == region
    ][:6]
    if nearby:
        links = "".join(
            f'<a class="card" href="/lieux/{quote(str(o["id"]))}"><strong>{escape(str(o.get("name", "")))}</strong>'
            f'<br><small>{escape(str(o.get("summary", ""))[:110])}</small></a>'
            for o in nearby
        )
        sections.append(f'<section><h2>À voir aussi dans la région {escape(region)}</h2><div class="grid">{links}</div></section>')
    if region in REGION_SEO_NAMES:
        sections.append(
            f'<p class="related"><a href="/regions/{escape(region_slug(region))}">Guide de la région {escape(region)} →</a></p>'
        )

    ask = quote(f"Parle-moi de {name}")
    plan = quote(name)
    actions = (
        '<div class="actions">'
        f'<a class="cta" href="/?q={ask}">Demander à Teranga AI</a>'
        f'<a class="cta" href="/trip-planner?context_place={plan}">Planifier un voyage depuis ce lieu</a>'
        '<a class="cta" href="/explorer">Explorer d’autres lieux</a>'
        "</div>"
    )
    nonce_attr = f' nonce="{escape(nonce)}"' if nonce else ""
    script = (
        f"<script{nonce_attr}>(async()=>{{const box=document.getElementById('gallery');if(!box)return;"
        "try{const d=await fetch('/explorer-image?query='+encodeURIComponent(box.dataset.query)).then(r=>r.json());"
        "const list=(d.images||[]).slice(0,4);if(!list.length){box.closest('section').remove();return}"
        "list.forEach(x=>{const img=document.createElement('img');img.loading='lazy';img.decoding='async';img.alt=x.alt||'';"
        "img.src=x.display_url||('/image-proxy?url='+encodeURIComponent(x.url));box.appendChild(img)});"
        "document.getElementById('gallery-credit').textContent='Photos : '+(list[0].credit||'Wikimedia Commons')}"
        "catch(_){box.closest('section').remove()}})();</script>"
    )
    return (
        _head(title, description, url, site_url, ld)
        + "<body>" + site_header("/lieux")
        + '<main><p class="related"><a href="/lieux">← Tous les lieux du Sénégal</a></p><article>'
        + f'<div class="kicker">{escape(type_label)} · {escape(region)}</div>'
        + f"<h1>{escape(name)}</h1><p class=\"muted\">{escape(summary)}</p>"
        + actions
        + "".join(sections)
        + "</article></main>"
        + site_footer()
        + script
        + "</body></html>"
    )


def render_places_index(places, site_url: str) -> str:
    site_url = site_url.rstrip("/")
    url = f"{site_url}/lieux"
    title = "Lieux à visiter au Sénégal : patrimoine, nature, plages | Teranga AI"
    description = "Fiches des lieux du Sénégal : Gorée, Saint-Louis, Djoudj, Sine-Saloum, Casamance, pays Bassari et plus, avec histoire, carte et photos."
    by_region: dict[str, list] = {}
    for place in places or []:
        if place.get("id"):
            by_region.setdefault(str(place.get("region") or "Autres"), []).append(place)
    blocks = []
    for region in sorted(by_region):
        cards = "".join(
            f'<a class="card" href="/lieux/{quote(str(p["id"]))}" data-type="{escape(str(p.get("type", "")))}" '
            f'data-text="{escape(_search_text(p))}"><strong>{escape(str(p.get("name", "")))}</strong>'
            f'<br><small>{escape(TYPE_LABELS.get(str(p.get("type", "")), "Lieu"))} · {escape(str(p.get("summary", ""))[:100])}</small></a>'
            for p in by_region[region]
        )
        blocks.append(f'<section data-region-block><h2>{escape(region)}</h2><div class="grid">{cards}</div></section>')
    types = sorted({str(p.get("type", "")) for p in places or [] if p.get("id") and p.get("type") in TYPE_LABELS},
                   key=lambda t: TYPE_LABELS[t])
    options = "".join(f'<option value="{escape(t)}">{escape(TYPE_LABELS[t])}</option>' for t in types)
    # Recherche instantanée : sans JavaScript, la page reste une liste complète.
    search = (
        '<form class="place-search" role="search" onsubmit="return false">'
        '<label>Rechercher un lieu <input type="search" id="place-q" placeholder="Gorée, plage, Casamance…" autocomplete="off"></label>'
        f'<label>Type <select id="place-type"><option value="">Tous</option>{options}</select></label>'
        '<p class="muted" id="place-count" aria-live="polite"></p></form>'
    )
    # Script statique (et non inline) : la page reste en cache public sans nonce CSP.
    script = f'<script src="{asset_url("places-search.js")}" defer></script>'
    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Lieux du Sénégal",
        "itemListElement": [
            {"@type": "ListItem", "position": index + 1, "url": place_url(site_url, place), "name": place.get("name", "")}
            for index, place in enumerate(p for p in places or [] if p.get("id"))
        ],
    }
    return (
        _head(title, description, url, site_url, ld)
        + "<body>" + site_header("/lieux")
        + '<main class="wide"><article><div class="kicker">Guide</div>'
        + "<h1>Lieux du Sénégal</h1>"
        + f'<p class="muted">{escape(description)}</p>'
        + search
        + "".join(blocks)
        + "</article></main>"
        + site_footer()
        + script
        + "</body></html>"
    )


def _search_text(place) -> str:
    """Texte de recherche sans accents : nom, région, localité, type et résumé."""
    import unicodedata

    raw = " ".join(str(place.get(k, "")) for k in ("name", "region", "locality", "summary", "what_to_see"))
    raw += " " + TYPE_LABELS.get(str(place.get("type", "")), "")
    return "".join(c for c in unicodedata.normalize("NFD", raw.lower()) if unicodedata.category(c) != "Mn")


def _norm(text: object) -> str:
    import unicodedata

    raw = unicodedata.normalize("NFD", str(text or "").lower())
    return " ".join("".join(c if c.isalnum() else " " for c in raw if unicodedata.category(c) != "Mn").split())


def _mentions(text: str, term: str) -> bool:
    return bool(term) and f" {term} " in f" {text} "


def mentioned_places(text: object, places, limit: int = 2) -> list[dict]:
    """Fiches /lieux citées dans une question (« Parle-moi de Gorée » → Île de Gorée).

    Le nom complet prime ; à défaut, le nom court (« Gorée »), sauf s'il désigne
    une région ou un autre lieu (« Sédhiou » renvoie à la ville, pas au fort).
    """
    from services.image_topics import _short_place_name

    value = _norm(text)
    if not value:
        return []
    usable = [p for p in places or [] if p.get("id") and p.get("name")]
    full_names = {_norm(p["name"]) for p in usable}
    regions = {_norm(p.get("region", "")) for p in usable}
    def names(place):
        # « Lac Rose / Lac Retba » : chaque partie compte ; plus les alias explicites.
        parts = [part.strip() for part in str(place["name"]).split("/")]
        return [_norm(n) for n in parts + list(place.get("aliases") or []) if str(n).strip()]

    found = [p for p in usable if any(_mentions(value, n) for n in names(p))]
    if not found:
        for place in usable:
            short = _norm(_short_place_name(str(place["name"])))
            if short and short not in regions and short not in full_names and _mentions(value, short):
                found.append(place)
    found.sort(key=lambda p: len(str(p["name"])), reverse=True)
    result, seen = [], set()
    for place in found:
        if place["id"] not in seen:
            seen.add(place["id"])
            result.append({"id": str(place["id"]), "name": str(place["name"])})
        if len(result) >= limit:
            break
    return result
