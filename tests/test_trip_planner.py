import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app

def test_trip_planner_page():
    response = app.test_client().get("/trip-planner")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Senegal Trip Planner" in body
    assert "/api/trip-planner" in body
    assert 'name="arrival"' in body

def test_trip_planner_rejects_invalid_json():
    response = app.test_client().post("/api/trip-planner", json={"arrival": "", "departure": ""})
    assert response.status_code == 400


def test_trip_planner_rejects_reversed_dates():
    response = app.test_client().post("/api/trip-planner", json={"arrival": "2026-10-10", "departure": "2026-10-09"})
    assert response.status_code == 400


def test_trip_budget_is_structured():
    from datetime import date
    from services.trip_planner import _budget

    data = {
        "arrival_date": date(2026, 10, 1),
        "departure_date": date(2026, 10, 8),
        "adults": 2,
        "children": 0,
        "budget": "Confort",
    }
    budget = _budget(data)
    assert budget["days"] == 7
    assert budget["total"][0] < budget["total"][1]
    assert sum(
        x[0]
        for k, x in budget.items()
        if k in {"accommodation", "food", "transport", "activities", "buffer"}
    ) == budget["total"][0]
def test_trip_budget_categories_reconcile_after_rounding():
    from datetime import date
    from services.trip_planner import _budget

    data = {
        "arrival_date": date(2026, 10, 1),
        "departure_date": date(2026, 10, 2),
        "adults": 1,
        "children": 0,
        "budget": "Confort",
    }
    budget = _budget(data)
    categories = ("accommodation", "food", "transport", "activities", "buffer")
    assert sum(budget[key][0] for key in categories) == budget["total"][0]
    assert sum(budget[key][1] for key in categories) == budget["total"][1]


def test_trip_plan_contract_falls_back_on_invalid_shape():
    from services.trip_planner import _normalize_plan

    fallback = _normalize_plan(["not", "an", "object"], "raw model output")
    assert fallback == {"summary": "raw model output", "days": [], "practical_notes": []}


def test_trip_plan_contract_normalizes_supported_fields():
    from services.trip_planner import _normalize_plan

    plan = _normalize_plan(
        {
            "summary": "Deux jours au Sénégal",
            "days": [
                {
                    "day": 1,
                    "title": "Dakar",
                    "region": "Dakar",
                    "morning": "Marché",
                    "afternoon": "Gorée",
                    "evening": "Dîner",
                    "transport": "Taxi",
                }
            ],
            "practical_notes": ["Vérifier les horaires."],
        },
        "fallback",
    )
    assert plan["summary"] == "Deux jours au Sénégal"
    assert plan["days"][0]["region"] == "Dakar"
    assert plan["practical_notes"] == ["Vérifier les horaires."]


def test_trip_map_bounds_follow_selected_regions():
    from services.trip_planner import _map_html

    map_html = _map_html(["Dakar", "Kédougou"])
    assert "bbox=" in map_html
    assert "-18.2677%2C11.7600%2C-11.3800%2C15.5167" in map_html


def test_trip_map_returns_empty_for_unknown_regions():
    from services.trip_planner import _map_html

    assert _map_html(["Unknown region"]) == ""


def test_trip_planner_normalizes_invalid_collection_and_option_inputs():
    from flask import Flask
    import services.trip_planner as trip_planner

    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured["prompt"] = kwargs["input"]
            return type("Response", (), {"output_text": '{"summary":"ok","days":[],"practical_notes":[]}'} )()

    class FakeClient:
        responses = FakeResponses()

    app = Flask(__name__)
    trip_planner.register_trip_planner(app, FakeClient(), "https://example.com")
    client = app.test_client()
    response = client.post("/api/trip-planner", json={
        "arrival": "2026-10-01",
        "departure": "2026-10-03",
        "interests": "Dakar",
        "regions": "Dakar",
        "budget": "not-a-budget",
        "pace": "not-a-pace",
    })
    assert response.status_code == 200
    assert "Interests: general discovery" in captured["prompt"]
    assert "Preferred regions: none" in captured["prompt"]
    assert "Budget level: Confort" in captured["prompt"]
    assert "Pace: Équilibré" in captured["prompt"]


def test_trip_planner_form_uses_distinct_option_groups():
    from services.trip_planner import _html

    body = _html("https://example.com", "fr")
    assert 'type="radio" name="budget"' in body
    assert 'type="radio" name="pace"' in body
    assert 'type="checkbox" name="interests"' in body
    assert 'type="checkbox" name="regions"' in body
    assert 'input[name=x]' not in body



def test_trip_planner_share_link_is_restorable_and_url_safe():
    from services.trip_planner import _html

    body = _html("https://example.com", "fr")
    assert "function encodeTrip(payload)" in body
    assert "function decodeTrip(value)" in body
    assert "applySharedTrip();" in body
    assert "replace(/\\+/g,'-')" in body
    assert 'new URLSearchParams(location.search).get(\'trip\')' in body
    assert '"share_id"' not in body
