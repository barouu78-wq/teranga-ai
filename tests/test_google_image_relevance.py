from services.images import _google_photo_matches_query


def test_dakar_rejects_saly_google_result():
    assert not _google_photo_matches_query(
        "Dakar Sénégal",
        "Saly Portudal beach",
        "https://example.com/saly-portudal",
    )


def test_dakar_keeps_dakar_google_result():
    assert _google_photo_matches_query(
        "Dakar Sénégal",
        "Dakar skyline",
        "https://example.com/dakar",
    )


def test_unrelated_query_is_not_overfiltered():
    assert _google_photo_matches_query(
        "plage Sénégal",
        "Saly Portudal beach",
        "https://example.com/saly",
    )
