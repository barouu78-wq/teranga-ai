import hashlib
import json
import secrets
from functools import lru_cache
from pathlib import Path

from flask import Response, jsonify, request

from services.assets import ICON_SVG, OG_SVG, build_og_png
from services.site_layout import HEAD_ASSETS, site_footer, site_header


def register_system_routes(app, deps):
    indexnow_key = deps["indexnow_key"]
    issue_csrf = deps["issue_csrf"]
    csrf_ttl = deps["csrf_ttl"]
    csrf_cookie = deps["csrf_cookie"]
    home_html = deps["home_html"]
    site_url = deps["site_url"]
    build_icon_png = deps["build_icon_png"]
    icon_svg = deps["icon_svg"]

    @app.route(f"/{indexnow_key}.txt")
    def indexnow():
        return Response(indexnow_key, mimetype="text/plain")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "teranga-ai"})

    # Images partagées (aperçus WhatsApp/Facebook, favicon) : référencées par
    # toutes les pages, elles doivent toujours répondre.
    @lru_cache(maxsize=4)
    def cached_png(kind):
        return build_og_png() if kind == "og" else build_icon_png(int(kind))

    @app.get("/icon.svg")
    def icon_svg_route():
        return Response(ICON_SVG, mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/og.svg")
    def og_svg():
        return Response(OG_SVG, mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/og.png")
    def og_png():
        try:
            return Response(cached_png("og"), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})
        except Exception:
            app.logger.exception("og.png")
            return og_svg()

    @app.get("/favicon.ico")
    def favicon():
        try:
            return Response(cached_png("48"), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})
        except Exception:
            return icon_svg_route()

    @app.get("/icon-192.png")
    def icon_192():
        try:
            return Response(
                build_icon_png(192),
                mimetype="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except Exception:
            return icon_svg()

    @app.get("/icon-512.png")
    def icon_512():
        try:
            return Response(
                build_icon_png(512),
                mimetype="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except Exception:
            return icon_svg()

    sw_path = Path(__file__).resolve().parents[1] / "static" / "sw.js"

    @app.get("/sw.js")
    def service_worker():
        # Servi depuis la racine pour que sa portée couvre tout le site.
        resp = Response(sw_path.read_text(encoding="utf-8"), mimetype="application/javascript")
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    widget_path = Path(__file__).resolve().parents[1] / "static" / "widget.js"

    @app.get("/widget.js")
    def partner_widget():
        # Chargé par les sites partenaires : URL stable, cache court.
        resp = Response(widget_path.read_text(encoding="utf-8"), mimetype="application/javascript")
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    @app.get("/offline")
    def offline_page():
        html = (
            '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex"><title>Hors ligne | Teranga AI</title>'
            + HEAD_ASSETS + "</head><body>" + site_header()
            + '<main><article><span class="kicker">Connexion</span><h1>Vous êtes hors ligne</h1>'
            '<p class="intro">Teranga AI a besoin d’internet pour répondre. Les pages que vous avez déjà ouvertes '
            "restent consultables : utilisez le bouton retour ou rouvrez-les depuis l’historique.</p>"
            '<div class="actions"><a class="cta primary" href="/">Réessayer</a><a class="cta" href="/lieux">Lieux déjà visités</a></div>'
            "</article></main>" + site_footer() + "</body></html>"
        )
        return Response(html, mimetype="text/html")

    @app.get("/manifest.webmanifest")
    def manifest():
        return Response(
            json.dumps(
                {
                    "id": "/",
                    "name": "Teranga AI",
                    "short_name": "Teranga",
                    "description": "Assistant du Sénégal en français, anglais et wolof.",
                    "start_url": "/",
                    "scope": "/",
                    "display": "standalone",
                    "display_override": ["window-controls-overlay", "standalone"],
                    "orientation": "portrait-primary",
                    "lang": "fr",
                    "dir": "ltr",
                    "background_color": "#f6efe3",
                    "theme_color": "#0f6a43",
                    "categories": ["travel", "lifestyle", "utilities"],
                    "icons": [
                        {
                            "src": "/icon-192.png",
                            "sizes": "192x192",
                            "type": "image/png",
                            "purpose": "any",
                        },
                        {
                            "src": "/icon-512.png",
                            "sizes": "512x512",
                            "type": "image/png",
                            "purpose": "any maskable",
                        },
                    ],
                }
            ),
            mimetype="application/manifest+json",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/csrf")
    def csrf_token():
        token = issue_csrf(app.config["SECRET_KEY"], csrf_ttl)
        resp = jsonify({"token": token})
        resp.set_cookie(
            csrf_cookie,
            token,
            httponly=False,
            secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https",
            samesite="Lax",
            max_age=60 * 60 * 12,
            path="/",
        )
        return resp

    # Script de l'accueil servi comme fichier statique (mis en cache par le
    # navigateur) ; l'empreinte du contenu force le rechargement après un déploiement.
    home_js_path = Path(__file__).resolve().parents[1] / "static" / "home.js"
    home_js_url = "/static/home.js?v=" + hashlib.sha256(home_js_path.read_bytes()).hexdigest()[:12]

    @app.get("/")
    def home():
        nonce = secrets.token_urlsafe(16)
        request._csp_nonce = nonce
        response = Response(
            home_html.replace("__CSP_NONCE__", nonce)
            .replace("__SITE_URL__", site_url)
            .replace("__HOME_JS__", home_js_url),
            mimetype="text/html",
        )
        response.set_cookie(
            csrf_cookie,
            issue_csrf(app.config["SECRET_KEY"], csrf_ttl),
            httponly=False,
            secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https",
            samesite="Lax",
            max_age=60 * 60 * 12,
            path="/",
        )
        return response
