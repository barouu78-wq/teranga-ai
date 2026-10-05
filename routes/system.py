import json
import os
import secrets
from functools import lru_cache
from pathlib import Path

from flask import Response, jsonify, request

from services.assets import ICON_SVG, OG_SVG, build_og_png
from services.site_layout import HEAD_ASSETS, site_footer, site_header


def _related_android_app():
    package = os.getenv("ANDROID_APP_PACKAGE", "").strip()
    if not package:
        return {}
    return {"related_applications": [{
        "platform": "play",
        "id": package,
        "url": f"https://play.google.com/store/apps/details?id={package}",
    }]}


def register_system_routes(app, deps):
    indexnow_key = deps["indexnow_key"]
    issue_csrf = deps["issue_csrf"]
    csrf_ttl = deps["csrf_ttl"]
    csrf_cookie = deps["csrf_cookie"]
    home_html = deps["home_html"]
    site_url = deps["site_url"]
    build_icon_png = deps["build_icon_png"]
    icon_svg = deps["icon_svg"]
    redis_client = deps.get("redis_client")
    redis_configured = deps.get("redis_configured", redis_client is not None)
    # Seulement « configuré ou non » : jamais la clé elle-même.
    google_images = "configured" if deps.get("google_images_configured") else "missing"

    @app.route(f"/{indexnow_key}.txt")
    def indexnow():
        return Response(indexnow_key, mimetype="text/plain")

    @app.get("/health")
    def health():
        # « redis » permet de vérifier la configuration REDIS_URL après un
        # déploiement. Le site reste « ok » sans Redis (limites en mémoire).
        if redis_client is None:
            # REDIS_URL présente mais illisible ≠ REDIS_URL absente.
            redis_state = "misconfigured" if redis_configured else "disabled"
        else:
            try:
                redis_state = "ok" if redis_client.ping() else "unavailable"
            except Exception:
                redis_state = "unavailable"
        return jsonify({"status": "ok", "service": "teranga-ai", "redis": redis_state, "google_images": google_images}), 200, {"Cache-Control": "no-store"}

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
                    "description": "Teranga AI, votre guide du Sénégal : histoire des lieux, météo, itinéraires, négociation au marché et vie pratique, en français, anglais et wolof.",
                    "start_url": "/",
                    "scope": "/",
                    "display": "standalone",
                    "display_override": ["window-controls-overlay", "standalone"],
                    "orientation": "portrait-primary",
                    "lang": "fr",
                    "dir": "ltr",
                    "background_color": "#fbf3e6",
                    "theme_color": "#b5451b",
                    "categories": ["travel", "education", "lifestyle"],
                    "prefer_related_applications": False,
                    "launch_handler": {"client_mode": ["navigate-existing", "auto"]},
                    "handle_links": "preferred",
                    "icons": [
                        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
                    ],
                    "shortcuts": [
                        {"name": "Poser une question", "short_name": "Chat", "url": "/", "icons": [{"src": "/icon-192.png", "sizes": "192x192"}]},
                        {"name": "Planifier un voyage", "short_name": "Planificateur", "url": "/trip-planner", "icons": [{"src": "/icon-192.png", "sizes": "192x192"}]},
                        {"name": "Explorer les lieux", "short_name": "Explorer", "url": "/explorer", "icons": [{"src": "/icon-192.png", "sizes": "192x192"}]},
                    ],
                    "screenshots": [
                        {"src": "/static/screenshots/accueil.png", "sizes": "780x1560", "type": "image/png", "form_factor": "narrow", "label": "Accueil de Teranga AI"},
                        {"src": "/static/screenshots/guide-goree.png", "sizes": "780x1560", "type": "image/png", "form_factor": "narrow", "label": "Guide local : l'histoire de Gorée"},
                        {"src": "/static/screenshots/planificateur.png", "sizes": "780x1560", "type": "image/png", "form_factor": "narrow", "label": "Planificateur de voyage"},
                        {"src": "/static/screenshots/fiche-lieu.png", "sizes": "780x1560", "type": "image/png", "form_factor": "narrow", "label": "Fiche d'un lieu"},
                        {"src": "/static/screenshots/bureau-accueil.png", "sizes": "1280x800", "type": "image/png", "form_factor": "wide", "label": "Teranga AI sur ordinateur"},
                        {"src": "/static/screenshots/bureau-planificateur.png", "sizes": "1280x800", "type": "image/png", "form_factor": "wide", "label": "Planificateur de voyage sur ordinateur"},
                    ],
                    # Lien vers l'application Google Play (TWA), seulement si son identifiant est configuré.
                    **_related_android_app(),
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
    # Même empreinte que asset_url : sinon le cache d'un an ne s'applique pas.
    from services.site_layout import asset_url

    home_js_url = asset_url("home.js")
    theme_js_url = asset_url("theme.js")

    @app.get("/")
    def home():
        nonce = secrets.token_urlsafe(16)
        request._csp_nonce = nonce
        response = Response(
            home_html.replace("__CSP_NONCE__", nonce)
            .replace("__SITE_URL__", site_url)
            .replace("__HOME_JS__", home_js_url)
            .replace("__THEME_JS__", theme_js_url),
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
