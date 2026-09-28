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


def test_structured_knowledge_can_focus_on_requested_region():
    from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge

    data = load_senegal_knowledge()
    context = format_senegal_knowledge(data, query="Que visiter en Casamance à Ziguinchor ?")
    assert "Ziguinchor" in context
    assert "Dakar" not in context or context.count("Dakar") < 2


def test_structured_people_are_loaded_separately():
    from services.senegal_knowledge import load_senegal_people

    people = load_senegal_people()
    names = {person["name"] for person in people}
    assert "Cheikh Anta Diop" in names
    assert "Léopold Sédar Senghor" in names


def test_structured_knowledge_does_not_require_all_regions_in_prompt():
    from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge

    data = load_senegal_knowledge()
    context = format_senegal_knowledge(data, query="Saint-Louis")
    assert "Saint-Louis" in context
    assert "Kaolack" not in context
\n\n\ndef test_all_fourteen_regions_are_covered():\n    from services.senegal_knowledge import SENEGAL_REGIONS\n    assert len(SENEGAL_REGIONS) == 14\n    assert len(set(SENEGAL_REGIONS)) == 14\n\n\ndef test_regional_location_context():\n    from services.intelligence import detect_location\n    assert detect_location("Je veux visiter Kédougou") == "kedougou"\n    assert detect_location("Que voir à Ziguinchor ?") == "ziguinchor"\n\n\ndef test_weather_is_a_fresh_web_domain():\n    assert classify_domain("météo à Dakar") == "weather"\n    assert "meteofrance.com" in source_domains("weather")\n