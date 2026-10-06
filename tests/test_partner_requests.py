"""Formulaire « Demander un partenariat » : envoi, validation et lecture dans la page privée."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.partner_requests import PartnerRequests  # noqa: E402

B = "https://teranga-ai.fr"


def _client(ip):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")

    def post(body, headers=None):
        return client.post("/api/partner-request", json=body, base_url=B, environ_base={"REMOTE_ADDR": ip},
                           headers={"X-CSRF-Token": token, "Origin": B, **(headers or {})})
    return client, post


def test_offers_page_shows_the_form():
    html = app_module.app.test_client().get("/offres-partenaires", base_url=B).get_data(as_text=True)
    assert 'id="partner-form"' in html and "partner-form.js" in html and 'name="website"' in html


def test_request_is_validated_stored_and_listed(monkeypatch):
    client, post = _client("203.0.113.81")
    assert post({"name": "Campement Test", "kind": "inconnu", "city": "Kafountine", "contact": "77 000 00 00"}).status_code == 400
    assert post({"name": "Campement Test", "kind": "hotel", "city": "Kafountine", "contact": "123"}).status_code == 400
    ok = post({"name": "Campement <Test>", "kind": "hotel", "city": "Kafountine", "contact": "+221 77 000 00 00", "message": "Bonjour\nnous"})
    assert ok.status_code == 200 and ok.get_json() == {"ok": True}
    monkeypatch.setenv("STATS_TOKEN", "x" * 20)
    page = client.post("/stats-partenaires", data={"cle": "x" * 20}, base_url=B,
                       environ_base={"REMOTE_ADDR": "203.0.113.82"}).get_data(as_text=True)
    assert "Campement &lt;Test&gt;" in page and "Kafountine" in page and "Bonjour nous" in page


def test_request_needs_csrf_and_ignores_bots():
    client, post = _client("203.0.113.83")
    denied = client.post("/api/partner-request", json={"name": "x"}, base_url=B, headers={"Origin": B},
                         environ_base={"REMOTE_ADDR": "203.0.113.83"})
    assert denied.status_code == 403
    before = len(PartnerRequests().recent())
    bot = post({"name": "Spam", "kind": "hotel", "city": "X", "contact": "770000000", "website": "http://spam"})
    assert bot.status_code == 200 and len(PartnerRequests().recent()) == before


def test_store_uses_redis_and_falls_back_to_memory():
    class FakePipe:
        def __init__(self, store):
            self.store, self.ops = store, []

        def lpush(self, key, raw):
            self.ops.append(raw)

        def ltrim(self, *a):
            pass

        def expire(self, *a):
            pass

        def execute(self):
            self.store[:0] = self.ops

    class FakeRedis:
        def __init__(self):
            self.items = []

        def pipeline(self, transaction=False):
            return FakePipe(self.items)

        def lrange(self, key, start, end):
            return self.items[start:end + 1]

    redis = FakeRedis()
    store = PartnerRequests(redis)
    store.add({"name": "A"})
    store.add({"name": "B"})
    assert [item["name"] for item in store.recent()] == ["B", "A"]

    class Broken:
        def pipeline(self, transaction=False):
            raise ConnectionError

        def lrange(self, *a):
            raise ConnectionError

    fallback = PartnerRequests(Broken())
    fallback.add({"name": "C"})
    assert [item["name"] for item in fallback.recent()] == ["C"]
