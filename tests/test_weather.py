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


def _slow_opener(calls, release):
    def opener(request, timeout=4):
        calls.append(request.full_url)
        release.wait(2)
        return io.BytesIO(json.dumps(SAMPLE).encode())
    return opener


def test_slow_open_meteo_does_not_block_the_answer_and_fills_the_cache_for_the_next_one():
    import threading
    import time

    weather._CACHE.clear()
    calls, release = [], threading.Event()
    opener = _slow_opener(calls, release)
    started = time.perf_counter()
    first = weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "météo Dakar", opener=opener, budget=0.05)
    assert first is None  # la recherche web prend le relais au lieu d'attendre jusqu'à 4 s
    assert time.perf_counter() - started < 0.5
    # Une deuxième question pendant l'attente ne relance pas un second appel.
    assert weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "météo Dakar", opener=opener, budget=0.05) is None
    release.set()
    deadline = time.monotonic() + 2
    while not weather._CACHE and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(calls) == 1
    second = weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "météo Dakar", opener=_opener(calls), budget=0.05)
    assert "pour Dakar" in second and len(calls) == 1  # servi par le cache, sans attente


def test_recently_stale_forecast_is_served_at_once_and_refreshed_in_the_background():
    import threading
    import time

    weather._CACHE.clear()
    key = (round(14.7167, 2), round(-17.4677, 2))
    weather._CACHE[key] = (time.monotonic() - weather.CACHE_SECONDS - 60, SAMPLE)
    calls, release = [], threading.Event()
    text = weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "météo Dakar", opener=_slow_opener(calls, release), budget=0.05)
    assert "relevée le 05/10 14:00" in text  # l'heure du relevé reste affichée
    release.set()
    deadline = time.monotonic() + 2
    while weather._CACHE[key][0] < time.monotonic() - weather.CACHE_SECONDS and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(calls) == 1 and time.monotonic() - weather._CACHE[key][0] < weather.CACHE_SECONDS


def test_too_old_forecast_is_not_served_without_a_fresh_reading():
    import time

    weather._CACHE.clear()
    key = (round(14.7167, 2), round(-17.4677, 2))
    weather._CACHE[key] = (time.monotonic() - weather.STALE_SECONDS - 60, SAMPLE)

    def broken(request, timeout=4):
        raise TimeoutError("lent")

    assert weather.live_weather_context(LOCATIONS, {"intent": "weather"}, "météo Dakar", opener=broken, budget=0.2) is None


def test_chat_waits_for_the_weather_only_a_short_budget(monkeypatch):
    import app as app_module

    seen = {}

    def fake(*args, **kwargs):
        seen.update(kwargs)
        return None

    monkeypatch.setattr(app_module, "live_weather_context", fake)
    with app_module.app.test_request_context("/chat", method="POST", json={"message": "Quel temps fait-il à Dakar ?", "language": "fr"}):
        app_module.parse_chat_payload()
    assert 0 < seen["budget"] <= 1.5
