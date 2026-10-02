from services.senegal_knowledge import classify_domain


def test_domain_matching_uses_complete_terms():
    assert classify_domain("Je cherche un business au Sénégal.") == "economy"


def test_transport_term_does_not_match_inside_unrelated_word():
    assert classify_domain("La transportation internationale est complexe.") == "general"


def test_weather_domain_still_matches():
    assert classify_domain("Quelle est la météo à Dakar ?") == "weather"
