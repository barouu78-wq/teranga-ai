"""Planificateur en flux : signes de vie pendant la réflexion du modèle, erreurs claires."""

import json
import os
import threading
import time

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import services.trip_planner as tp  # noqa: E402

B = "https://teranga-ai.fr"
BODY = {"lang": "fr", "arrival": "2026-11-10", "departure": "2026-11-12", "adults": 2, "children": 0,
        "interests": [], "budget": "Confort", "pace": "Équilibré", "regions": ["Dakar"]}


class Ev:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _post(monkeypatch, stream_factory):
    from app import app

    monkeypatch.setattr(tp, "HEARTBEAT_SECONDS", 0.1)
    monkeypatch.setattr(tp, "_create", lambda client, stream=False, **kw: stream_factory())
    response = app.test_client().post("/api/trip-planner", json=BODY, headers={"Origin": B, "X-Teranga-Stream": "1"}, base_url=B)
    return [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]


class SlowModel:
    """Faux flux du modèle : lent, il compte ses lectures et note sa fermeture."""

    def __init__(self, pause=0.03, total=300):
        self.pause, self.total = pause, total
        self.reads = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.reads >= self.total:
            raise StopIteration
        time.sleep(self.pause)
        self.reads += 1
        return Ev(type="response.output_text.delta", delta=" ")

    def close(self):
        self.closed = True


def _reader_threads():
    return [t for t in threading.enumerate() if t.name == "trip-stream" and t.is_alive()]


def _wait_until(condition, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def _open_stream(monkeypatch, model, address):
    """Appel réel de la route, réponse lue au fil de l'eau (comme un navigateur)."""
    from app import app

    monkeypatch.setattr(tp, "HEARTBEAT_SECONDS", 0.1)
    monkeypatch.setattr(tp, "_create", lambda client, stream=False, **kw: model)
    return app.test_client().post(
        "/api/trip-planner", json=BODY, headers={"Origin": B, "X-Teranga-Stream": "1"}, base_url=B,
        environ_base={"REMOTE_ADDR": address}, buffered=False,
    )


def test_deadline_stops_reading_the_model(monkeypatch):
    """Après le délai, le fil de lecture s'arrête et le flux du modèle est fermé."""
    model = SlowModel()
    monkeypatch.setattr(tp, "STREAM_DEADLINE_SECONDS", 0.4)
    response = _open_stream(monkeypatch, model, "203.0.113.41")
    lines = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    assert lines[-1]["status"] == 504

    reads_at_deadline = model.reads
    assert _wait_until(lambda: not _reader_threads()), "le fil « trip-stream » est resté en vie après le délai"
    assert model.reads <= reads_at_deadline + 2, "le modèle a continué à être lu après le délai"
    assert model.reads < model.total
    assert model.closed


def test_browser_disconnect_stops_reading_the_model(monkeypatch):
    """Le navigateur part en cours de génération : plus aucune lecture, flux fermé."""
    model = SlowModel(pause=0.15)  # plus lent que les signes de vie (0,1 s) : des lignes arrivent
    response = _open_stream(monkeypatch, model, "203.0.113.42")
    chunks = iter(response.response)
    for _ in range(3):
        assert next(chunks)
    response.close()

    reads_at_disconnect = model.reads
    assert _wait_until(lambda: not _reader_threads()), "le fil « trip-stream » est resté en vie après la déconnexion"
    assert model.reads <= reads_at_disconnect + 2
    assert model.reads < model.total
    assert model.closed


class BlockedThenFailing(SlowModel):
    """Une lecture reste bloquée 0,6 s sur le réseau puis échoue : l'erreur arrive après le délai."""

    def __next__(self):
        if self.reads >= 1:
            time.sleep(0.6)
            raise RuntimeError("upstream timeout")
        self.reads += 1
        return Ev(type="response.created")  # rien d'écrit : le secours serait permis sans l'annulation


def test_no_backup_model_is_called_after_the_reader_left(monkeypatch):
    """Le flux casse après le délai : Claude (secours) ne doit pas être sollicité pour rien."""
    backup_calls = []
    monkeypatch.setattr(tp, "_backup_plan_text", lambda *a, **kw: backup_calls.append(1) or "plan de secours")
    monkeypatch.setattr(tp, "STREAM_DEADLINE_SECONDS", 0.3)
    response = _open_stream(monkeypatch, BlockedThenFailing(), "203.0.113.43")
    assert json.loads(response.get_data(as_text=True).splitlines()[-1])["status"] == 504

    assert _wait_until(lambda: not _reader_threads())
    assert backup_calls == []


def test_no_second_model_is_started_after_the_reader_left(monkeypatch):
    """Claude (IA principale) échoue après le départ du lecteur : OpenAI n'est pas relancé."""

    def claude_events(prompt, **kwargs):
        yield Ev(type="response.created")  # rien d'écrit : OpenAI prendrait le relais sans l'annulation
        time.sleep(0.6)
        raise RuntimeError("claude down")

    openai_model = SlowModel()
    monkeypatch.setattr(tp, "claude_is_primary", lambda: True)
    monkeypatch.setattr(tp, "claude_events", claude_events)
    monkeypatch.setattr(tp, "STREAM_DEADLINE_SECONDS", 0.3)
    response = _open_stream(monkeypatch, openai_model, "203.0.113.44")
    assert json.loads(response.get_data(as_text=True).splitlines()[-1])["status"] == 504

    assert _wait_until(lambda: not _reader_threads())
    assert openai_model.reads == 0, "OpenAI a été relancé alors que plus personne ne lisait"


def test_closing_the_event_reader_cancels_the_model_stream():
    model = SlowModel(pause=0.02)
    events = tp._events_with_heartbeat(lambda: model)
    assert next(events).type == "response.output_text.delta"
    events.close()

    assert _wait_until(lambda: not _reader_threads())
    reads = model.reads
    time.sleep(0.2)
    assert model.reads == reads, "le flux est encore lu après la fermeture"
    assert model.closed


def test_normal_stream_is_read_to_the_end_and_closed():
    model = SlowModel(pause=0.0, total=5)
    events = list(tp._events_with_heartbeat(lambda: model))
    assert len(events) == 5 and model.reads == 5
    assert _wait_until(lambda: not _reader_threads())
    assert model.closed


def test_stream_without_close_method_is_still_supported():
    """Un flux sans close() (liste, itérateur) se lit comme avant."""
    events = list(tp._events_with_heartbeat(lambda: iter([Ev(type="a"), Ev(type="b")])))
    assert [e.type for e in events] == ["a", "b"]


def test_upstream_error_is_still_raised_to_the_reader():
    def boom():
        yield Ev(type="response.output_text.delta", delta="x")
        raise RuntimeError("upstream down")

    events = tp._events_with_heartbeat(boom)
    assert next(events).delta == "x"
    try:
        next(events)
    except RuntimeError as exc:
        assert "upstream down" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("l'erreur du flux amont doit remonter")


def test_silent_model_still_sends_signs_of_life(monkeypatch):
    plan = json.dumps({"summary": "T", "days": [{"day": 1, "title": "J", "region": "Dakar"}, {"day": 2, "title": "K", "region": "Dakar"}]})

    def slow():
        time.sleep(0.45)
        yield Ev(type="response.output_text.delta", delta=plan)
        yield Ev(type="response.completed", response=Ev(output_text=plan))

    events = _post(monkeypatch, slow)
    assert sum(1 for e in events if e.get("progress", {}).get("day") == 0) >= 3
    assert events[-1].get("result")


def test_incomplete_answer_keeps_the_text_received(monkeypatch):
    plan = json.dumps({"summary": "T", "days": [{"day": 1, "title": "J", "region": "Dakar"}, {"day": 2, "title": "K", "region": "Dakar"}]})

    def cut():
        yield Ev(type="response.output_text.delta", delta=plan)
        yield Ev(type="response.incomplete", response=Ev(output_text=""))

    assert _post(monkeypatch, cut)[-1].get("result")


def test_model_failure_returns_a_readable_error(monkeypatch):
    def boom():
        raise RuntimeError("upstream down")
        yield  # pragma: no cover

    last = _post(monkeypatch, boom)[-1]
    assert last["status"] == 503 and "Réessaie" in last["error"]
