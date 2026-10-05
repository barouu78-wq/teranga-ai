import io
import json
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import weather

SAMPLE = {
    "current": {"time": "2026-10-05T14:00", "temperature_2m": 31.2, "apparent_temperature": 35.0,
                "relative_humidity_2m": 70, "wind_speed_10m": 14.0, "weather_code": 2, "precipitation": 0},
    "daily": {"time": ["2026-10-05", "2026-10-06"], "weather_code": [2, 95],
              "temperature_2m_min": [25.1, 24.8], "temperature_2m_max": [32.0, 30.5],
              "precipitation_probability_max": [10, 80], "wind_speed_10m_max": [20.0, 35.0]},
}
LOCATIONS = weather.build_locations({"Dakar": (14.7167, -17.4677), "Ziguinchor": (12.5833, -16.2667), "Saint-Louis": (16.0326, -16.4818)}, [])


def _opener(calls):
    def opener(request, timeout=4):
        calls.append(request.full_url)
        return io.BytesIO(json.dumps(SAMPLE).encode())
    return opener


def test_weather_context_uses_open_meteo_for_the_requested_city():
    weather._CACHE.clear()
    calls = []
    text = weather.live_weather_context(LOCATIONS, {"intent": "weather", "location": None}, "Il pleut à Ziguinchor demain ?", "fr", opener=_opener(calls))
    assert "latitude=12.58" in calls[0] and "timezone=Africa%2FDakar" in calls[0]
    assert "MÉTÉO EN DIRECT (Open-Meteo" in text and "pour Ziguinchor" in text
    assert "Demain : orages, 24.8–30.5 °C, risque de pluie 80 %" in text
    assert "ANACIM" in text


def test_weather_defaults_to_dakar_and_is_cached():
    weather._CACHE.clear()
    calls = []
    opener = _opener(calls)
    first = weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "Quel temps fait-il ?", "en", opener=opener)
    weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "Quel temps fait-il ?", "en", opener=opener)
    assert len(calls) == 1
    assert "LIVE WEATHER" in first and "for Dakar" in first and "Tomorrow : thunderstorms" in first


def test_weather_ignores_other_intents_and_survives_outages():
    assert weather.live_weather_context(LOCATIONS, {"intent": "food"}, "météo des plats", opener=_opener([])) is None
    weather._CACHE.clear()

    def broken(request, timeout=4):
        raise TimeoutError("lent")

    assert weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "météo Saint-Louis", opener=broken) is None


def test_weather_question_skips_web_search_when_forecast_is_available(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "live_weather_context", lambda *a, **k: "MÉTÉO EN DIRECT (Open-Meteo) pour Dakar")
    with app_module.app.test_request_context("/chat", method="POST", json={"message": "Quel temps fait-il à Dakar aujourd'hui ?", "language": "fr"}):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    assert payload["use_web"] is False and payload["live_weather"] is True
    assert payload["instructions"].endswith("MÉTÉO EN DIRECT (Open-Meteo) pour Dakar")
