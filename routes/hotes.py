"""Teranga Hôtes : page publique d'un hébergeur et son QR code (services/hotes.py)."""

from __future__ import annotations

from flask import Response, abort

from services.hotes import SLUG, page_hote, qr_svg


def register_hotes_routes(app, hotes: dict, site_url: str) -> None:
    def trouver(slug: str) -> dict:
        if not SLUG.fullmatch(slug or "") or slug not in hotes:
            abort(404)
        return hotes[slug]

    @app.get("/hote/<slug>")
    def page_hebergeur(slug):
        hote = trouver(slug)
        reponse = Response(page_hote(hote), mimetype="text/html")
        reponse.headers["Cache-Control"] = "public, max-age=600"
        if not hote["indexer"]:
            # Lien donné aux clients de la maison, pas une page pour les moteurs (sauf demande de l'hôte).
            reponse.headers["X-Robots-Tag"] = "noindex, nofollow"
        return reponse

    @app.get("/hote/<slug>/qr.svg")
    def qr_hebergeur(slug):
        hote = trouver(slug)
        reponse = Response(qr_svg(f"{site_url}/hote/{hote['slug']}"), mimetype="image/svg+xml")
        reponse.headers["Cache-Control"] = "public, max-age=86400"
        return reponse
