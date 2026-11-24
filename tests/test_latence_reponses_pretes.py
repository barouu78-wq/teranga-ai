"""Mesurer l'indépendance de Teranga : la ligne de latence dit si la réponse était une réponse prête.

Décision du propriétaire du 19 octobre 2026 : Teranga répond seul aux questions qu'il sait déjà traiter (réponses
prêtes de services/quick_answers.py). Jusqu'ici, la ligne « latence » les comptait comme « cache=oui », mêlées aux
anciennes réponses du modèle gardées en cache : impossible de savoir combien de questions sont servies sans IA.
Le champ « pret=oui|non » les distingue ; scripts/lire_latence.py en fait un groupe à part.
"""

import io

import pytest

import latence_harness as h
from latence_harness import completed, delta, finish, post_chat
from scripts import lire_latence
from services.latency import format_line

READY_QUESTION = "Quel est le numéro de la police ?"  # numéros d'urgence vérifiés : réponse prête
MODEL_QUESTION = "Parle-moi de la culture sérère."  # le modèle répond, puis la réponse va au cache
# Même fausse réponse que tests/test_latence_routes.py (60 caractères au moins : sinon le cache ne la garde pas).
TEXT = "Prends un car depuis la gare routière de Pompiers, c'est le plus simple."
STREAM = [delta("Prends un car depuis "), delta("la gare routière de Pompiers, "), delta("c'est le plus simple."), completed(TEXT)]


@pytest.fixture
def lines():
    handler = h.capture_lines()
    yield handler.lines
    h.release_lines(handler)


def test_a_ready_answer_is_marked_ready_and_calls_no_provider(monkeypatch, lines):
    provider = h.install_provider(monkeypatch, events=STREAM)
    finish(post_chat(READY_QUESTION))
    (line,) = lines
    f = h.fields(line)
    assert f["pret"] == "oui" and f["cache"] == "oui" and f["statut"] == "ok"
    assert provider.calls == []


def test_a_model_answer_then_its_cached_copy_are_not_marked_ready(monkeypatch, lines):
    provider = h.install_provider(monkeypatch, events=STREAM)
    finish(post_chat(MODEL_QUESTION))
    finish(post_chat(MODEL_QUESTION))
    first, second = (h.fields(line) for line in lines)
    assert (first["cache"], first["pret"]) == ("non", "non")
    assert (second["cache"], second["pret"]) == ("oui", "non")
    assert provider.calls == [True]


def test_the_ready_field_only_takes_yes_no_or_dash():
    base = {"total_ms": 5, "statut": "ok"}
    assert " pret=oui " in format_line("chat", {**base, "pret": True})
    assert " pret=non " in format_line("chat", {**base, "pret": False})
    assert " pret=- " in format_line("chat", base)
    assert " pret=- " in format_line("chat", {**base, "pret": "Quel est le numéro ?"})


def _summary(text):
    return {group["groupe"]: group for group in lire_latence.summarize(lire_latence.read_records(io.StringIO(text)))}


def test_the_log_reader_counts_ready_answers_apart():
    groups = _summary(
        "latence route=chat total_ms=8.0 contexte_ms=2.0 recherche_ms=- premier_mot_ms=3.0 fournisseur_ms=- "
        "cache=oui pret=oui web=- modele=- mode=flux statut=ok\n"
        "latence route=chat total_ms=30.0 contexte_ms=2.0 recherche_ms=- premier_mot_ms=9.0 fournisseur_ms=- "
        "cache=oui pret=non web=- modele=- mode=flux statut=ok\n"
        "latence route=chat total_ms=2000.0 contexte_ms=9.0 recherche_ms=- premier_mot_ms=1500.0 fournisseur_ms=1400.0 "
        "cache=non pret=non web=non modele=m mode=flux statut=ok\n"
    )
    assert set(groups) == {"chat, réponse prête", "chat, cache=oui", "chat, cache=non"}


def test_older_lines_without_the_ready_field_keep_their_group():
    groups = _summary(
        "latence route=chat total_ms=35.0 contexte_ms=9.0 recherche_ms=- premier_mot_ms=8.0 fournisseur_ms=- "
        "cache=oui web=non modele=- mode=flux statut=ok\n"
    )
    assert set(groups) == {"chat, cache=oui"}
