import services.images as images


def test_should_fetch_images_requires_complete_trigger_terms():
    assert not images.should_fetch_images("peinture photographique")
    assert not images.should_fetch_images("montre-moi le budget")
    assert images.should_fetch_images("montre-moi Dakar en photo")


def test_topic_wikipedia_titles_uses_complete_place_terms():
    assert images.topic_wikipedia_titles("Le routeur est à Dakar") == ["Dakar"]
    assert images.topic_wikipedia_titles("Photos de Saint-Louis") == ["Saint-Louis (Sénégal)"]
    assert images.topic_wikipedia_titles("Une image de Saint-Louis") == ["Saint-Louis (Sénégal)"]
