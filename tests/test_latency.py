"""Mesure de latence (services/latency.py) : format de la ligne, chronomètres, confidentialité, journal dédié.

Aucun appel réseau. Les durées exactes viennent d'une horloge simulée ; les tests de route (avec un faux fournisseur)
sont dans test_latence_routes.py.
"""

import logging
import re

import pytest
from flask import Flask, jsonify

from services import latency
from services.latency import LatencyTrace, format_line, status_from_http


class FakeClock:
    """Horloge manuelle : `tick(ms)` avance le temps, rien d'autre."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def tick(self, ms):
        self.now += ms / 1000


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


@pytest.fixture
def lines():
    handler = Capture()
    logger = latency.get_logger()
    logger.addHandler(handler)
    yield handler.lines
    logger.removeHandler(handler)


# --- Format -----------------------------------------------------------------------------------------------


def test_chat_line_has_a_stable_layout():
    line = format_line("chat", {
        "total_ms": 2310.44, "contexte_ms": 12.8, "recherche_ms": None, "premier_mot_ms": 1480.25,
        "fournisseur_ms": 1410.9, "cache": False, "web": True, "modele": "gpt-5.6-luna", "mode": "flux", "statut": "ok",
    })
    assert line == (
        "latence route=chat total_ms=2310.4 contexte_ms=12.8 recherche_ms=- premier_mot_ms=1480.2 "
        "fournisseur_ms=1410.9 cache=non web=oui modele=gpt-5.6-luna mode=flux statut=ok"
    )


def test_voice_line_is_shorter_and_keeps_the_same_keys():
    line = format_line("stt", {"total_ms": 950.1, "fournisseur_ms": 902.6, "modele": "gpt-4o-transcribe", "statut": "ok"})
    assert line == "latence route=stt total_ms=950.1 fournisseur_ms=902.6 modele=gpt-4o-transcribe statut=ok"
    assert format_line("tts", {"total_ms": 1}).startswith("latence route=tts total_ms=1.0 fournisseur_ms=- modele=- statut=")


def test_a_missing_value_is_a_dash_and_a_cache_hit_is_oui():
    line = format_line("chat", {"total_ms": 5, "cache": True, "statut": "ok"})
    assert "recherche_ms=- " in line and "premier_mot_ms=- " in line and "cache=oui" in line and "modele=- " in line


def test_every_value_is_neutralised_so_free_text_cannot_reach_the_line():
    hostile = "Quelle est ma question secrète ? clé=sk-123 ip=203.0.113.9"
    line = format_line("chat", {
        "total_ms": hostile, "contexte_ms": hostile, "recherche_ms": [hostile], "premier_mot_ms": float("nan"),
        "fournisseur_ms": float("inf"), "cache": hostile, "web": hostile, "modele": hostile, "mode": hostile, "statut": hostile,
        "message": hostile, "ip": hostile,  # clés inconnues : ignorées
    })
    assert line == (
        "latence route=chat total_ms=- contexte_ms=- recherche_ms=- premier_mot_ms=- fournisseur_ms=- "
        "cache=- web=- modele=autre mode=- statut=erreur"
    )
    assert "secrète" not in line and "sk-" not in line and "203.0.113.9" not in line


def test_unknown_route_is_labelled_autre_and_loses_everything_else():
    assert format_line("/chat?q=secret", {"total_ms": 3, "statut": "ok", "modele": "m"}) == "latence route=autre total_ms=3.0 statut=ok"


def test_negative_durations_are_clamped_and_booleans_are_not_numbers():
    assert format_line("tts", {"total_ms": -4, "fournisseur_ms": True}).startswith("latence route=tts total_ms=0.0 fournisseur_ms=-")


@pytest.mark.parametrize("code, expected", [
    (200, "ok"), (204, "ok"), (302, "ok"), (400, "invalide"), (403, "invalide"), (404, "invalide"),
    (429, "refuse"), (500, "erreur"), (502, "erreur"), (503, "erreur"), (None, "erreur"), ("x", "erreur"),
])
def test_status_is_deduced_from_the_http_code(code, expected):
    assert status_from_http(code) == expected


# --- Chronomètres -----------------------------------------------------------------------------------------


def make(route="chat"):
    clock = FakeClock()
    return LatencyTrace(route, clock=clock), clock


def test_stages_are_measured_and_accumulated(lines):
    trace, clock = make()
    with trace.stage("contexte"):
        clock.tick(12)
    with trace.stage("recherche"):
        clock.tick(30)
    with trace.stage("recherche"):
        clock.tick(20)
    clock.tick(8)
    trace.status = "ok"
    trace.emit()
    assert lines == ["latence route=chat total_ms=70.0 contexte_ms=12.0 recherche_ms=50.0 premier_mot_ms=- fournisseur_ms=- cache=- web=- modele=- mode=- statut=ok"]


def test_a_failing_stage_is_still_measured_and_the_exception_is_not_swallowed():
    trace, clock = make()
    with pytest.raises(ValueError):
        with trace.stage("recherche"):
            clock.tick(25)
            raise ValueError("panne")
    assert trace.values()["recherche_ms"] == pytest.approx(25)


def test_first_word_is_counted_once_and_stops_the_provider_timer(lines):
    trace, clock = make()
    with trace.stage("contexte"):
        clock.tick(10)
    clock.tick(5)
    trace.begin("fournisseur")
    clock.tick(400)
    trace.first_word()
    clock.tick(600)
    trace.first_word()  # les mots suivants ne comptent pas
    trace.end("fournisseur")  # déjà arrêté : sans effet
    trace.status, trace.model, trace.cache, trace.mode = "ok", "gpt-5.6-luna", False, "flux"
    trace.emit()
    assert lines == [
        "latence route=chat total_ms=1015.0 contexte_ms=10.0 recherche_ms=- premier_mot_ms=415.0 "
        "fournisseur_ms=400.0 cache=non web=- modele=gpt-5.6-luna mode=flux statut=ok"
    ]


def test_first_sound_of_the_voice_is_counted_once_and_written_at_the_end_of_the_tts_line(lines):
    """/tts en flux : premier_son_ms (premier octet de son envoyé) et le mode, ajoutés APRÈS statut : les lectures
    qui s'arrêtent à statut (scripts, recherches dans les journaux) restent justes."""
    trace, clock = make("tts")
    trace.begin("fournisseur")
    clock.tick(800)
    trace.first_sound()
    clock.tick(4000)
    trace.first_sound()  # les morceaux suivants ne comptent pas
    trace.status, trace.model, trace.mode = "ok", "gpt-4o-mini-tts", "flux"
    trace.emit()
    assert lines == [
        "latence route=tts total_ms=4800.0 fournisseur_ms=800.0 modele=gpt-4o-mini-tts statut=ok premier_son_ms=800.0 mode=flux"
    ]
    assert format_line("tts", {"total_ms": 9, "mode": "fichier", "statut": "ok"}).endswith("statut=ok premier_son_ms=- mode=fichier")
    assert format_line("tts", {"total_ms": 9, "mode": "secret"}).endswith("mode=-")
    assert format_line("stt", {"total_ms": 9, "statut": "ok"}) == "latence route=stt total_ms=9.0 fournisseur_ms=- modele=- statut=ok"


def test_end_without_begin_does_nothing():
    trace, _ = make()
    trace.end("fournisseur")
    assert trace.values()["fournisseur_ms"] is None


def test_the_line_is_written_once_even_if_emit_is_called_twice(lines):
    trace, _ = make("tts")
    trace.emit()
    trace.emit()
    assert len(lines) == 1


def test_a_broken_logger_never_breaks_the_request(monkeypatch):
    trace, _ = make()

    def boom():
        raise RuntimeError("journal indisponible")

    monkeypatch.setattr(latency, "get_logger", boom)
    trace.emit()  # ne lève rien


# --- Statut -----------------------------------------------------------------------------------------------


def test_a_stream_closed_before_its_end_is_an_abandon():
    trace, _ = make()
    trace._streamed = True
    assert trace.values()["statut"] == "abandon"


def test_an_explicit_status_wins_over_the_http_code():
    trace, _ = make()
    trace._http_status = 200
    trace.status = "secours"
    assert trace.values()["statut"] == "secours"


# --- Intégration Flask : run / follow ---------------------------------------------------------------------


def mini_app():
    app = Flask(__name__)

    @app.get("/ok")
    def ok():
        return LatencyTrace("tts").run(app, lambda trace: jsonify({"a": 1}))

    @app.get("/tuple")
    def tup():
        return LatencyTrace("tts").run(app, lambda trace: (jsonify({"error": "x"}), 429, {"Retry-After": "8"}))

    @app.get("/boom")
    def boom():
        def body(trace):
            raise RuntimeError("secret-que-le-journal-ne-doit-pas-voir")

        return LatencyTrace("tts").run(app, body)

    @app.get("/stream")
    def stream():
        def body(trace):
            def gen():
                yield "a"
                trace.status = "ok"
                yield "b"

            from flask import Response

            return Response(gen())

        return LatencyTrace("tts").run(app, body)

    return app


def test_run_returns_the_same_response_and_writes_the_line_on_close(lines):
    client = mini_app().test_client()
    response = client.get("/ok")
    assert response.get_json() == {"a": 1}
    assert lines == []  # la ligne part à la fermeture de la réponse, comme le fait le serveur WSGI
    response.close()
    assert len(lines) == 1 and lines[0].endswith("statut=ok")


def test_run_keeps_tuple_status_and_headers(lines):
    response = mini_app().test_client().get("/tuple")
    assert response.status_code == 429 and response.headers["Retry-After"] == "8"
    response.close()
    assert lines[0].endswith("statut=refuse")


def test_an_exception_is_relaunched_and_logged_without_its_message(lines):
    app = mini_app()
    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = app.test_client().get("/boom")
    response.close()
    assert response.status_code == 500
    assert len(lines) == 1 and lines[0].endswith("statut=erreur") and "secret" not in lines[0]


def test_a_stream_read_to_the_end_is_ok_and_one_closed_early_is_an_abandon(lines):
    client = mini_app().test_client()
    full = client.get("/stream")
    assert full.get_data() == b"ab"
    full.close()
    early = client.get("/stream")
    assert next(early.response) == b"a"
    early.close()
    assert [line.rsplit(" ", 1)[1] for line in lines] == ["statut=ok", "statut=abandon"]


# --- Journal dédié ----------------------------------------------------------------------------------------


def test_the_lines_reach_standard_output_even_though_the_root_logger_only_shows_warnings(capsys):
    """Sous Gunicorn, `app.logger.info` est muet (niveau WARNING) : ce journal dédié doit, lui, sortir."""
    logger = latency.get_logger()
    assert logger.level == logging.INFO and logger.propagate is False
    trace, clock = make("stt")
    clock.tick(7)
    trace.status = "ok"
    trace.emit()
    out = capsys.readouterr().out
    assert out == "latence route=stt total_ms=7.0 fournisseur_ms=- modele=- statut=ok\n"


def test_the_logger_is_configured_only_once():
    first = latency.get_logger()
    count = len(first.handlers)
    assert latency.get_logger() is first and len(first.handlers) == count


def test_line_prefix_is_easy_to_filter():
    assert re.fullmatch(r"latence route=\w+( \w+=\S+)+", format_line("chat", {"total_ms": 1, "statut": "ok"}))
