from pathlib import Path


PAYLOAD = Path(__file__).resolve().parents[1] / "services" / "chat_payload_service.py"
POLICY = Path(__file__).resolve().parents[1] / "services" / "web_policy.py"


def test_weather_response_contract_requires_verified_period_and_source():
    source = PAYLOAD.read_text(encoding="utf-8")
    assert "MÉTÉO :" in source
    assert "privilégie ANACIM" in source
    assert "date de validité" in source
    assert "indique clairement la source" in source
    assert "ne remplace pas ANACIM" in source


def test_weather_policy_does_not_allow_meteo_france_as_senegal_priority():
    source = POLICY.read_text(encoding="utf-8")
    assert '"weather": ("anacim.sn", "ansd.sn", "gov.sn")' in source
    assert '"weather": ("meteofrance.com"' not in source
