from services.photo_search import normalize_place_query, relevant_image_evidence

def test_precise_goree_query():
    assert "Gorée" in normalize_place_query("photos de Gorée")

def test_precise_photo_relevance():
    assert relevant_image_evidence("Gorée", "Île de Gorée", "")
    assert not relevant_image_evidence("Gorée", "Yoff Beach, Dakar", "")
