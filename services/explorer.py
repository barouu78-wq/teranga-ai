"""Rendu de la page Explorer de Teranga AI."""

from html import escape
from urllib.parse import quote


def render_explorer_page(places, regions, selected_region=""):
    cards = []
    for place in places:
        cards.append(
            '<article data-place="{name}" data-region="{region}" data-summary="{summary}" data-lat="{lat}" data-lon="{lon}"><div class="gallery" data-query="{photo}"><div class="gallery-track"></div><div class="gallery-credit">Wikimedia Commons</div></div><small>{type} · {region}</small><h2>{name}</h2><p>{summary}</p>'
            '<a href="/?q={query}" data-place-action="chat">Demander à Teranga →</a> <a href="/trip-planner" data-place-action="plan">Planifier depuis ce lieu</a> '
            '<a href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}" target="_blank" rel="noopener">Carte</a></article>'.format(
                type=escape(str(place.get("type", "lieu"))), region=escape(str(place.get("region", ""))),
                name=escape(str(place.get("name", ""))),
                photo=escape(quote(str((place.get("image_queries") or [place.get("name", "")])[0]))),
                summary=escape(str(place.get("summary", ""))),
                query=escape(quote("Parle-moi de " + str(place.get("name", "")))),
                lat=escape(str(place.get("latitude", ""))), lon=escape(str(place.get("longitude", ""))),
            )
        )
    region_links = " · ".join(
        '<a href="/explorer?region={id}">{name}</a>'.format(id=escape(quote(str(r.get("id", "")))), name=escape(str(r.get("name", ""))))
        for r in regions
    )
    selected = (selected_region or "").strip().lower()
    if selected:
        target = next((r for r in regions if r.get("id") == selected), None)
        if target:
            cards = [x for x, p in zip(cards, places) if p.get("region", "").lower() == target.get("name", "").lower()]
    html = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Explorer les lieux du Sénégal avec Teranga AI."><title>Explorer le Sénégal | Teranga AI</title>
<style>
body{margin:0;background:#0b0907;color:#f6efe3;font:15px/1.5 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:24px 16px 50px}a{color:#e2b34a;text-decoration:none}.hero{padding:24px;border:1px solid #3b2d18;border-radius:24px;background:#171310;margin-bottom:16px}.muted{color:#b8a48c}.regions{line-height:2}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}article{padding:16px;border:1px solid #3b2d18;border-radius:20px;background:#171310}article .gallery{height:170px;margin:-16px -16px 14px;background:#0f0d0b;border-radius:20px 20px 0 0;overflow:hidden}.gallery-track{height:145px;display:flex;overflow-x:auto;scroll-snap-type:x mandatory}.gallery-track img{width:100%;min-width:100%;height:145px;object-fit:cover;scroll-snap-align:start}.gallery-credit{height:25px;padding:4px 9px;color:#b8a48c;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}article small{color:#e2b34a;text-transform:uppercase}article>a{display:inline-block;margin:4px 8px 0 0;min-height:24px;line-height:24px} @media(max-width:560px){main{padding:16px 10px 40px}.hero{padding:18px;border-radius:20px}.hero h1{font-size:30px}.regions{line-height:2.25}.grid{gap:10px}article{padding:14px;border-radius:18px}article .gallery{margin:-14px -14px 12px;border-radius:18px 18px 0 0}article>a{display:block;margin:8px 0 0;min-height:40px;line-height:40px;padding:0 4px;border-top:1px solid #3b2d18}article>a:last-child{border-top:0}.gallery-track,.gallery-track img{height:155px}.gallery{height:180px!important}.gallery-credit{height:25px}}article h2{font-family:Georgia,serif;margin:8px 0}article p{color:#b8a48c;min-height:64px}@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.grid{grid-template-columns:1fr}}
</style><script>
async function loadGalleries(){for(const box of document.querySelectorAll('.gallery[data-query]')){try{const d=await fetch('/explorer-image?query='+encodeURIComponent(box.dataset.query)).then(r=>r.json());if(!d.images||!d.images.length){box.style.display='none';continue}const track=box.querySelector('.gallery-track');track.replaceChildren();d.images.forEach(x=>{const img=document.createElement('img');img.loading='lazy';img.alt=x.alt||'';img.src=x.display_url||('/image-proxy?url='+encodeURIComponent(x.url));img.dataset.directUrl=x.url||'';img.onerror=()=>{if(img.dataset.fallbackUsed||!img.dataset.directUrl)return;img.dataset.fallbackUsed='1';img.src=img.dataset.directUrl};track.appendChild(img)});const x=d.images[0];box.querySelector('.gallery-credit').textContent='Wikimedia Commons'+(x.artist?' · '+x.artist:'')+(x.license?' · '+x.license:'')}catch(_){box.style.display='none'}}}
function savePlaceContext(article, journey){const context={name:article.dataset.place||'',region:article.dataset.region||'',summary:article.dataset.summary||'',latitude:article.dataset.lat||'',longitude:article.dataset.lon||'',query:'Parle-moi de '+(article.dataset.place||'')};try{sessionStorage.setItem('teranga-place-context',JSON.stringify(context));sessionStorage.setItem('teranga-place-name',context.name);sessionStorage.setItem('teranga-journey',journey)}catch(_){}} function bindPlaceContext(){document.querySelectorAll('article[data-place]').forEach(article=>article.querySelectorAll('[data-place-action]').forEach(link=>link.addEventListener('click',()=>savePlaceContext(article,link.dataset.placeAction))))} document.addEventListener('DOMContentLoaded',()=>{loadGalleries();bindPlaceContext();});
</script></head><body><main><p><a href="/">← Teranga AI</a></p><section class="hero"><small>EXPLORER · SÉNÉGAL</small><h1>Le Sénégal, lieu par lieu.</h1><p class="muted">Explore les fiches lieux de Teranga AI : histoire, culture, coordonnées et recherches photo.</p><div class="regions">{regions}</div></section><div class="grid">{cards}</div></main></body></html>"""
    return html.replace("{regions}", region_links).replace("{cards}", "".join(cards))
