import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

DATA = json.loads((Path(__file__).resolve().parents[1] / "data" / "senegal_knowledge.json").read_text(encoding="utf-8"))


def test_every_region_has_at_least_one_place():
    regions = {region["name"] for region in DATA["regions"]}
    covered = {place["region"] for place in DATA["places"]}
    assert regions <= covered, sorted(regions - covered)


def test_places_are_complete_and_located_in_senegal():
    ids = set()
    for place in DATA["places"]:
        assert place["id"] not in ids
        ids.add(place["id"])
        for field in ("name", "type", "region", "summary", "what_to_see"):
            assert str(place.get(field, "")).strip(), (place["id"], field)
        # Boîte englobante du Sénégal.
        assert 12.2 <= place["latitude"] <= 16.8, place["id"]
        assert -17.6 <= place["longitude"] <= -11.3, place["id"]


def test_new_places_cite_their_sources():
    for place_id in (
        "desert-de-lompoul", "langue-de-barbarie", "marche-de-diaobe", "fort-pinet-laprade-sedhiou", "kaffrine",
        "kaolack", "mbacke", "reserve-de-fathala", "kafountine", "mlomp", "musee-theodore-monod", "manufactures-thies",
    ):
        place = next(p for p in DATA["places"] if p["id"] == place_id)
        assert place.get("sources"), place_id


def test_dindefello_is_in_kedougou_department():
    place = next(p for p in DATA["places"] if p["id"] == "dindefello")
    assert place["locality"] == "Kédougou"


def test_knowledge_ranks_the_named_place_first():
    from app import SENEGAL_KNOWLEDGE, SENEGAL_PEOPLE
    from services.senegal_knowledge import format_senegal_knowledge

    for query, expected in (
        ("Histoire du fort de Sédhiou", "Fort Pinet-Laprade de Sédhiou"),
        ("marché de Diaobé le mercredi", "Marché hebdomadaire de Diaobé"),
        ("Parle-moi du désert de Lompoul", "Désert de Lompoul"),
    ):
        text = format_senegal_knowledge(SENEGAL_KNOWLEDGE, query=query, people=SENEGAL_PEOPLE)
        first = text.split("LIEUX PERTINENTS :\n", 1)[1].split("\n", 1)[0]
        assert first.startswith(f"- {expected}:"), (query, first)


def test_image_titles_prefer_the_specific_place():
    from app import knowledge_image_titles

    assert knowledge_image_titles("photos de Gorée")[0] == "Gorée"
    assert "Île de Gorée" in knowledge_image_titles("photos de Gorée")
    assert knowledge_image_titles("photos du désert de Lompoul")[0] == "Désert de Lompoul"
    assert knowledge_image_titles("images de Dakar")[0] == "Dakar"


def test_sources_are_https_links_and_precision_is_declared():
    for place in DATA["places"]:
        for url in place.get("sources", []):
            assert url.startswith("https://"), (place["id"], url)
        assert place.get("coordinates_precision", "exact") in {"exact", "approximate"}, place["id"]


def test_wolof_contract_carries_official_orthography_and_safe_phrases():
    from services.language_quality import language_instruction

    wolof = language_instruction("wo")
    assert "Jërëjëf" in wolof and "ñ, ŋ" in wolof and "Dalal ak jàmm" in wolof
    assert "Jërëjëf" not in language_instruction("fr")
    assert "Repères" not in language_instruction("en")


def test_second_batch_covers_thin_regions_with_sources():
    by_id = {p["id"]: p for p in DATA["places"]}
    for place_id, region in (("louga", "Louga"), ("ourossogui", "Matam"), ("kolda", "Kolda"), ("sedhiou", "Sédhiou"), ("koungheul", "Kaffrine")):
        assert by_id[place_id]["region"] == region
        assert by_id[place_id]["sources"]


def test_region_pages_and_place_pages_link_to_each_other():
    from app import app

    client = app.test_client()
    region = client.get("/regions/kaolack", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert 'href="/lieux/kaolack"' in region and '"ItemList"' in region
    place = client.get("/lieux/kaolack", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert 'href="/regions/kaolack"' in place


def test_places_index_has_accent_free_search_without_inline_script():
    from app import app

    html = app.test_client().get("/lieux", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert 'id="place-q"' in html and 'id="place-type"' in html
    assert 'data-text="ile de goree' in html.lower() or "goree" in html
    assert '<script src="/static/places-search.js" defer></script>' in html
    assert "nonce=" not in html  # page en cache public : pas de nonce CSP


def test_chat_question_names_the_place_pages_it_mentions():
    from services.places import mentioned_places

    places = DATA["places"]
    ids = lambda q: [p["id"] for p in mentioned_places(q, places)]  # noqa: E731
    assert ids("Parle-moi de Gorée") == ["goree"]
    assert ids("que voir à Saint-Louis ?") == ["saint-louis"]
    assert set(ids("le lac Rose et Saly")) == {"lac-rose", "saly"}
    assert ids("météo à Dakar") == []  # « Corniche de Dakar » ne capte pas Dakar
    assert ids("Parle moi des personnages de sénégalais") == []


def test_chat_stream_sends_place_links(monkeypatch):
    import json
    from types import SimpleNamespace

    import app as app_module

    def fake_stream(payload, stream=True):
        yield SimpleNamespace(type="response.output_text.delta", delta="Gorée est une île.")

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_stream)
    client = app_module.app.test_client()
    base = "https://teranga-ai.fr"
    token = client.get("/csrf", base_url=base).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post("/chat", json={"message": "Parle-moi de Gorée", "language": "fr"},
                           headers={"X-CSRF-Token": token, "Origin": base}, base_url=base)
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
    assert {"places": [{"id": "goree", "name": "Île de Gorée"}]} in events
