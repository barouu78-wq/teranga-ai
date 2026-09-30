from services.youth_opportunities import find_youth_opportunities


def test_opportunity_radar_matches_project_category():
    results = find_youth_opportunities("digital")
    assert results
    assert any(item["organization"] == "DER/FJ" for item in results)


def test_opportunity_radar_keeps_official_source_urls():
    results = find_youth_opportunities()
    assert results
    assert all(item["url"].startswith("https://") for item in results)
    assert any("anpej.sn" in item["url"] for item in results)
