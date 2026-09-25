from flask import Response

from app import SITE_URL, app

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
    if environ.get("PATH_INFO") == "/robots.txt":
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(ROBOTS))),
            ("Cache-Control", "public, max-age=300"),
        ]
        start_response("200 OK", headers)
        return [ROBOTS]
    return _inner(environ, start_response)


app.wsgi_app = _wsgi
