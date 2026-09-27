from services.web_policy import preferred_domains, reasoning_effort, search_context_size


def test_official_domains_for_senegal_statistics():
    domains = preferred_domains("society")
    assert "ansd.sn" in domains
    assert "gov.sn" in domains


def test_travel_source_policy():
    domains = preferred_domains("travel")
    assert domains[:2] == ("tourisme.gouv.sn", "ansd.sn")
    assert "unesco.org" in domains


def test_general_web_has_no_restrictive_domain_filter():
    assert preferred_domains("general") == ()


def test_search_context_is_low_for_fast_lookup():
    assert search_context_size("weather") == "low"
    assert search_context_size("travel") == "low"


def test_planner_and_sensitive_domains_keep_medium_context():
    assert search_context_size("travel", planner=True) == "medium"
    assert search_context_size("administration") == "medium"


def test_simple_requests_use_no_reasoning_by_default():
    assert reasoning_effort(False, False) == "none"
    assert reasoning_effort(True, False) == "low"
