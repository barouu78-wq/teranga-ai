from services.image_topics import _build_primary_query


def normalize(value):
    import unicodedata
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def test_generic_photo_request_uses_actual_visual_intent():
    query = _build_primary_query("Meilleur photo plage", [], [], normalize)
    assert query == "Meilleur photo plage Sénégal"


def test_specific_place_query_wins_over_generic_request():
    query = _build_primary_query("montre moi Gorée", ["Île de Gorée"], ["Dakar"], normalize)
    assert query == "Île de Gorée"


def test_photo_request_does_not_fall_back_to_dakar():
    query = _build_primary_query("photos du Sénégal", [], [], normalize)
    assert "Dakar" not in query
    assert "Sénégal" in query


def test_dakar_request_keeps_dakar_as_primary_query():
    query = _build_primary_query("montre moi des photos de Dakar", [], [], normalize)
    assert query == "Dakar Sénégal"


def test_saly_request_keeps_saly_as_primary_query():
    query = _build_primary_query("photos de Saly Portudal", [], [], normalize)
    assert query == "Saly Portudal Sénégal"


def test_goree_request_keeps_goree_as_primary_query():
    query = _build_primary_query("montre-moi des photos de l'île de Gorée", [], [], normalize)
    assert query == "l'île de Gorée Sénégal"


def test_city_is_not_replaced_by_generic_senegal():
    query = _build_primary_query("photos Dakar", [], [], normalize)
    assert query == "Dakar Sénégal"
