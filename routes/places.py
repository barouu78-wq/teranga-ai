"""Place pages: /lieux index and one indexable page per place."""

import secrets

from flask import Response, request

from services.places import place_index, render_place_page, render_places_index


def register_place_routes(app, knowledge, site_url):
    places = list(knowledge.get("places", []) or [])
    by_id = place_index(places)

    @app.get("/lieux")
    def places_index():
        return Response(
            render_places_index(places, site_url),
            mimetype="text/html",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/lieux/<place_id>")
    def place_page(place_id):
        place = by_id.get(place_id)
        if place is None:
            return Response("Lieu introuvable", status=404, mimetype="text/plain")
        nonce = secrets.token_urlsafe(16)
        # Lu par add_security_headers : le script de galerie est autorisé par nonce.
        request._csp_nonce = nonce
        return Response(
            render_place_page(place, places, site_url, nonce=nonce),
            mimetype="text/html",
        )
