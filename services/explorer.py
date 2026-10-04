"""Rendu de la page Explorer de Teranga AI."""

from html import escape
from urllib.parse import quote

from services.site_layout import HEAD_ASSETS, site_footer, site_header


def render_explorer_page(places, regions, selected_region=""):
    cards = []
    for place in places:
        cards.append(
            '<article data-place="{name}" data-region="{region}" data-summary="{summary}" data-lat="{lat}" data-lon="{lon}"><div class="gallery" data-query="{photo}"><div class="gallery-track"></div><div class="gallery-credit">Wikimedia Commons</div></div><small>{type} · {region}</small><h2>{name}</h2><p>{summary}</p>'
            '<div class="place-actions"><a class="primary" href="/lieux/{pid}">Fiche du lieu</a><a href="/?q={query}" data-place-action="chat">Demander à Teranga</a><a href="/trip-planner" data-place-action="plan">Planifier</a>'
            '<a href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}" target="_blank" rel="noopener">Carte</a></div></article>'.format(
                type=escape(str(place.get("type", "lieu"))), region=escape(str(place.get("region", ""))),
                name=escape(str(place.get("name", ""))),
                photo=escape(quote(str((place.get("image_queries") or [place.get("name", "")])[0]))),
                summary=escape(str(place.get("summary", ""))),
                query=escape(quote("Parle-moi de " + str(place.get("name", "")))),
                lat=escape(str(place.get("latitude", ""))), lon=escape(str(place.get("longitude", ""))),
                pid=escape(quote(str(place.get("id", "")))),
            )
        )
    selected = (selected_region or "").strip().lower()
    region_links = '<a href="/explorer"{all_current}>Tout le Sénégal</a>'.format(
        all_current=' aria-current="page"' if not selected else ""
    ) + "".join(
        '<a href="/explorer?region={id}"{current}>{name}</a>'.format(
            id=escape(quote(str(r.get("id", "")))),
            name=escape(str(r.get("name", ""))),
            current=' aria-current="page"' if str(r.get("id", "")).lower() == selected else "",
        )
        for r in regions
    )
    if selected:
        target = next((r for r in regions if r.get("id") == selected), None)
        if target:
            cards = [x for x, p in zip(cards, places) if p.get("region", "").lower() == target.get("name", "").lower()]
    html = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Explorer les lieux du Sénégal avec Teranga AI."><title>Explorer le Sénégal | Teranga AI</title>
{head}<style>
.explorer-hero{margin-bottom:18px}
.explorer-hero h1{margin-top:6px}
.regions{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}
.regions a{padding:7px 12px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);font-size:14px;text-decoration:none}
.regions a:hover{border-color:var(--accent);color:var(--link)}
.regions a[aria-current="page"]{background:var(--ink);border-color:var(--ink);color:var(--bg)}
.grid{grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.grid article{display:flex;flex-direction:column;padding:0;overflow:hidden;border-radius:var(--radius);box-shadow:var(--shadow-sm)}
.grid article .gallery{display:block;margin:0;background:var(--surface-2)}
.gallery-track{display:flex;height:180px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none}
.gallery-track::-webkit-scrollbar{display:none}
.gallery-track img{flex:0 0 100%;width:100%;height:180px;object-fit:cover;border-radius:0;scroll-snap-align:start}
.gallery.empty .gallery-track{align-items:center;justify-content:center;background:linear-gradient(135deg,var(--surface-2),var(--bg))}
.gallery.empty .gallery-track::after{content:"Photo indisponible";color:var(--muted);font-size:13px}
.gallery.empty .gallery-credit{visibility:hidden}
.gallery-credit{padding:5px 14px;color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.grid article small{padding:12px 16px 0;color:var(--gold);font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.grid article h2{margin:4px 16px 6px;font-size:21px}
.grid article p{flex:1;margin:0 16px 14px;color:var(--muted);font-size:15px}
.place-actions{display:flex;flex-wrap:wrap;gap:6px;padding:12px 16px 16px;border-top:1px solid var(--line)}
.place-actions a{display:inline-flex;align-items:center;min-height:40px;padding:7px 12px;border-radius:999px;border:1px solid var(--line);color:var(--ink);font-size:13px;font-weight:600;text-decoration:none}
.place-actions a.primary{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.place-actions a:hover{border-color:var(--line-strong)}
</style><script>
async function fillGallery(box){try{const d=await fetch('/explorer-image?query='+encodeURIComponent(box.dataset.query)).then(r=>r.json());if(!d.images||!d.images.length){box.classList.add('empty');return}const track=box.querySelector('.gallery-track');track.replaceChildren();d.images.forEach(x=>{const img=document.createElement('img');img.loading='lazy';img.decoding='async';img.alt=x.alt||'';img.src=x.display_url||('/image-proxy?url='+encodeURIComponent(x.url));img.dataset.directUrl=x.url||'';img.onerror=()=>{if(img.dataset.fallbackUsed||!img.dataset.directUrl)return;img.dataset.fallbackUsed='1';img.src=img.dataset.directUrl};track.appendChild(img)});const x=d.images[0];box.querySelector('.gallery-credit').textContent=(x.credit||'Wikimedia Commons')+(x.artist?' · '+x.artist:'')+(x.license?' · '+x.license:'')}catch(_){box.classList.add('empty')}} const GALLERY_CONCURRENCY=4;const galleryQueue=[];let galleryActive=0;function pumpGalleries(){while(galleryActive<GALLERY_CONCURRENCY&&galleryQueue.length){const box=galleryQueue.shift();galleryActive++;fillGallery(box).finally(()=>{galleryActive--;pumpGalleries()})}}function queueGallery(box){if(box.dataset.queued)return;box.dataset.queued='1';galleryQueue.push(box);pumpGalleries()}function loadGalleries(){const boxes=[...document.querySelectorAll('.gallery[data-query]')];if(!('IntersectionObserver' in window)){boxes.forEach(queueGallery);return}const io=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){io.unobserve(e.target);queueGallery(e.target)}}),{rootMargin:'600px 0px'});boxes.forEach(b=>io.observe(b))}
function savePlaceContext(article, journey){const context={name:article.dataset.place||'',region:article.dataset.region||'',summary:article.dataset.summary||'',latitude:article.dataset.lat||'',longitude:article.dataset.lon||'',query:'Parle-moi de '+(article.dataset.place||'')};try{sessionStorage.setItem('teranga-place-context',JSON.stringify(context));sessionStorage.setItem('teranga-place-name',context.name);sessionStorage.setItem('teranga-journey',journey)}catch(_){}} function bindPlaceContext(){document.querySelectorAll('article[data-place]').forEach(article=>article.querySelectorAll('[data-place-action]').forEach(link=>link.addEventListener('click',()=>savePlaceContext(article,link.dataset.placeAction))))} document.addEventListener('DOMContentLoaded',()=>{loadGalleries();bindPlaceContext();});
</script></head><body>{header}<main class="wide"><div class="panel explorer-hero"><span class="kicker">Explorer · Sénégal</span><h1>Le Sénégal, lieu par lieu.</h1><p class="muted">Histoire, culture, photos et carte de chaque lieu. Choisis une région ou ouvre une fiche.</p><nav class="regions" aria-label="Régions">{regions}</nav></div><div class="grid">{cards}</div></main>{footer}</body></html>"""
    return (
        html.replace("{head}", HEAD_ASSETS)
        .replace("{header}", site_header("/explorer"))
        .replace("{footer}", site_footer())
        .replace("{regions}", region_links)
        .replace("{cards}", "".join(cards))
    )
