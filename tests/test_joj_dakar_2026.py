"""JOJ Dakar 2026 mis en avant (demande du propriétaire du 31 octobre 2026, « Go » pour une ambiance « spécial JOJ »
sans logo officiel).

Faits tirés des pages officielles olympics.com (rubrique Dakar 2026) : dates du 31 octobre au 13 novembre 2026, trois
sites (Dakar, Diamniadio, Saly). Ni logo, ni anneaux, ni mascotte : ce sont des marques protégées du CIO, et Teranga
n'est pas un site officiel (la page le dit). Aucun prix ni horaire : billets et programme sur le site officiel.
"""

import datetime as dt
import os

import pytest

from services import quick_answers
from services.events import events_context, upcoming_events
from services.practical_facts import matching_topics, practical_context
from services.quick_answers import quick_answer

OFFICIAL = "https://www.olympics.com/en/dakar-2026"


def _app():
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    import app as app_module

    return app_module.app.test_client()


def test_the_games_are_in_the_calendar_for_their_whole_duration():
    for today in (dt.date(2026, 10, 31), dt.date(2026, 11, 13)):
        joj = [e for e in upcoming_events(today) if "JOJ" in e["name"]]
        assert joj, today
        assert joj[0]["start"] == dt.date(2026, 10, 31) and joj[0]["end"] == dt.date(2026, 11, 13)
        assert joj[0]["confirmed"] and "Diamniadio" in joj[0]["place"] and "Saly" in joj[0]["place"]
    assert not [e for e in upcoming_events(dt.date(2026, 11, 14)) if "JOJ" in e["name"]]


def test_the_ai_knows_the_dates_while_the_games_run():
    context = events_context(dt.date(2026, 11, 2), "Programme des JOJ ?")
    assert "JOJ" in context and "31 octobre 2026 au 13 novembre 2026" in context


@pytest.mark.parametrize("question", [
    "C'est quand les JOJ ?",
    "C'est quand les Jeux olympiques de la jeunesse ?",
    "JOJ Dakar 2026 c'est quand ?",
])
def test_when_are_the_games_gets_a_ready_answer(monkeypatch, question):
    monkeypatch.setattr(quick_answers, "_today", lambda: dt.date(2026, 10, 31))
    ready = quick_answer({"message": question, "language": "fr"}, {})
    assert ready is not None, question
    assert "31 octobre 2026" in ready["reply"] and "13 novembre 2026" in ready["reply"]


@pytest.mark.parametrize("question", [
    "Où ont lieu les JOJ ?",
    "Quels sports aux Jeux olympiques de la jeunesse à Saly ?",
    "Comment aller voir les JOJ à Diamniadio ?",
    "Dakar 2026 : où acheter des billets ?",
])
def test_games_questions_get_the_verified_venues(question):
    assert "joj" in matching_topics(question), question
    context = practical_context(question)
    assert "Diamniadio" in context and "Saly" in context and "site officiel olympics.com (rubrique Dakar 2026)" in context
    assert "n'est pas un site officiel" in context


def test_the_fallback_names_the_games_in_both_languages():
    """IA indisponible : la réponse de la base garde les repères vérifiés, sous un titre dans la langue du visiteur
    (relecture Codex sur #556). Comme pour tous les sujets, les repères eux-mêmes restent en français."""
    from services.fallback_answer import knowledge_fallback
    from services.senegal_knowledge import load_senegal_knowledge

    data = load_senegal_knowledge()
    today = dt.date(2026, 11, 2)
    english = knowledge_fallback("Where are the Youth Olympic Games?", data["places"], data["dishes"], "en", today=today)
    french = knowledge_fallback("Où ont lieu les JOJ ?", data["places"], data["dishes"], "fr", today=today)
    assert "Dakar 2026 Youth Olympic Games" in english and "Diamniadio" in english
    assert "JOJ Dakar 2026" in french and "Diamniadio" in french


@pytest.mark.parametrize("question", [
    "Cours de yoga à Dakar",
    "Le match de l'Olympique de Marseille",
    "Quelles fêtes à Dakar en 2026 ?",
    "Jouer au foot à Saly",
])
def test_no_false_trigger(question):
    assert "joj" not in matching_topics(question), question


def test_the_guide_page_is_served_with_the_official_link_and_the_notice():
    client = _app()
    page = client.get("/joj-dakar-2026", base_url="https://teranga-ai.fr")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "31 octobre au 13 novembre 2026" in html
    for site in ("Dakar", "Diamniadio", "Saly"):
        assert site in html
    assert OFFICIAL in html and "n'est pas un site officiel" in html
    assert "anneaux" not in html.lower()  # aucun emblème olympique décrit ou reproduit
    sitemap = client.get("/sitemap.xml", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert "https://teranga-ai.fr/joj-dakar-2026" in sitemap


def test_no_price_or_time_is_given_on_the_page():
    import re

    html = _app().get("/joj-dakar-2026", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert not re.search(r"\d\s*(fcfa|cfa|€|euros?)\b", html.lower())
    assert not re.search(r"\b\d{1,2}\s*h\s*\d{0,2}\b", html.lower())
