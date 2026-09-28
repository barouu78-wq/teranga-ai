from services.photo_search import normalize_place_query, relevant_image_evidence

def test_precise_goree_query():
    assert "Gorée" in normalize_place_query("photos de Gorée")

def test_precise_photo_relevance():
    assert relevant_image_evidence("Gorée", "Île de Gorée", "")
    assert not relevant_image_evidence("Gorée", "Yoff Beach, Dakar", "")



def test_regional_photo_queries_stay_precise():
    assert "Thiès" in normalize_place_query("photos de Thiès")
    assert relevant_image_evidence("Thiès", "Thiès, Sénégal", "")
    assert not relevant_image_evidence("Thiès", "Saint-Louis, Sénégal", "")


def test_additional_senegal_photo_aliases():
    assert "Delta du Saloum" in normalize_place_query("photos du Saloum")
    assert "Pays Bassari" in normalize_place_query("Pays Bassari")
    assert relevant_image_evidence("Dindéfelo", "Dindéfelo waterfall, Senegal")
    assert not relevant_image_evidence("Dindéfelo", "Yoff Beach, Dakar")
