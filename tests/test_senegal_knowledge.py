from services.senegal_knowledge import classify_domain, needs_fresh_web, source_domains

def test_classifies_population_as_society():
    assert classify_domain("Quelle est la population du Sénégal ?") == "society"

def test_classifies_casamance_as_travel():
    assert classify_domain("Que visiter en Casamance ?") == "travel"

def test_classifies_agriculture():
    assert classify_domain("Parle-moi de l'agriculture au Sénégal.") == "agriculture"

def test_weather_has_fresh_web_and_anacim():
    assert classify_domain("Quel temps fait-il à Dakar aujourd'hui ?") == "weather"
    assert needs_fresh_web("weather", "météo actuelle à Dakar")
    assert source_domains("weather")[0] == "anacim.sn"

def test_transport_uses_public_sources():
    assert source_domains("transport")[0] == "transports.gouv.sn"

def test_dynamic_domain_requires_fresh_web():
    assert needs_fresh_web("travel", "horaires ferry Gorée")

def test_official_sources_are_prioritized():
    assert "ansd.sn" in source_domains("society")
