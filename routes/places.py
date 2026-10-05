"""Place pages: /lieux index and one indexable page per place."""

import secrets

from flask import Response, abort, request

from services.monetization import affiliate_config, booking_html, booking_links, partners_for_place, partners_html
from services.places import place_index, render_place_page, render_places_index


def register_place_routes(app, knowledge, site_url, partners=None):
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
            abort(404)
        nonce = secrets.token_urlsafe(16)
        # Lu par add_security_headers : le script de galerie est autorisé par nonce.
        request._csp_nonce = nonce
        return Response(
            render_place_page(
                place, places, site_url, nonce=nonce,
                extra_html=booking_html(booking_links(place, affiliate_config())) + partners_html(partners_for_place(partners or [], place)),
            ),
            mimetype="text/html",
        )
