from services.images import topic_wikipedia_titles


def test_topic_wikipedia_titles_resolves_known_places():
    assert topic_wikipedia_titles("Montre-moi des photos de Gorée") == ["Île de Gorée"]
    assert topic_wikipedia_titles("photos de Saint-Louis et du Djoudj", limit=2) == [
        "Saint-Louis (Sénégal)",
        "Parc national des oiseaux du Djoudj",
    ]


def test_topic_wikipedia_titles_ignores_unknown_topics():
    assert topic_wikipedia_titles("Quelle est l'histoire du Sénégal ?") == []


def test_fetch_topic_images_caches_repeated_google_lookup():
    from services.image_topics import fetch_topic_images

    calls = []

    def google(query, limit=8):
        calls.append((query, limit))
        return [{"url": "https://example.test/dakar.jpg", "alt": "Dakar"}]

    kwargs = dict(
        message="Montre-moi des photos de Dakar",
        knowledge={},
        normalize=lambda value: str(value or "").lower(),
        should_fetch_images=lambda _message: True,
        topic_wikipedia_titles=lambda _message, _limit: ["Dakar Sénégal"],
        fetch_commons_images=lambda _title, limit=4: [],
        fetch_google_images=google,
        fetch_city_image=lambda _title: None,
        image_proxy_url=lambda src: src,
        logger=type("Logger", (), {"exception": staticmethod(lambda *args, **kwargs: None)})(),
        max_photos=8,
    )

    first = fetch_topic_images(**kwargs)
    second = fetch_topic_images(**kwargs)

    assert first == second
    assert calls == [("Dakar Sénégal", 8)]


def test_knowledge_image_titles_requires_complete_place_terms():
    from services.image_topics import knowledge_image_titles

    knowledge = {"places": [{"name": "Dakar", "image_queries": ["Dakar"]}]}
    assert knowledge_image_titles("Le Dakarien parle de transport", knowledge, normalize=lambda value: str(value or "").lower()) == []
    assert knowledge_image_titles("Photos de Dakar", knowledge, normalize=lambda value: str(value or "").lower()) == ["Dakar"]


def test_fetch_topic_images_requires_complete_structured_place_terms():
    from services.image_topics import fetch_topic_images

    calls = []

    def commons(query, limit=4):
        calls.append(query)
        return []

    knowledge = {"places": [{"name": "Dakar", "image_queries": ["Dakar Sénégal"]}]}
    result = fetch_topic_images(
        message="Le Dakarien parle de transport",
        knowledge=knowledge,
        normalize=lambda value: str(value or "").lower(),
        should_fetch_images=lambda _message: True,
        topic_wikipedia_titles=lambda _message, _limit: [],
        knowledge_image_titles=lambda _message, _limit: [],
        fetch_commons_images=commons,
        fetch_google_images=None,
        fetch_city_image=lambda _title: None,
        image_proxy_url=lambda src: src,
        logger=type("Logger", (), {"exception": staticmethod(lambda *args, **kwargs: None)})(),
        max_photos=8,
    )
    assert result is None
    assert calls == []
