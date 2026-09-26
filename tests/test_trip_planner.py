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
