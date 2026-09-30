from services.web_policy import preferred_domains, reasoning_effort, search_context_size


def test_official_domains_for_senegal_statistics():
    domains = preferred_domains("society")
    assert "ansd.sn" in domains
    assert "gov.sn" in domains


def test_travel_source_policy():
    domains = preferred_domains("travel")
    assert domains[:2] == ("tourisme.gouv.sn", "ansd.sn")
    assert "unesco.org" in domains


def test_weather_source_policy():
    domains = preferred_domains("weather")
    assert domains[:2] == ("meteofrance.com", "ansd.sn")


def test_general_web_has_no_restrictive_domain_filter():
    assert preferred_domains("general") == ()


def test_search_context_is_low_for_fast_lookup():
    assert search_context_size("weather") == "low"
    assert search_context_size("travel") == "low"


def test_planner_and_sensitive_domains_keep_medium_context():
    assert search_context_size("travel", planner=True) == "medium"
    assert search_context_size("administration") == "medium"


def test_fast_chat_uses_low_reasoning_by_default():
    assert reasoning_effort(False, False) == "low"
    assert reasoning_effort(True, False) == "low"


def test_should_use_web_detects_live_and_contextual_requests():
    from services.web_policy import should_use_web

    assert should_use_web("Quel est le prix actuel du billet ?")
    assert should_use_web("Et demain ?", "météo à Dakar")
    assert not should_use_web("Quelle est l'histoire de Gorée ?")


def test_transport_and_food_source_policy():
    assert preferred_domains("transport")[:2] == ("transports.gouv.sn", "gov.sn")
    assert preferred_domains("food")[:2] == ("agriculture.gouv.sn", "tourisme.gouv.sn")
