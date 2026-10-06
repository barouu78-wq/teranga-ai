"""Revenus : liens de réservation affiliés et adresses partenaires.

Rien ne s'affiche tant que les identifiants ne sont pas configurés :
- GETYOURGUIDE_PARTNER_ID : activités et excursions (commission GetYourGuide) ;
- BOOKING_AID : hébergements (commission Booking.com) ;
- TAXI_PARTNER_URL : appli de taxi / VTC partenaire (lien de parrainage ou
  d'affiliation en https, par exemple celui fourni par Sengo).

Les liens passent par /go/<type> : l'URL de destination est construite côté
serveur (jamais une adresse fournie par le visiteur, donc pas de redirection
ouverte) et chaque clic est compté dans les journaux, sans donnée personnelle.

Les adresses partenaires (data/partners.json) sont toujours présentées comme
« Partenaire » : sur les fiches lieux comme dans les réponses de l'IA.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import unicodedata
from html import escape
from pathlib import Path
from urllib.parse import urlencode

AFFILIATE_ENV = {
    "activites": "GETYOURGUIDE_PARTNER_ID",
    "hotels": "BOOKING_AID",
}
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_MAX_QUERY = 80


def affiliate_config(env=None) -> dict[str, str]:
    """Identifiants affiliés valides, par type de lien (« activites », « hotels »)."""
    env = os.environ if env is None else env
    config = {}
    for kind, name in AFFILIATE_ENV.items():
        value = str(env.get(name, "") or "").strip()
        if _ID_RE.match(value):
            config[kind] = value
    taxi = _safe_url(env.get("TAXI_PARTNER_URL", ""))
    if taxi:
        config["taxi"] = taxi
    return config


def clean_query(value: object) -> str:
    text = re.sub(r"[\x00-\x1f<>\"]", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()[:_MAX_QUERY]


def affiliate_target(kind: str, query: str, config: dict[str, str]) -> str | None:
    """URL du partenaire pour une recherche ; None si le type n'est pas configuré."""
    partner = config.get(kind)
    query = clean_query(query)
    if not partner or not query:
        return None
    if kind == "taxi":
        # Adresse fixe choisie par l'exploitant : la recherche ne sert qu'au comptage.
        return partner
    if kind == "activites":
        return "https://www.getyourguide.com/s/?" + urlencode({"q": query, "partner_id": partner})
    if kind == "hotels":
        return "https://www.booking.com/searchresults.html?" + urlencode({"ss": query, "aid": partner})
    return None


def _destination(place: dict) -> str:
    """Ce qu'on cherche chez le partenaire : la localité (hôtels) ou le lieu."""
    name = str(place.get("name", "")).split("/")[0].strip()
    locality = str(place.get("locality") or place.get("region") or "").strip()
    return name, locality


def booking_links(place: dict, config: dict[str, str], lang: str = "fr") -> list[dict]:
    """Liens « Réserver » d'un lieu, prêts à afficher (href interne /go/…)."""
    if not config:
        return []
    name, locality = _destination(place)
    en = lang == "en"
    links = []
    if "hotels" in config and (locality or name):
        where = f"{locality or name}, Sénégal"
        links.append({
            "kind": "hotels",
            "label": (f"🏨 Hotels near {locality or name}" if en else f"🏨 Hôtels à {locality or name}"),
            "href": "/go/hotels?" + urlencode({"q": where, "from": place.get("id", "")}),
        })
    if "activites" in config and name:
        links.append({
            "kind": "activites",
            "label": (f"🎟️ Tours: {name}" if en else f"🎟️ Visites et activités : {name}"),
            "href": "/go/activites?" + urlencode({"q": f"{name} Sénégal", "from": place.get("id", "")}),
        })
    if "taxi" in config and name:
        links.append({
            "kind": "taxi",
            "label": (f"🚕 Book a taxi to {name}" if en else f"🚕 Commander un taxi pour {name}"),
            "href": "/go/taxi?" + urlencode({"q": name, "from": place.get("id", "")}),
        })
    return links


DISCLOSURE = {
    "fr": "Liens partenaires : Teranga AI peut recevoir une commission, sans frais supplémentaires pour vous.",
    "en": "Partner links: Teranga AI may earn a commission at no extra cost to you.",
}


# --- Adresses partenaires -------------------------------------------------

def _fold(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def load_partners(path: Path | None = None) -> list[dict]:
    path = path or Path(__file__).resolve().parents[1] / "data" / "partners.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data.get("partners") if isinstance(data, dict) else None
    return [p for p in items or [] if isinstance(p, dict) and p.get("name") and p.get("id")]


def _is_active(partner: dict, today: _dt.date) -> bool:
    until = str(partner.get("until", "") or "")
    if not until:
        return True
    try:
        return _dt.date.fromisoformat(until) >= today
    except ValueError:
        return False


def partners_for_place(partners: list[dict], place: dict, today: _dt.date | None = None, limit: int = 3) -> list[dict]:
    """Partenaires actifs liés au lieu (id), à sa localité ou à sa région."""
    today = today or _dt.date.today()
    keys = {_fold(place.get("id")), _fold(place.get("locality")), _fold(place.get("region"))} - {""}
    found = []
    for partner in partners:
        targets = {_fold(t) for t in partner.get("places", []) or []}
        if _is_active(partner, today) and targets & keys:
            found.append(partner)
    # Le partenaire lié au lieu lui-même passe avant celui de la région.
    found.sort(key=lambda p: 0 if _fold(place.get("id")) in {_fold(t) for t in p.get("places", [])} else 1)
    return found[:limit]


def partners_for_text(partners: list[dict], text: str, today: _dt.date | None = None, limit: int = 3) -> list[dict]:
    """Partenaires dont un lieu desservi est cité dans la question."""
    today = today or _dt.date.today()
    value = " " + re.sub(r"[^a-z0-9]+", " ", _fold(text)) + " "
    found = []
    for partner in partners:
        if not _is_active(partner, today):
            continue
        for target in partner.get("places", []) or []:
            term = re.sub(r"[^a-z0-9]+", " ", _fold(target)).strip()
            if len(term) >= 4 and f" {term} " in value:
                found.append(partner)
                break
    return found[:limit]


def _safe_url(value: object) -> str:
    url = str(value or "").strip()
    return url if re.match(r"^https://[A-Za-z0-9.-]+(/[^\s\"<>]*)?$", url) else ""


def partners_html(partners: list[dict]) -> str:
    if not partners:
        return ""
    cards = []
    for p in partners:
        url = _safe_url(p.get("url"))
        title = escape(str(p["name"]))
        if url:
            title = f'<a href="{escape(url)}" target="_blank" rel="sponsored noopener">{title}</a>'
        phone = f'<br><small>📞 {escape(str(p["phone"]))}</small>' if p.get("phone") else ""
        cards.append(
            f'<div class="card"><span class="badge">Partenaire</span> <strong>{title}</strong>'
            f'<br><small>{escape(str(p.get("category", "")))}</small>'
            f'<p>{escape(str(p.get("description", ""))[:240])}</p>{phone}</div>'
        )
    return (
        "<section><h2>Adresses partenaires</h2>"
        f'<div class="grid">{"".join(cards)}</div>'
        '<p class="muted">Ces adresses sont des partenaires de Teranga AI. '
        '<a href="/offres-partenaires">Devenir partenaire</a></p></section>'
    )


def partners_context(partners: list[dict]) -> str:
    """Bloc pour l'IA : peut citer ces adresses, toujours comme partenaires."""
    if not partners:
        return ""
    lines = [
        "ADRESSES PARTENAIRES DE TERANGA AI (tu peux les proposer si elles répondent vraiment à la demande, "
        "en précisant toujours « partenaire de Teranga AI » ; ne les présente jamais comme un avis neutre "
        "et continue de citer d'autres options si c'est utile) :"
    ]
    for p in partners:
        lines.append(f"- {p['name']} ({p.get('category', '')}) : {p.get('description', '')}")
    return "\n".join(lines)


def booking_html(links: list[dict], lang: str = "fr") -> str:
    if not links:
        return ""
    anchors = "".join(
        f'<a class="cta" href="{escape(link["href"])}" rel="sponsored nofollow">{escape(link["label"])}</a>'
        for link in links
    )
    title = "Book" if lang == "en" else "Réserver"
    return f'<section><h2>{title}</h2><div class="actions">{anchors}</div><p class="muted">{escape(DISCLOSURE.get(lang, DISCLOSURE["fr"]))}</p></section>'

