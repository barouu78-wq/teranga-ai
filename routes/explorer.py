"""Explorer routes and image lookup endpoints."""

from flask import Response, jsonify, request

from services.explorer import render_explorer_page


def register_explorer_routes(app, knowledge, fetch_commons_images, image_proxy_url):
    @app.get("/explorer-image")
    def explorer_image():
        query = request.args.get("query", "").strip()[:180]
        if not query:
            return jsonify({"images": []})
        try:
            images = fetch_commons_images(query, limit=4)
            for item in images:
                item["display_url"] = image_proxy_url(item.get("url", ""))
            return jsonify({"images": images})
        except Exception:
            app.logger.exception("explorer-image")
            return jsonify({"image": None})

    @app.get("/explorer")
    def explorer():
        html = render_explorer_page(
            knowledge.get("places", []),
            knowledge.get("regions", []),
            request.args.get("region", ""),
        )
        return Response(html, mimetype="text/html")
