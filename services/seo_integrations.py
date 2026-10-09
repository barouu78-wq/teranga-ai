"""Connecteurs serveur pour les rapports SEO de Teranga AI."""
from __future__ import annotations

import csv
import datetime as dt
import io
import os
import re
from urllib.parse import quote, urlparse

import httpx

TIMEOUT = httpx.Timeout(10.0, connect=3.0)


class SeoIntegrationError(RuntimeError):
    """Erreur d'accès à une API SEO, sans exposer de secret ni le corps distant."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SeoIntegrationError(f"Configuration manquante : {name}.")
    return value


def _access_token() -> str:
    token = os.getenv("GOOGLE_SEARCH_CONSOLE_TOKEN", "").strip()
    if token:
        return token
    refresh_token = os.getenv("GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN", "").strip()
    if not refresh_token:
        raise SeoIntegrationError("Jeton Search Console non configuré.")
    form = {
        "client_id": _required("GOOGLE_SEARCH_CONSOLE_CLIENT_ID"),
        "client_secret": _required("GOOGLE_SEARCH_CONSOLE_CLIENT_SECRET"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        response = httpx.post("https://oauth2.googleapis.com/token", data=form, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SeoIntegrationError("Impossible d'obtenir un jeton Google OAuth.") from exc
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise SeoIntegrationError("Google OAuth n'a pas renvoyé de jeton d'accès.")
    return str(token)


def search_console_query(
    *,
    site_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    dimensions: list[str] | None = None,
    row_limit: int = 100,
) -> dict:
    """Interroge les performances Search Console avec OAuth ou un jeton d'accès."""
    site = (site_url or os.getenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "") or os.getenv("SITE_URL", "")).strip()
    if not site:
        raise SeoIntegrationError("Propriété Search Console non configurée.")
    today = dt.date.today()
    end = end_date or (today - dt.timedelta(days=3)).isoformat()
    start = start_date or (today - dt.timedelta(days=31)).isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", end) or start > end:
        raise ValueError("La période Search Console doit utiliser des dates ISO valides.")
    allowed_dimensions = {"date", "query", "page", "country", "device", "searchAppearance"}
    requested_dimensions = dimensions or ["query", "page"]
    if any(item not in allowed_dimensions for item in requested_dimensions):
        raise ValueError("Dimension Search Console non prise en charge.")
    url = "https://searchconsole.googleapis.com/webmasters/v3/sites/" + quote(site, safe="") + "/searchAnalytics/query"
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": requested_dimensions,
        "rowLimit": max(1, min(int(row_limit), 25000)),
    }
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
            json=body,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SeoIntegrationError("Échec de la requête Google Search Console.") from exc
    if not isinstance(data, dict):
        raise SeoIntegrationError("Réponse Search Console invalide.")
    return data


def semrush_domain_overview(
    domain: str, *, database: str | None = None, max_rows: int = 5
) -> dict:
    """Récupère un aperçu SEO de domaine via le rapport Semrush domain_ranks."""
    key = _required("SEMRUSH_API_KEY")
    raw_domain = str(domain or "").strip()
    parsed = urlparse(raw_domain if "://" in raw_domain else "https://" + raw_domain)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname or not re.fullmatch(r"[a-z0-9.-]+", hostname) or ".." in hostname:
        raise ValueError("Un nom de domaine valide est obligatoire.")
    db = (database or os.getenv("SEMRUSH_DATABASE", "fr")).strip().lower()
    if not re.fullmatch(r"[a-z]{2,3}", db):
        raise ValueError("La base régionale Semrush est invalide.")
    params = {
        "key": key,
        "type": "domain_ranks",
        "domain": hostname,
        "database": db,
        "export_columns": "Db,Dn,Rk,Or,Ot,Oc,Ad,At,Ac",
    }
    try:
        response = httpx.get("https://api.semrush.com/", params=params, timeout=TIMEOUT)
        response.raise_for_status()
        text = response.text.strip()
    except httpx.HTTPError as exc:
        raise SeoIntegrationError("Échec de la requête Semrush.") from exc
    if not text or text.upper().startswith("ERROR"):
        raise SeoIntegrationError("Semrush a renvoyé une erreur API ou aucun résultat.")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    return {
        "domain": hostname,
        "database": db,
        "columns": reader.fieldnames or [],
        "rows": rows[: max(1, min(int(max_rows), 20))],
    }
