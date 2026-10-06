"""Page « Calendrier des fêtes et événements au Sénégal »."""

from __future__ import annotations

import datetime as _dt
import json
from html import escape
from urllib.parse import quote

from flask import Response

from services.events import TYPE_LABELS, french_date, upcoming_events
from services.site_layout import HEAD_ASSETS, site_footer, site_header

TITLE = "Fêtes au Sénégal : Magal, Tabaski, Korité, Gamou | Teranga AI"
DESCRIPTION = (
    "Calendrier des fêtes et événements au Sénégal : Magal de Touba, Tabaski, Korité, Gamou, 4 avril, "
    "jazz de Saint-Louis. Dates et conseils pratiques."
)


def render_events_page(site_url: str, today: _dt.date | None = None) -> str:
    events = upcoming_events(today)
    cards = []
    for event in events:
        when = french_date(event["start"]) + (f" → {french_date(event['end'])}" if event["end"] else "")
        status = "" if event["confirmed"] else ' <span class="badge">date estimée</span>'
        soon = ""
        if event["days_left"] <= 0:
            soon = '<p><strong>En ce moment</strong></p>'
        elif event["days_left"] <= 30:
            soon = f'<p><strong>Dans {event["days_left"]} jour(s)</strong></p>'
        question = quote(f"Je voyage au Sénégal pendant {event['name']} : quels conseils pratiques ?")
        cards.append(
            f'<div class="card"><small>{escape(TYPE_LABELS.get(event["kind"], ""))} · {escape(event["place"])}</small>'
            f"<h3>{escape(event['name'])}</h3><p>📅 {escape(when)}{status}</p>{soon}"
            f"<p>{escape(event['tips'])}</p>"
            f'<p><a href="/?q={question}">Demander à Teranga AI</a></p></div>'
        )
    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Fêtes et événements au Sénégal",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "Event",
                    "name": event["name"],
                    "startDate": event["start"].isoformat(),
                    "endDate": (event["end"] or event["start"]).isoformat(),
                    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                    "eventStatus": "https://schema.org/EventScheduled",
                    "location": {"@type": "Place", "name": event["place"], "address": {"@type": "PostalAddress", "addressCountry": "SN"}},
                    "description": event["tips"],
                },
            }
            for i, event in enumerate(events)
        ],
    }
    body = "".join(cards) or '<p class="muted">Le calendrier sera bientôt mis à jour.</p>'
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(TITLE)}</title>
<meta name="description" content="{escape(DESCRIPTION)}">
<link rel="canonical" href="{escape(site_url.rstrip('/'))}/calendrier-fetes-senegal">
<meta name="robots" content="index,follow">{HEAD_ASSETS}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>
<body>{site_header()}<main><article><div class="kicker">Calendrier</div>
<h1>Fêtes et événements au Sénégal</h1>
<p class="intro">Les grandes fêtes changent le rythme du pays : transports pleins, villes qui se vident ou se remplissent, bureaux fermés. Voici les prochaines dates et les bons réflexes.</p>
<section><div class="grid">{body}</div></section>
<p class="muted">Les fêtes musulmanes suivent le calendrier lunaire : les dates marquées « estimée » sont confirmées quelques jours avant par la commission nationale du croissant lunaire ou les familles religieuses.</p>
</article></main>{site_footer()}</body></html>"""


def register_events_routes(app, site_url: str) -> None:
    @app.get("/calendrier-fetes-senegal")
    def events_page():
        return Response(render_events_page(site_url), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})
