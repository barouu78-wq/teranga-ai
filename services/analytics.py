"""Optional privacy-friendly audience measurement (Plausible, Umami…).

Disabled unless ANALYTICS_SCRIPT_URL is set. The script is injected into HTML
pages only, and its origin is added to the Content-Security-Policy so nothing
else from that host is allowed.
"""

from __future__ import annotations

from html import escape
from urllib.parse import urlparse


def analytics_config(script_url: object, site_id: object = "") -> dict[str, str] | None:
    """Validate the configuration; returns None when analytics is disabled."""
    url = str(script_url or "").strip()
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    origin = f"https://{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")
    return {"script_url": url, "site_id": str(site_id or "").strip(), "origin": origin}


def analytics_tag(config: dict[str, str] | None) -> str:
    if not config:
        return ""
    attributes = [f'src="{escape(config["script_url"])}"', "defer"]
    site_id = config.get("site_id")
    if site_id:
        # Plausible lit data-domain, Umami data-website-id : les deux sont inoffensifs.
        attributes.append(f'data-domain="{escape(site_id)}"')
        attributes.append(f'data-website-id="{escape(site_id)}"')
    return "<script " + " ".join(attributes) + "></script>"


def inject_analytics(response, config: dict[str, str] | None):
    """Insert the analytics tag before </head> of a buffered HTML response."""
    if not config or response.direct_passthrough or response.is_streamed:
        return response
    if response.status_code != 200 or response.mimetype != "text/html":
        return response
    body = response.get_data(as_text=True)
    index = body.lower().rfind("</head>")
    if index == -1:
        return response
    response.set_data(body[:index] + analytics_tag(config) + body[index:])
    return response
