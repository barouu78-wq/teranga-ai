from services.image_topics import _build_primary_query


def normalize(value):
    import unicodedata
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def test_generic_photo_request_uses_actual_visual_intent():
    query = _build_primary_query(
        "Meilleur photo plage",
        [],
        [],
        normalize,
    )
    assert query == "Meilleur photo plage Sénégal"


def test_specific_place_query_wins_over_generic_request():
    query = _build_primary_query(
        "montre moi Gorée",
        ["Île de Gorée"],
        ["Dakar"],
        normalize,
    )
    assert query == "Île de Gorée"


def test_photo_request_does_not_fall_back_to_dakar():
    query = _build_primary_query(
        "photos du Sénégal",
        [],
        [],
        normalize,
    )
    assert "Dakar" not in query
    assert "Sénégal" in query
