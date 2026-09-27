from services.senegal_knowledge import classify_domain, needs_fresh_web, source_domains

def test_senegal_domain_classification():
    assert classify_domain("Quelle est la population du Sénégal ?") == "society"
    assert classify_domain("Que visiter en Casamance ?") == "travel"
    assert classify_domain("Comment va l'agriculture ?") == "agriculture"

def test_fresh_web_for_dynamic_questions():
    assert needs_fresh_web("general", "Quel est le prix aujourd'hui ?")
    assert needs_fresh_web("transport", "Comment aller à Saint-Louis ?")

def test_official_sources_are_prioritized():
    assert "ansd.sn" in source_domains("society")
    assert "tourisme.gouv.sn" in source_domains("travel")


def test_all_fourteen_regions_are_covered():
    from services.senegal_knowledge import SENEGAL_REGIONS
    assert len(SENEGAL_REGIONS) == 14
    assert {"Dakar", "Kaffrine", "Kédougou", "Sédhiou", "Ziguinchor"}.issubset(SENEGAL_REGIONS)


def test_regional_location_context():
    from services.intelligence import detect_location
    assert detect_location("Je veux visiter Kédougou") == "kédougou"
    assert detect_location("Que voir à Ziguinchor ?") == "ziguinchor"
