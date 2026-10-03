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



def test_all_fourteen_regions_are_covered():
    from services.senegal_knowledge import SENEGAL_REGIONS
    assert len(SENEGAL_REGIONS) == 14
    assert len(set(SENEGAL_REGIONS)) == 14


def test_regional_location_context():
    from services.intelligence import detect_location
    assert detect_location("Je veux visiter Kédougou") == "kedougou"
    assert detect_location("Que voir à Ziguinchor ?") == "ziguinchor"


def test_weather_is_a_fresh_web_domain():
    assert classify_domain("météo à Dakar") == "weather"
    assert "anacim.sn" in source_domains("weather")

def test_core_senegal_destinations_are_retrievable():
    from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge

    data = load_senegal_knowledge()
    cases = {
        "Dakar": "Dakar",
        "Île de Gorée": "Île de Gorée",
        "Saint-Louis": "Île de Saint-Louis",
        "Saly": "Saly",
        "Casamance": "Ziguinchor",
    }
    for query, expected in cases.items():
        context = format_senegal_knowledge(data, query=query)
        assert expected in context

def test_knowledge_context_adds_relevant_domain():
    from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge

    data = load_senegal_knowledge()
    context = format_senegal_knowledge(data, query="Que visiter à Dakar ?")
    assert "DOMAINE PERTINENT (travel)" in context
    assert "Tourisme" in context or "tourisme" in context


def test_dynamic_source_priorities_match_web_policy():
    assert source_domains("transport")[:2] == ("transports.gouv.sn", "gov.sn")
    assert source_domains("food")[:2] == ("agriculture.gouv.sn", "tourisme.gouv.sn")
    assert source_domains("weather")[:2] == ("anacim.sn", "ansd.sn")


def test_knowledge_context_cache_reuses_same_query():
    from services.senegal_knowledge import _KNOWLEDGE_CONTEXT_CACHE, format_senegal_knowledge, load_senegal_knowledge

    data = load_senegal_knowledge()
    _KNOWLEDGE_CONTEXT_CACHE.clear()
    first = format_senegal_knowledge(data, query="Que visiter à Casamance ?")
    second = format_senegal_knowledge(data, query="Que visiter à Casamance ?")

    assert first == second
    assert len(_KNOWLEDGE_CONTEXT_CACHE) == 1


def test_knowledge_domain_routes_business_and_employment():
    from services.senegal_knowledge import _knowledge_domain

    assert _knowledge_domain("Je veux lancer une entreprise au Sénégal") == "business"
    assert _knowledge_domain("Je cherche un emploi à Dakar") == "employment"


def test_knowledge_domain_routes_education_and_diaspora():
    from services.senegal_knowledge import _knowledge_domain

    assert _knowledge_domain("Quelle formation suivre au Sénégal ?") == "education"
    assert _knowledge_domain("Je prépare mon retour depuis la diaspora") == "diaspora"


def test_health_source_priority_matches_web_policy():
    assert source_domains("health")[:2] == ("sante.gouv.sn", "who.int")


def test_health_domain_classification_and_freshness():
    assert classify_domain("Quels sont les services de santé à Dakar ?") == "health"
    assert needs_fresh_web("health", "Quels centres sont ouverts aujourd’hui ?")
