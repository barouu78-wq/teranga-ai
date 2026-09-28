"""SEO and public discovery routes.

Route registration is kept separate from application orchestration.
"""

from flask import Response

from services.international_seo import localized_sitemap_urls
from services.seo import SEO_PAGES, render_seo_page


def register_seo_routes(app, site_url):
    @app.get("/a-propos")
    def seo_a_propos():
        return render_seo_page("a-propos", site_url)

    @app.get("/presse")
    def seo_presse():
        return render_seo_page("presse", site_url)

    @app.get("/media-kit")
    def seo_media_kit():
        return render_seo_page("media-kit", site_url)

    @app.get("/dakar")
    def seo_dakar():
        return render_seo_page("dakar", site_url)

    @app.get("/assistant-senegal")
    def seo_assistant_senegal():
        return render_seo_page("assistant-senegal", site_url)

    @app.get("/senegal")
    def seo_senegal():
        return render_seo_page("senegal", site_url)

    @app.get("/meteo-dakar")
    def seo_meteo_dakar():
        return render_seo_page("meteo-dakar", site_url)

    @app.get("/visiter-goree")
    def seo_visiter_goree():
        return render_seo_page("visiter-goree", site_url)

    @app.get("/restaurants-dakar")
    def seo_restaurants_dakar():
        return render_seo_page("restaurants-dakar", site_url)

    @app.get("/specialites-senegal")
    def seo_specialites_senegal():
        return render_seo_page("specialites-senegal", site_url)

    @app.get("/regions-senegal")
    def seo_regions_senegal():
        return render_seo_page("regions-senegal", site_url)

    @app.get("/france-senegal")
    def seo_france_senegal():
        return render_seo_page("france-senegal", site_url)

    @app.get("/diaspora-senegalaise")
    def seo_diaspora_senegalaise():
        return render_seo_page("diaspora-senegalaise", site_url)

    @app.get("/robots.txt")
    def robots():
        body = (
            f"User-agent: *\n"
            f"Allow: /\n"
            f"Disallow: /chat\n"
            f"Disallow: /tts\n"
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
                f"<url><loc>{url}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>"
                for url in localized_sitemap_urls(site_url)
            )
            + "</urlset>"
        )
        return Response(
            body,
            mimetype="application/xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )
