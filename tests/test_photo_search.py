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


def test_precise_queries_are_not_collapsed_to_a_city():
    # Un lieu précis dans une ville ne devient pas « Dakar Sénégal ».
    assert normalize_place_query("Île de Ngor Dakar").startswith("Île de Ngor Dakar")
    assert normalize_place_query("Monument Renaissance africaine Dakar").startswith("Monument Renaissance")
    # « touba » ne se confond pas avec Toubacouta ni Toubab Dialaw.
    assert "Touba" not in normalize_place_query("mangrove Toubacouta Sénégal").replace("Toubacouta", "")
    assert normalize_place_query("Toubab Dialaw").startswith("Toubab Dialaw")
    assert not relevant_image_evidence("Touba Grande Mosquée de Touba Sénégal", "Toubab Dialaw beach")
    # Une photo de Ngor n'est pas rejetée parce qu'elle ne dit pas « Dakar ».
    assert relevant_image_evidence("Île de Ngor Dakar", "Ngor Island beach")
