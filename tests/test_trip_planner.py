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
    data = {"arrival_date": date(2026, 10, 1), "departure_date": date(2026, 10, 8),
            "adults": 2, "children": 0, "budget": "Confort"}
    budget = _budget(data)
    assert budget["days"] == 7
    assert budget["total"][0] < budget["total"][1]
    assert sum(x[0] for k, x in budget.items() if k in {"accommodation","food","transport","activities","buffer"}) == budget["total"][0]
