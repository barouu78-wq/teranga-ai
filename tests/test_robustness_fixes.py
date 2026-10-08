"""Corrections issues de la relecture du code : erreurs 500, protections qui s'activent à tort, mentions trompeuses."""

import datetime as dt
import math
import os
import time

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services import weather  # noqa: E402
from services.partner_requests import PartnerRequests  # noqa: E402
from services.shared_answers import open_token, sign_answer  # noqa: E402
from services.youth_projects import _money_amount  # noqa: E402

B = "https://teranga-ai.fr"


def _post_client(ip):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    headers = {"X-CSRF-Token": token, "Origin": B}
    return client, headers, {"REMOTE_ADDR": ip}


def test_share_token_with_non_ascii_characters_is_refused_not_a_server_error():
    assert open_token("secret", "é.abc") is None and open_token("secret", "abc.é") is None
    good = sign_answer("secret", "Question", "Une réponse assez longue pour être partagée.", None, "fr")
    assert open_token("secret", good)["answer"].startswith("Une réponse")
    client = app_module.app.test_client()
    for token in ("é.abc", "abc.é", "a.b.c"):
        response = client.post("/api/share/open", json={"token": token}, base_url=B, headers={"Origin": B},
                               environ_base={"REMOTE_ADDR": "203.0.113.161"})
        assert response.status_code < 500, token


def test_report_endpoint_rejects_a_body_that_is_not_an_object():
    client, headers, env = _post_client("203.0.113.162")
    for body in ([1], "texte", 5):
        response = client.post("/api/report", json=body, base_url=B, headers=headers, environ_base=env)
        assert response.status_code == 400, body
    ok = client.post("/api/report", json={"reply": "Une réponse à signaler", "reason": "inappropriate"},
                     base_url=B, headers=headers, environ_base=env)
    assert ok.status_code == 200 and ok.get_json() == {"ok": True}


def test_money_amount_handles_infinity_decimals_and_millions():
    assert _money_amount(math.inf) is None and _money_amount(math.nan) is None and _money_amount(-5.0) is None
    assert _money_amount(1500000.0) == 1500000
    assert _money_amount("1 500 000 FCFA") == 1500000 and _money_amount("1.500.000") == 1500000
    assert _money_amount("2,5 millions") == 2500000 and _money_amount("1 million") == 1000000
    assert _money_amount("1,5") == 2 and _money_amount("pas de montant") is None


def test_image_proxy_rate_limit_does_not_lock_the_visitor_out_of_other_routes():
    ip = "203.0.113.163"
    client = app_module.app.test_client()
    codes = [client.get("/image-proxy?url=x", base_url=B, environ_base={"REMOTE_ADDR": ip}).status_code for _ in range(60)]
    assert 429 in codes  # la limite existe toujours
    # Mais elle ne bloque plus la même personne sur les autres routes (avant : 429 sur tout pendant 10 minutes).
    post_client, headers, env = _post_client(ip)
    other = post_client.post("/api/report", json={"reply": "Une réponse à signaler"}, base_url=B, headers=headers, environ_base=env)
    assert other.status_code == 200, other.get_data(as_text=True)


def test_partner_requests_older_than_a_year_are_dropped_even_when_new_ones_arrive():
    store = PartnerRequests()
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=401)
    store.add({"name": "Ancien"}, now=old)
    store.add({"name": "Récent"})
    names = [item["name"] for item in store.recent()]
    assert names == ["Récent"]


class _FakeRedis:
    def __init__(self):
        self.items = []

    def pipeline(self, transaction=False):
        return self

    def lpush(self, key, raw):
        self.items.insert(0, raw)
        return self

    def ltrim(self, key, start, end):
        self.items = self.items[start:end + 1]
        return self

    def expire(self, key, seconds):
        return self

    def execute(self):
        return []

    def lrange(self, key, start, end):
        end = len(self.items) if end == -1 else end + 1
        return self.items[start if start >= 0 else len(self.items) + start:end]

    def rpop(self, key):
        return self.items.pop() if self.items else None


def test_partner_requests_in_redis_drop_old_entries_when_a_new_one_is_added():
    redis = _FakeRedis()
    store = PartnerRequests(redis)
    store.add({"name": "Ancien"}, now=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=500))
    store.add({"name": "Récent"})
    assert [item["name"] for item in store.recent()] == ["Récent"]
    assert len(redis.items) == 1


def test_exchange_rates_say_so_when_the_bceao_page_could_not_be_read(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "_fx_cache", {"at": time.time(), "date": "", "rates": {"EUR": 655.957, "USD": 577.07, "GBP": 762.86}})
    data = client.get("/exchange-rates", base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.164"}).get_json()
    assert data["source"] == "indicatif" and data["live"] is False
    monkeypatch.setattr(app_module, "_fx_cache", {"at": time.time(), "date": "7 octobre 2026", "rates": {"EUR": 655.957}})
    data = client.get("/exchange-rates", base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.165"}).get_json()
    assert data["source"] == "BCEAO" and data["live"] is True


def _fake_forecast(monkeypatch):
    calls = []

    def fake(lat, lon, opener=None):
        calls.append((lat, lon))
        return {"current": {"time": "2026-10-08T12:00", "temperature_2m": 30, "apparent_temperature": 32, "weather_code": 1,
                            "wind_speed_10m": 10, "relative_humidity_2m": 60}, "daily": {}}

    monkeypatch.setattr(weather, "fetch_forecast", fake)
    return calls


def test_weather_for_a_city_outside_senegal_is_not_answered_with_dakar(monkeypatch):
    calls = _fake_forecast(monkeypatch)
    locations = {"dakar": ("Dakar", 14.69, -17.44), "saint-louis": ("Saint-Louis", 16.03, -16.5)}
    ctx = {"intent": "weather", "location": None}
    for question in ("Quelle est la météo à Paris aujourd'hui ?", "Quel temps fait-il à Abidjan ?", "What's the weather in London?"):
        assert weather.live_weather_context(locations, ctx, question, "fr") is None, question
    assert calls == []
    # Sans lieu nommé, ou avec un lieu du Sénégal, les prévisions restent données.
    for question in ("Quel temps fait-il ?", "Quel temps fait-il aujourd'hui ?", "Météo demain ?", "Météo à Saint-Louis demain"):
        assert "MÉTÉO EN DIRECT" in weather.live_weather_context(locations, ctx, question, "fr"), question
