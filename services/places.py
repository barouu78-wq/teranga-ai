"""Indexable place pages (/lieux/<id>) built from the Senegal knowledge base."""

from __future__ import annotations

import json
from html import escape
from urllib.parse import quote

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

_STYLE = (
    "body{margin:0;background:#0b0907;color:#f6efe3;font:16px/1.65 system-ui,sans-serif}"
    "main{width:min(960px,calc(100% - 32px));margin:auto;padding:28px 0 60px}a{color:#e2b34a;text-decoration:none}"
    "article{background:#171310;border:1px solid #3b2d18;border-radius:26px;padding:28px}"
    "h1{font:700 clamp(32px,7vw,50px)/1.08 Georgia,serif;margin:8px 0 12px}h2{font-size:20px;margin:0 0 6px}"
    ".muted{color:#b8a48c}.kicker{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#b8a48c}"
    "section{border-top:1px solid #3b2d18;padding:18px 0}"
    ".actions{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}"
    ".cta{border:1px solid #3b2d18;border-radius:999px;padding:10px 14px;background:#20190f;color:#e2b34a;font-weight:700}"
    ".gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-top:10px}"
    ".gallery img{width:100%;height:160px;object-fit:cover;border-radius:14px;background:#20190f}"
    ".credit{font-size:12px;color:#b8a48c;margin-top:6px}"
    "iframe{width:100%;height:300px;border:0;border-radius:16px}"
    "ul{padding-left:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}"
    ".card{border:1px solid #3b2d18;border-radius:18px;padding:14px;background:#171310}"
    ".card small{color:#b8a48c}"
)


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
        f"<style>{_STYLE}</style></head>"
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
        + '<body><main><p><a href="/lieux">← Tous les lieux du Sénégal</a></p><article>'
        + f'<div class="kicker">{escape(type_label)} · {escape(region)}</div>'
        + f"<h1>{escape(name)}</h1><p class=\"muted\">{escape(summary)}</p>"
        + actions
        + "".join(sections)
        + "</article></main>"
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
            f'<a class="card" href="/lieux/{quote(str(p["id"]))}"><strong>{escape(str(p.get("name", "")))}</strong>'
            f'<br><small>{escape(TYPE_LABELS.get(str(p.get("type", "")), "Lieu"))} · {escape(str(p.get("summary", ""))[:100])}</small></a>'
            for p in by_region[region]
        )
        blocks.append(f'<section><h2>{escape(region)}</h2><div class="grid">{cards}</div></section>')
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
        + '<body><main><p><a href="/">← Teranga AI</a></p><article><div class="kicker">Guide</div>'
        + "<h1>Lieux du Sénégal</h1>"
        + f'<p class="muted">{escape(description)}</p>'
        + "".join(blocks)
        + "</article></main></body></html>"
    )
