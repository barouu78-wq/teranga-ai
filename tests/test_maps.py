from services.maps import lookup_map, should_fetch_map


def test_map_intent_uses_word_boundaries():
    assert should_fetch_map("Comment aller à Dakar ?")
    assert not should_fetch_map("Je travaille dans une entreprise.")


def test_map_lookup_prefers_specific_place_alias():
    result = lookup_map("Où est la maison des esclaves à Gorée ?")
    assert result["label"] == "Maison des Esclaves"


def test_map_lookup_does_not_match_inside_word():
    assert lookup_map("Je parle de Dakart aujourd'hui.") is None
