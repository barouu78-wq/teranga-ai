from services.senegal_knowledge import classify_domain


def test_domain_matching_uses_complete_terms():
    assert classify_domain("Je cherche un business au Sénégal.") == "economy"


def test_business_does_not_trigger_transport():
    assert classify_domain("Le business est important.") == "economy"


def test_weather_domain_still_matches():
    assert classify_domain("Quelle est la météo à Dakar ?") == "weather"
