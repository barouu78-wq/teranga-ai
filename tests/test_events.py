"""Calendrier des fêtes : seulement l'à-venir, dates estimées signalées, contexte du chat."""

import datetime as dt
import json
import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from routes.events import render_events_page  # noqa: E402
from services.events import EVENTS, events_context, upcoming_events  # noqa: E402

B = "https://teranga-ai.fr"


def test_only_current_and_future_events_are_listed():
    events = upcoming_events(dt.date(2027, 5, 5))
    assert events[0]["name"] == "Festival international de jazz de Saint-Louis"  # en cours
    assert events[0]["days_left"] < 0
    assert all((e["end"] or e["start"]) >= dt.date(2027, 5, 5) for e in events)


def test_lunar_dates_are_marked_as_estimates():
    page = render_events_page(B, dt.date(2026, 10, 6))
    assert "Tabaski" in page and "date estimée" in page
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        data = json.loads(block)
        assert data["itemListElement"][0]["item"]["startDate"] >= "2026-10-06"
    assert "[estimée, à confirmer]" in events_context(dt.date(2027, 1, 2))


def test_every_event_has_tips_and_a_valid_range():
    for start, end, name, place, kind, confirmed, tips in EVENTS:
        assert name and place and tips and kind
        assert end is None or end >= start


def test_page_is_served_and_in_the_sitemap():
    from app import app

    client = app.test_client()
    assert client.get("/calendrier-fetes-senegal", base_url=B).status_code == 200
    assert "/calendrier-fetes-senegal" in client.get("/sitemap.xml", base_url=B).get_data(as_text=True)


def test_events_context_adds_a_named_far_event():
    import datetime as dt
    from services.events import events_context
    today = dt.date(2026, 10, 7)
    assert "Tabaski" not in events_context(today)
    assert "Tabaski (Aïd el-Kébir)" in events_context(today, query="C'est quand la Tabaski ?")
    assert "Tabaski (Aïd el-Kébir)" in events_context(today, query="La fête du mouton c'est quand ?")
    assert "jazz" in events_context(today, query="When is the Saint-Louis jazz festival?")



def test_event_words_cover_english_and_other_names():
    from app import _EVENT_WORDS
    for question in ("When is Senegal's Independence Day?", "Date du Mouloud", "When is Ashura?", "Assumption day"):
        assert _EVENT_WORDS.search(question), question
