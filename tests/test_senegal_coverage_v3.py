from services.intelligence import detect_location
from services.senegal_knowledge import REGIONS, region_highlights, classify_domain, source_domains
from services.photo_search import normalize_place_query, relevant_image_evidence

def test_all_fourteen_regions_are_recognized():
    assert len(REGIONS) == 14
    expected = {"Dakar": "dakar", "Thiès": "thies", "Diourbel": "diourbel", "Fatick": "fatick", "Kaolack": "kaolack", "Kaffrine": "kaffrine", "Louga": "louga", "Saint-Louis": "saint-louis", "Matam": "matam", "Tambacounda": "tambacounda", "Kédougou": "kedougou", "Kolda": "kolda", "Sédhiou": "sedhiou", "Ziguinchor": "ziguinchor"}
    for region in REGIONS:
        assert detect_location(region) == expected[region]
        assert region_highlights(region)

def test_weather_is_a_fresh_web_domain():
    assert classify_domain("météo à Dakar") == "weather"
    assert "meteofrance.com" in source_domains("weather")

def test_precise_photo_aliases_cover_more_senegal():
    assert "Delta du Saloum" in normalize_place_query("photos du Saloum")
    assert "Pays Bassari" in normalize_place_query("Pays Bassari")
    assert relevant_image_evidence("Dindéfelo", "Dindéfelo waterfall, Senegal")
    assert not relevant_image_evidence("Dindéfelo", "Yoff Beach, Dakar")