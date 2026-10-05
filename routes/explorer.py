"""Explorer routes and image lookup endpoints."""

import threading
import time
from collections import OrderedDict

from flask import Response, jsonify, request

from services.explorer import render_explorer_page

IMAGE_CACHE_TTL = 6 * 60 * 60
IMAGE_CACHE_MAX = 512


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


def register_explorer_routes(app, knowledge, fetch_google_images, fetch_commons_images, image_proxy_url, rate_guard=None, fetch_article_images=None):
    region_names = [str(r.get("name", "")) for r in knowledge.get("regions", []) if isinstance(r, dict)]
    # Each Explorer page load requests one gallery per place: caching keeps the
    # paid Google Custom Search quota from being spent on identical queries.
    cache = OrderedDict()
    cache_lock = threading.Lock()

    def cached_images(query):
        key = query.casefold()
        now = time.time()
        with cache_lock:
            hit = cache.get(key)
            if hit and now - hit[0] < IMAGE_CACHE_TTL:
                cache.move_to_end(key)
                return [dict(item) for item in hit[1]]
        return None

    def store_images(query, images):
        with cache_lock:
            cache[query.casefold()] = (time.time(), [dict(item) for item in images])
            cache.move_to_end(query.casefold())
            while len(cache) > IMAGE_CACHE_MAX:
                cache.popitem(last=False)

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
        # 1. Photos choisies par les rédacteurs de l'article Wikipédia du lieu :
        #    les plus fiables (la recherche plein texte renvoie souvent rien ou hors sujet).
        images = []
        if title and fetch_article_images:
            for article in article_titles(title, region_names):
                try:
                    images = fetch_article_images(article, limit=4)
                except Exception as exc:
                    app.logger.warning("explorer-image article: %s", type(exc).__name__)
                    images = []
                if images:
                    break
        # 2. Google, puis 3. Commons ; une panne de l'un ne prive pas des autres.
        if not images:
            try:
                images = fetch_google_images(query, limit=4)
            except Exception as exc:
                app.logger.warning("explorer-image google: %s", type(exc).__name__)
                images = []
        if not images:
            try:
                images = fetch_commons_images(query, limit=4)
            except Exception as exc:
                app.logger.warning("explorer-image commons: %s", type(exc).__name__)
                images = []
            for item in images:
                item["display_url"] = image_proxy_url(item.get("url", ""))
        if images:
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
