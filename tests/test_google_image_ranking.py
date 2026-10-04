from services.images import _google_photo_relevance_score, _google_photo_matches_query


def test_dakar_exact_result_ranks_above_saly():
    dakar = _google_photo_relevance_score(
        "photos de Dakar",
        "Dakar skyline",
        "https://example.com/dakar",
    )
    saly = _google_photo_relevance_score(
        "photos de Dakar",
        "Saly Portudal beach",
        "https://example.com/saly-portudal",
    )
    assert dakar > saly


def test_saly_exact_result_ranks_above_dakar():
    saly = _google_photo_relevance_score(
        "photos de Saly",
        "Saly Portudal beach",
        "https://example.com/saly",
    )
    dakar = _google_photo_relevance_score(
        "photos de Saly",
        "Dakar beach",
        "https://example.com/dakar",
    )
    assert saly > dakar


def test_generic_senegal_beach_query_keeps_saly_relevant():
    assert _google_photo_relevance_score(
        "meilleures photos plage Sénégal",
        "Saly Portudal beach",
        "https://example.com/saly",
    ) >= 0


def test_precise_dakar_result_with_saly_context_is_rejected():
    assert not _google_photo_matches_query(
        "Dakar Sénégal",
        "Dakar beach in Saly",
        "https://example.com/saly",
    )


def test_precise_place_without_exact_evidence_is_lower_ranked_not_crashed():
    assert _google_photo_relevance_score(
        "photos de Dakar",
        "Belle plage du Sénégal",
        "https://example.com/senegal",
    ) < _google_photo_relevance_score(
        "photos de Dakar",
        "Dakar beach",
        "https://example.com/dakar",
    )
