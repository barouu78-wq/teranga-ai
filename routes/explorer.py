"""Explorer routes and image lookup endpoints."""

import threading
import time
from collections import OrderedDict

from flask import Response, jsonify, request

from services.explorer import render_explorer_page

IMAGE_CACHE_TTL = 6 * 60 * 60
IMAGE_CACHE_MAX = 512


def register_explorer_routes(app, knowledge, fetch_google_images, fetch_commons_images, image_proxy_url, rate_guard=None):
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
        if not query:
            return jsonify({"images": []})
        images = cached_images(query)
        if images is not None:
            return jsonify({"images": images})
        if rate_guard is not None:
            blocked = rate_guard("explorer_image")
            if blocked is not None:
                return blocked
        # Google en panne ou refusé ne doit pas priver la galerie de Commons.
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
            store_images(query, images)
        return jsonify({"images": images})

    @app.get("/explorer")
    def explorer():
        html = render_explorer_page(
            knowledge.get("places", []),
            knowledge.get("regions", []),
            request.args.get("region", ""),
        )
        return Response(html, mimetype="text/html")
