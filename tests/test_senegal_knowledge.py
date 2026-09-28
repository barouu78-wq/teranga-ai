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
