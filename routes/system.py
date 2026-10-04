import json
import secrets
from functools import lru_cache

from flask import Response, jsonify, request

from services.assets import ICON_SVG, OG_SVG, build_og_png


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

    @app.get("/sw.js")
    def service_worker():
        body = """
self.addEventListener('install', event => {
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.pathname === '/chat' || url.pathname === '/tts') return;
  if (url.pathname === '/' ) return;
});
"""
        resp = Response(
            body.strip() + "\n",
            mimetype="application/javascript",
        )
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

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

    @app.get("/")
    def home():
        nonce = secrets.token_urlsafe(16)
        request._csp_nonce = nonce
        response = Response(
            home_html.replace("__CSP_NONCE__", nonce).replace("__SITE_URL__", site_url),
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
