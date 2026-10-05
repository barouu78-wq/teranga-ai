"""SEO and public discovery routes.

Route registration is kept separate from application orchestration.
"""

from html import escape

from flask import Response, abort

from services.international_seo import localized_sitemap_urls
from services.seo import SEO_PAGES, REGION_SEO_NAMES, render_region_page, region_slug, render_seo_page



def register_seo_routes(app, site_url, places=None):
    place_ids = [str(place["id"]) for place in places or [] if place.get("id")]

    @app.get("/regions/<slug>")
    def seo_region(slug):
        region = next((name for name in REGION_SEO_NAMES if region_slug(name) == slug), None)
        if not region:
            abort(404)
        return render_region_page(region, site_url, places)

    # Une route par page de SEO_PAGES : le sitemap et les routes ne peuvent plus
    # diverger (deux pages du sitemap renvoyaient 404).
    def _make_seo_view(slug):
        def view():
            return render_seo_page(slug, site_url)
        return view

    for slug in SEO_PAGES:
        app.add_url_rule(
            f"/{slug}",
            endpoint="seo_" + slug.replace("-", "_"),
            view_func=_make_seo_view(slug),
            methods=["GET"],
        )

    @app.get("/llms.txt")
    def llms():
        # Point d'entrée compact pour les crawlers et assistants qui lisent
        # des descriptions de sites en texte brut.
        body = (
            "# Teranga AI\\n\\n"
            "Teranga AI est un assistant numérique consacré au Sénégal, accessible depuis le Sénégal, la France et la diaspora.\\n\\n"
            "## Site officiel\\n"
            f"- {site_url}/\\n\\n"
            "## Pages prioritaires\\n"
            f"- {site_url}/assistant-senegal — assistant IA du Sénégal\\n"
            f"- {site_url}/ia-senegal — intelligence artificielle au Sénégal\\n"
            f"- {site_url}/dakar — guide pratique de Dakar\\n"
            f"- {site_url}/voyage-senegal — voyage au Sénégal\\n"
            f"- {site_url}/transport-senegal — transport au Sénégal\\n"
            f"- {site_url}/meteo-dakar — météo Dakar\\n"
            f"- {site_url}/visiter-goree — visiter Gorée\\n"
            f"- {site_url}/diaspora-senegalaise — diaspora sénégalaise\\n"
            f"- {site_url}/emploi-senegal — emploi au Sénégal\\n"
            f"- {site_url}/formation-senegal — formation au Sénégal\\n"
            f"- {site_url}/entreprendre-senegal — entreprendre au Sénégal\\n"
            f"- {site_url}/regions-senegal — 14 régions du Sénégal\\n\\n"
            "## Langues\\n"
            "Français, anglais et wolof.\\n\\n"
            "## Informations changeantes\\n"
            "Les horaires, prix, formalités, météo et disponibilités doivent être vérifiés auprès de sources récentes ou officielles.\\n"
        )
        return Response(body, mimetype="text/plain", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/robots.txt")
    def robots():
        body = (
            f"User-agent: *\n"
            f"Allow: /\n"
            f"Disallow: /chat\n"
            f"Disallow: /tts\n"
            f"Disallow: /stt\n"
            f"Disallow: /realtime-call\n"
            f"Disallow: /csrf\n"
            f"Disallow: /api/\n"
            f"Disallow: /image-proxy\n"
            f"Disallow: /explorer-image\n"
            f"Disallow: /exchange-rates\n"
            f"Sitemap: {site_url}/sitemap.xml\n"
        )
        return Response(
            body,
            mimetype="text/plain",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/sitemap.xml")
    def sitemap():
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{site_url}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>"
            f"<url><loc>{site_url}/trip-planner</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>"
            + "".join(
                f"<url><loc>{site_url}/{slug}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
                for slug in SEO_PAGES
            )
            + "".join(
                f"<url><loc>{site_url}/regions/{region_slug(region)}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>"
                for region in REGION_SEO_NAMES
            )
            + "".join(
                f"<url><loc>{url}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>"
                for url in localized_sitemap_urls(site_url)
            )
            + (
                f"<url><loc>{site_url}/lieux</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
                if place_ids else ""
            )
            + "".join(
                f"<url><loc>{site_url}/lieux/{escape(place_id)}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>"
                for place_id in place_ids
            )
            + "</urlset>"
        )
        return Response(
            body,
            mimetype="application/xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )
