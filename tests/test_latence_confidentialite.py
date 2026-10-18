"""Confidentialité des lignes de latence : jamais le texte d'un visiteur, d'une réponse, une adresse IP ou une clé.

Le test fait passer par la vraie application des textes de test faciles à repérer (question, réponse du fournisseur,
transcription, texte lu, message d'erreur du fournisseur, adresse IP, cookie de visiteur, clé de recherche) sur
/chat (flux, JSON, cache, secours, erreur), /stt et /tts, puis lit TOUTES les lignes produites. Il échoue si l'un de
ces textes y apparaît, ou si une ligne sort de la grammaire fixe (clés connues, nombres ou étiquettes fixes).
"""

import itertools
import re

import pytest

import latence_harness as h
from latence_harness import completed, delta, finish, full, post_chat
from services.latency import LatencyTrace, format_line

QUESTION = "Zorglub-QUESTION-7391 : où dormir à Dakar ?"
ANSWER = "Zorglub-REPONSE-4417 : dormez à la Médina, c'est calme et près de tout ce qu'il faut voir."
TRANSCRIPTION = "Zorglub-TRANSCRIPTION-5520"
SPOKEN = "Zorglub-LECTURE-6603 bonjour"
VOICE_CONTEXT = "Zorglub-CONTEXTE-VOCAL-9042"
PROVIDER_ERROR = "clé sk-Zorglub-CLE-8801 refusée pour 203.0.113.77 (Zorglub-ERREUR-3318)"
IP_PREFIX = "203.0.113."  # une adresse par exécution (les limites de débit ne se mélangent pas) ; le préfixe est interdit
_IPS = itertools.count(1)
VISITOR = "Zorglub-VISITEUR-identifiant-2025-abcdef"
SEARCH_KEY = "tvly-Zorglub-CLE-RECHERCHE-1234"
SECRETS = (
    "Zorglub", QUESTION, ANSWER, TRANSCRIPTION, SPOKEN, VOICE_CONTEXT, PROVIDER_ERROR, VISITOR, SEARCH_KEY,
    "sk-", "tvly-", IP_PREFIX, "192.0.2.",
)

MS = r"(?:\d+\.\d|-)"
GRAMMAR = {
    "chat": re.compile(
        rf"latence route=chat total_ms={MS} contexte_ms={MS} recherche_ms={MS} premier_mot_ms={MS} fournisseur_ms={MS} "
        r"cache=(?:oui|non|-) web=(?:oui|non|-) modele=(?:[A-Za-z0-9][A-Za-z0-9._:-]{0,47}|-) mode=(?:flux|json|-) "
        r"statut=(?:ok|secours|erreur|abandon|refuse|invalide)"
    ),
    "voix": re.compile(
        rf"latence route=(?:stt total_ms={MS}|tts total_ms={MS} premier_mot_ms={MS}) fournisseur_ms={MS} modele=(?:[A-Za-z0-9][A-Za-z0-9._:-]{{0,47}}|-) "
        r"statut=(?:ok|secours|erreur|abandon|refuse|invalide)"
    ),
}


def leaks(lines, secrets=SECRETS):
    """Textes interdits retrouvés dans les lignes (liste vide = rien ne fuit)."""
    return [(secret, line) for line in lines for secret in secrets if secret.lower() in line.lower()]


def off_grammar(lines):
    return [line for line in lines if not (GRAMMAR["chat"].fullmatch(line) or GRAMMAR["voix"].fullmatch(line))]


@pytest.fixture
def lines():
    handler = h.capture_lines()
    yield handler.lines
    h.release_lines(handler)


def run_everything(monkeypatch):
    """Toutes les formes de requête, avec les textes secrets dans la question, la réponse, les erreurs, l'IP et le cookie."""
    from services import external_research

    monkeypatch.setenv("TAVILY_API_KEY", SEARCH_KEY)
    monkeypatch.setattr(external_research, "_engine_context", lambda name, query: {
        "provider": name, "context": f"Contexte web {ANSWER}", "sources": [{"title": ANSWER, "url": "https://exemple.sn/x"}],
    })
    stream = [delta(ANSWER[:30]), delta(ANSWER[30:]), completed(ANSWER)]
    runs = 0
    ip = IP_PREFIX + str(next(_IPS) + 100)
    # 1. flux normal, puis la même question : réponse du cache
    h.install_provider(monkeypatch, events=stream)
    for _ in range(2):
        finish(post_chat(QUESTION, ip=ip, identity=VISITOR))
        runs += 1
    # 2. mode JSON, puis cache
    h.install_provider(monkeypatch, full_reply=full(ANSWER))
    for _ in range(2):
        finish(post_chat(QUESTION + " (json)", ip=ip, identity=VISITOR, json_mode=True))
        runs += 1
    # 3. question avec recherche externe (texte de la question dans le contexte envoyé au modèle)
    h.install_provider(monkeypatch, events=stream)
    finish(post_chat("Quel est le prix actuel du ticket : " + QUESTION, ip=ip, identity=VISITOR))
    runs += 1
    # 4. le fournisseur échoue avec un message qui contient une clé, l'IP et du texte : secours, flux et JSON
    h.install_provider(monkeypatch, error=PROVIDER_ERROR)
    finish(post_chat(QUESTION + " (secours)", ip=ip, identity=VISITOR))
    finish(post_chat(QUESTION + " (secours json)", ip=ip, identity=VISITOR, json_mode=True))
    runs += 2
    # 5. refus : message vide (400), limite de débit (429)
    finish(post_chat("   ", ip=ip, identity=VISITOR))
    runs += 1
    h.install_provider(monkeypatch, events=stream)
    limited_ip = h.next_ip()
    for _ in range(h.app_module.RATE_LIMIT + 2):
        finish(post_chat(QUESTION + " (débit)", ip=limited_ip, identity=VISITOR))
        runs += 1
    # 6. flux fermé par le visiteur
    response = post_chat(QUESTION + " (abandon)", ip=ip, identity=VISITOR)
    next(response.response)
    response.close()
    runs += 1
    # 7. voix : succès, panne du fournisseur (message d'erreur secret), audio absent
    h.post_stt(text=TRANSCRIPTION, context=VOICE_CONTEXT, ip=ip, monkeypatch=monkeypatch).close()
    h.post_stt(error=PROVIDER_ERROR, context=VOICE_CONTEXT, ip=ip, monkeypatch=monkeypatch).close()
    h.post_stt(audio=None, ip=ip, monkeypatch=monkeypatch).close()
    h.post_tts(SPOKEN, ip=ip, monkeypatch=monkeypatch).close()
    h.post_tts(SPOKEN, error=PROVIDER_ERROR, ip=ip, monkeypatch=monkeypatch).close()
    runs += 5
    return runs


def test_no_user_text_ip_cookie_or_key_ever_reaches_a_latency_line(monkeypatch, lines, capsys):
    expected = run_everything(monkeypatch)
    assert len(lines) == expected  # une ligne, et une seule, par requête
    assert leaks(lines) == []
    assert off_grammar(lines) == []
    # Ce qui part réellement sur la sortie standard (Render) est exactement ces lignes, rien d'autre.
    printed = [line for line in capsys.readouterr().out.splitlines() if line.startswith("latence ")]
    assert printed == lines


def test_every_status_and_route_was_actually_exercised(monkeypatch, lines):
    run_everything(monkeypatch)
    seen = {(h.fields(line)["route"], h.fields(line)["statut"]) for line in lines}
    for wanted in (
        ("chat", "ok"), ("chat", "secours"), ("chat", "refuse"), ("chat", "invalide"), ("chat", "abandon"),
        ("stt", "ok"), ("stt", "erreur"), ("stt", "invalide"), ("tts", "ok"), ("tts", "erreur"),
    ):
        assert wanted in seen, (wanted, sorted(seen))
    caches = {h.fields(line).get("cache") for line in lines if line.startswith("latence route=chat")}
    assert {"oui", "non"} <= caches  # un test qui ne verrait que des « non » ne prouverait rien sur le cache


# --- Le détecteur lui-même doit mordre ---------------------------------------------------------------------


def test_the_detector_catches_a_leaked_question_ip_or_key():
    ip = IP_PREFIX + "77"
    clean = "latence route=chat total_ms=12.0 contexte_ms=3.0 recherche_ms=- premier_mot_ms=9.0 fournisseur_ms=5.0 cache=non web=non modele=m mode=flux statut=ok"
    assert leaks([clean]) == [] and off_grammar([clean]) == []
    for leaking in (clean + " q=" + QUESTION, clean + " ip=" + ip, clean + " cle=" + SEARCH_KEY, clean.replace("modele=m", "modele=" + ANSWER)):
        assert leaks([leaking]) != [] or off_grammar([leaking]) != []
    assert off_grammar([clean + " visiteur=abc"]) != []  # une clé inconnue sort de la grammaire
    assert off_grammar([clean.replace("statut=ok", "statut=Zorglub")]) != []


def test_the_formatter_cannot_be_made_to_print_a_secret_even_when_a_route_tries():
    from services.latency import LatencyTrace

    trace = LatencyTrace("chat")
    trace.model = QUESTION  # une route qui se tromperait de variable
    trace.mode = ANSWER
    trace.status = PROVIDER_ERROR
    trace.cache = QUESTION
    trace.web = IP_PREFIX + "77"
    line = format_line(trace.route, trace.values())
    assert leaks([line]) == [] and off_grammar([line]) == []


def test_a_regression_that_logs_the_question_would_make_this_file_fail(monkeypatch, lines):
    """Simule le défaut à éviter (une route qui ajouterait la question à la ligne) : la détection doit le voir."""
    from flask import request

    from services import latency

    current = {}
    original_run = LatencyTrace.run
    original_format = latency.format_line

    def leaky_run(self, app, handler):
        current["q"] = (request.get_json(silent=True) or {}).get("message", "")
        return original_run(self, app, handler)

    monkeypatch.setattr(LatencyTrace, "run", leaky_run)
    monkeypatch.setattr(latency, "format_line", lambda route, values: original_format(route, values) + " q=" + current["q"])
    h.install_provider(monkeypatch, events=[delta(ANSWER), completed(ANSWER)])
    finish(post_chat(QUESTION))
    assert len(lines) == 1
    assert leaks(lines) != [] and off_grammar(lines) != []
