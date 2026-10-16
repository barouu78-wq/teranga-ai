"""Injection PostHog activée uniquement si les trois variables sont configurées.

Aucun SDK tiers n'est chargé avant le consentement explicite. Le SDK reste désactivé
si la configuration est incomplète ; les valeurs d'hôte doivent venir du compte PostHog.
"""
from __future__ import annotations

from html import escape
from urllib.parse import urlparse


def posthog_config(project_key: object, api_host: object, asset_host: object) -> dict[str, str] | None:
    key = str(project_key or "").strip()
    api = str(api_host or "").strip().rstrip("/")
    assets = str(asset_host or "").strip().rstrip("/")
    if not key.startswith("phc_") or len(key) > 200:
        return None
    parsed_api, parsed_assets = urlparse(api), urlparse(assets)
    for parsed in (parsed_api, parsed_assets):
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            return None
    api_origin = f"https://{parsed_api.hostname}" + (f":{parsed_api.port}" if parsed_api.port else "")
    assets_origin = f"https://{parsed_assets.hostname}" + (f":{parsed_assets.port}" if parsed_assets.port else "")
    return {
        "project_key": key,
        "api_host": api_origin,
        "asset_host": assets_origin,
        "api_origin": api_origin,
        "asset_origin": assets_origin,
    }


def posthog_tag(config: dict[str, str] | None) -> str:
    if not config:
        return ""
    return (
        '<script src="/static/posthog-consent.js" defer'
        f' data-project-key="{escape(config["project_key"], quote=True)}"'
        f' data-api-host="{escape(config["api_host"], quote=True)}"'
        f' data-asset-host="{escape(config["asset_host"], quote=True)}"></script>'
    )


def inject_posthog(response, config: dict[str, str] | None):
    """Inject only our local consent controller into buffered HTML pages."""
    if not config or response.direct_passthrough or response.is_streamed:
        return response
    if response.status_code != 200 or response.mimetype != "text/html":
        return response
    body = response.get_data(as_text=True)
    index = body.lower().rfind("</head>")
    if index < 0:
        return response
    response.set_data(body[:index] + posthog_tag(config) + body[index:])
    return response
