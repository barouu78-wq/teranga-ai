"""Planificateur en flux : signes de vie pendant la réflexion du modèle, erreurs claires."""

import json
import os
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
