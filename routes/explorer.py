"""Explorer routes and image lookup endpoints."""

import hashlib
import json
import threading
import time
from collections import OrderedDict

from flask import Response, jsonify, request

from services.explorer import render_explorer_page

IMAGE_CACHE_TTL = 6 * 60 * 60
# Aucune photo trouvée : on ne réinterroge pas Google/Wikipédia pendant 15 min
# (quota Google préservé), sans figer une panne passagère trop longtemps.
EMPTY_CACHE_TTL = 15 * 60
IMAGE_CACHE_MAX = 512
_REDIS_PREFIX = "teranga:explorer-img:"


def article_titles(title, region_names=()):
    """Titres d'articles Wikipédia à essayer pour un lieu : nom complet, puis nom court.

    « Île de Saint-Louis » → ["Île de Saint-Louis", "Saint-Louis"] ; le nom court
    est ignoré s'il désigne une région entière (« Corniche de Dakar » ≠ Dakar).
    """
    from services.image_topics import _short_place_name

    name = str(title or "").split("/")[0].strip()[:120]
    if not name:
        return []
    titles = [name]
    short = _short_place_name(name)
    if short and short.casefold() not in {r.casefold() for r in region_names}:
        titles.append(short)
    return titles


def register_explorer_routes(app, knowledge, fetch_google_images, fetch_commons_images, image_proxy_url, rate_guard=None, fetch_article_images=None, redis_client=None):
    region_names = [str(r.get("name", "")) for r in knowledge.get("regions", []) if isinstance(r, dict)]
    places_by_name = {
        str(p.get("name", "")).casefold(): p for p in knowledge.get("places", []) if isinstance(p, dict) and p.get("name")
    }
    # Chaque visite de l'Explorer demande une galerie par lieu : le cache évite
    # de dépenser le quota Google sur les mêmes recherches. Avec Redis, il est
    # partagé entre les workers et survit aux redéploiements.
    cache = OrderedDict()
    cache_lock = threading.Lock()

    def _redis_key(key):
        return _REDIS_PREFIX + hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]

    def cached_images(query):
        key = query.casefold()
        now = time.time()
        with cache_lock:
            hit = cache.get(key)
            if hit and now < hit[0]:
                cache.move_to_end(key)
                return [dict(item) for item in hit[1]]
        if redis_client is not None:
            try:
                raw = redis_client.get(_redis_key(key))
                if raw:
                    images = json.loads(raw)
                    if isinstance(images, list):
                        images = [dict(item) for item in images if isinstance(item, dict)]
                        # Copie locale : les visites suivantes évitent un aller-retour Redis.
                        ttl = IMAGE_CACHE_TTL if images else EMPTY_CACHE_TTL
                        try:
                            remaining = int(redis_client.ttl(_redis_key(key)))
                            ttl = remaining if remaining > 0 else ttl
                        except Exception:
                            pass
                        with cache_lock:
                            cache[key] = (now + ttl, [dict(item) for item in images])
                            cache.move_to_end(key)
                            while len(cache) > IMAGE_CACHE_MAX:
                                cache.popitem(last=False)
                        return images
            except Exception:
                app.logger.warning("explorer-image redis get failed")
        return None

    def store_images(query, images):
        key = query.casefold()
        ttl = IMAGE_CACHE_TTL if images else EMPTY_CACHE_TTL
        with cache_lock:
            cache[key] = (time.time() + ttl, [dict(item) for item in images])
            cache.move_to_end(key)
            while len(cache) > IMAGE_CACHE_MAX:
                cache.popitem(last=False)
        if redis_client is not None:
            try:
                redis_client.setex(_redis_key(key), ttl, json.dumps(images, ensure_ascii=False))
            except Exception:
                app.logger.warning("explorer-image redis set failed")

    def _try(source, fn, *args):
        try:
            return fn(*args, limit=4) or []
        except Exception as exc:
            # Code HTTP inclus (403 = accès refusé, 429 = quota) pour le diagnostic.
            app.logger.warning("explorer-image %s: %s %s", source, type(exc).__name__, getattr(exc, "code", ""))
            return []

    def find_images(query, title):
        # 1. Google Images (meilleures photos).
        images = _try("google", fetch_google_images, query)
        if images:
            return images, "google"
        # 2. Photos de l'article Wikipédia du lieu (nom complet, puis nom court).
        if title and fetch_article_images:
            for article in article_titles(title, region_names):
                images = _try("article", fetch_article_images, article)
                if images:
                    return images, "article"
        # 3. Recherche Commons : la requête demandée, puis les autres requêtes
        #    prévues pour ce lieu dans la base, puis « <nom> Sénégal ».
        place = places_by_name.get(str(title or "").casefold())
        queries = [query]
        if place:
            queries += [str(q) for q in place.get("image_queries") or [] if q]
            queries.append(str(place.get("name", "")).split("/")[0].strip() + " Sénégal")
        for commons_query in list(dict.fromkeys(q for q in queries if q.strip()))[:4]:
            images = _try("commons", fetch_commons_images, commons_query)
            if images:
                for item in images:
                    item["display_url"] = image_proxy_url(item.get("url", ""))
                return images, "commons"
        return [], "none"

    @app.get("/explorer-image")
    def explorer_image():
        query = request.args.get("query", "").strip()[:180]
        title = request.args.get("title", "").strip()[:120]
        if not query:
            return jsonify({"images": []})
        cache_name = f"{query}|{title}"
        images = cached_images(cache_name)
        if images is not None:
            return jsonify({"images": images})
        if rate_guard is not None:
            blocked = rate_guard("explorer_image")
            if blocked is not None:
                return blocked
        images, source = find_images(query, title)
        if source == "none":
            # Visible dans les journaux : quels lieux n'ont aucune photo.
            app.logger.info("explorer-image none query=%r title=%r", query, title)
        store_images(cache_name, images)
        return jsonify({"images": images})

    @app.get("/explorer")
    def explorer():
        html = render_explorer_page(
            knowledge.get("places", []),
            knowledge.get("regions", []),
            request.args.get("region", ""),
        )
        return Response(html, mimetype="text/html")
