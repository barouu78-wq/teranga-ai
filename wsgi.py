from flask import Response

from app import SITE_URL, app

from services.international_seo import render_international_page, localized_sitemap_urls, localized_routes

_inner = app.wsgi_app

ROBOTS = (
    "User-agent: *\n"
    "Allow: /\n"
    "User-agent: Googlebot\n"
    "Allow: /\n"
    "User-agent: Google-InspectionTool\n"
    "Allow: /\n"
    f"Sitemap: {SITE_URL}/sitemap.xml\n"
).encode("utf-8")


def _wsgi(environ, start_response):
    path = environ.get("PATH_INFO", "")
    if path == "/robots.txt":
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(ROBOTS))),
            ("Cache-Control", "public, max-age=300"),
        ]
        start_response("200 OK", headers)
        return [ROBOTS]

    if path == "/sitemap.xml":
        urls = [f"{SITE_URL}/"]
        urls.extend(localized_sitemap_urls(SITE_URL))
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{u}</loc></url>" for u in urls)
            + "</urlset>"
        ).encode("utf-8")
        headers = [
            ("Content-Type", "application/xml; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "public, max-age=3600"),
        ]
        start_response("200 OK", headers)
        return [body]

    parts = [p for p in path.split("/") if p]
    if len(parts) == 2 and (parts[0], parts[1]) in localized_routes():
        response = render_international_page(parts[0], parts[1], SITE_URL)
        if response is not None:
            return response(environ, start_response)

    return _inner(environ, start_response)


app.wsgi_app = _wsgi
