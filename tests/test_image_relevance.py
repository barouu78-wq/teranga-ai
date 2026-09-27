from services.images import _photo_matches_query


def test_precise_photo_query_rejects_dakar_for_goree():
    assert not _photo_matches_query(
        "Île de Gorée Sénégal",
        "File:Dakar.jpg",
        "Vue de Dakar",
    )


def test_precise_photo_query_accepts_goree():
    assert _photo_matches_query(
        "Île de Gorée Sénégal",
        "File:Gorée.jpg",
        "Vue de l'île de Gorée",
    )


def test_precise_photo_query_rejects_generic_lac_rose_result():
    assert not _photo_matches_query(
        "Lac Rose Sénégal",
        "File:Dakar beach.jpg",
        "Vue de Dakar",
    )


def test_generic_photo_query_keeps_normal_results():
    assert _photo_matches_query(
        "Dakar Sénégal",
        "File:Dakar.jpg",
        "Vue de Dakar",
    )
