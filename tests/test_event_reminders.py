"""Rappels des fêtes : fichiers calendrier (.ics) gratuits, sans compte ni notification serveur."""

import datetime as dt
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from routes.events import render_events_page  # noqa: E402
from services.event_reminders import calendar_ics, event_slug, find_event  # noqa: E402
from services.events import upcoming_events  # noqa: E402

B = "https://teranga-ai.fr"
TODAY = dt.date(2026, 10, 17)
NOW = dt.datetime(2026, 10, 17, 9, 0, tzinfo=dt.timezone.utc)


def _unfold(text):
    return text.replace("\r\n ", "")


def _tabaski():
    return next(e for e in upcoming_events(TODAY) if e["name"].startswith("Tabaski"))


def test_slug_is_stable_and_url_safe():
    assert event_slug(_tabaski()) == "tabaski-aid-el-kebir-2027"
    jazz = next(e for e in upcoming_events(TODAY) if "jazz" in e["name"])
    assert event_slug(jazz) == "festival-international-de-jazz-de-saint-louis-2027"


def test_find_event_only_returns_upcoming_events():
    assert find_event("tabaski-aid-el-kebir-2027", TODAY)["name"].startswith("Tabaski")
    # Le Magal 2026 (2 août) est passé : plus de rappel.
    assert find_event("grand-magal-de-touba-2026", TODAY) is None
    assert find_event("../../etc/passwd", TODAY) is None


def test_estimated_date_is_said_in_the_title_and_description():
    ics = _unfold(calendar_ics([_tabaski()], B, NOW))
    assert "SUMMARY:Tabaski (Aïd el-Kébir) (date estimée)" in ics
    assert "DTSTART;VALUE=DATE:20270517" in ics
    assert "DTEND;VALUE=DATE:20270518" in ics
    assert "Date estimée" in ics and "à vérifier" in ics


def test_confirmed_event_has_no_estimate_mention_and_multi_day_end():
    jazz = next(e for e in upcoming_events(TODAY) if "jazz" in e["name"])
    ics = _unfold(calendar_ics([jazz], B, NOW))
    assert "date estimée" not in ics.lower()
    assert "DTSTART;VALUE=DATE:20270504" in ics
    # DTEND est exclusif : dernier jour (8 mai) + 1.
    assert "DTEND;VALUE=DATE:20270509" in ics


def test_two_reminders_at_9am_one_week_and_one_day_before():
    ics = calendar_ics([_tabaski()], B, NOW)
    assert ics.count("BEGIN:VALARM") == 2
    # Fête sans heure = minuit : -P6DT15H et -PT15H sonnent à 9 h, pas en pleine nuit.
    assert "TRIGGER:-P6DT15H" in ics and "TRIGGER:-PT15H" in ics


def test_slugs_are_unique_for_every_event():
    from services.events import EVENTS

    slugs = [event_slug({"name": e[2], "start": e[0]}) for e in EVENTS]
    assert len(slugs) == len(set(slugs))


def test_ics_is_valid_rfc5545():
    ics = calendar_ics(upcoming_events(TODAY), B, NOW)
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert "\n" not in ics.replace("\r\n", "")
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, line
    assert ics.count("BEGIN:VEVENT") == len(upcoming_events(TODAY))
    uids = [line for line in _unfold(ics).split("\r\n") if line.startswith("UID:")]
    assert len(uids) == len(set(uids))
    assert "DTSTAMP:20261017T090000Z" in ics


def test_text_is_escaped():
    event = dict(_tabaski(), tips="Prévoir ; virgule, et\nretour", place="A, B")
    ics = _unfold(calendar_ics([event], B, NOW))
    assert "Prévoir \\; virgule\\, et\\nretour" in ics
    assert "LOCATION:A\\, B\\, Sénégal" in ics


def test_routes_serve_calendar_files():
    from app import app

    client = app.test_client()
    # Fête à venir à la date réelle du test : le test ne vieillit pas.
    one = client.get(f"/calendrier-fetes-senegal/{event_slug(upcoming_events()[-1])}.ics", base_url=B)
    assert one.status_code == 200
    assert one.mimetype == "text/calendar"
    assert "attachment" in one.headers["Content-Disposition"]
    assert "BEGIN:VEVENT" in one.get_data(as_text=True)
    every = client.get("/calendrier-fetes-senegal.ics", base_url=B)
    assert every.status_code == 200 and every.mimetype == "text/calendar"
    assert client.get("/calendrier-fetes-senegal/inconnu-2027-01-01.ics", base_url=B).status_code == 404


def test_page_offers_a_reminder_per_event_and_for_all():
    page = render_events_page(B, TODAY)
    assert 'href="/calendrier-fetes-senegal/tabaski-aid-el-kebir-2027.ics"' in page
    assert 'href="/calendrier-fetes-senegal.ics"' in page
    assert "Me le rappeler" in page
    assert page.count('class="cta reminder"') == len(upcoming_events(TODAY))
