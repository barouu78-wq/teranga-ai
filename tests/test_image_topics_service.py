from services.image_topics import fetch_topic_images, knowledge_image_titles


def test_knowledge_image_titles_uses_region_and_place_queries():
    knowledge = {
        "regions": [
            {"name": "Dakar", "places": ["Gorée"], "highlights": [], "image_queries": ["Dakar skyline"]}
        ],
        "places": [{"name": "Lac Rose", "image_queries": ["Lac Retba"]}],
    }

    assert knowledge_image_titles(
        "photos de Gorée",
        knowledge,
        normalize=lambda value: str(value).lower(),
    ) == ["Dakar", "Gorée", "Dakar skyline"]


def test_fetch_topic_images_prefers_specific_place_queries_and_deduplicates():
    calls = []
    knowledge = {
        "places": [
            {"name": "Île de Gorée", "image_queries": ["Île de Gorée waterfront"]},
            {"name": "Dakar", "image_queries": ["Dakar"]},
        ]
    }

    def commons(title, limit=3):
        calls.append(title)
        return [
            {"url": "https://upload.wikimedia.org/a.jpg"},
            {"url": "https://upload.wikimedia.org/a.jpg"},
            {"url": "https://upload.wikimedia.org/b.jpg"},
        ]

    result = fetch_topic_images(
        "Montre-moi des photos de Gorée",
        knowledge,
        normalize=lambda value: str(value).lower().replace("î", "i"),
        should_fetch_images=lambda value: True,
        topic_wikipedia_titles=lambda value, limit: [],
        fetch_commons_images=commons,
        fetch_city_image=lambda title: None,
        image_proxy_url=lambda src: "/image-proxy?url=" + src.rsplit("/", 1)[-1],
        logger=type("Logger", (), {"exception": lambda *args: None})(),
    )

    assert calls == ["Île de Gorée waterfront"]
    assert [item["url"] for item in result] == [
        "https://upload.wikimedia.org/a.jpg",
        "https://upload.wikimedia.org/b.jpg",
    ]
    assert all(item["search_query"] == "Île de Gorée waterfront" for item in result)


def test_fetch_topic_images_prefers_google_and_can_return_eight_images():
    google_calls = []
    commons_calls = []

    def google(title, limit=8):
        google_calls.append((title, limit))
        return [{"url": f"https://images.example/{i}.jpg", "display_url": f"https://thumb.example/{i}.jpg"} for i in range(8)]

    def commons(title, limit=4):
        commons_calls.append((title, limit))
        return []

    knowledge = {"regions": [{"name": "Dakar", "places": [], "highlights": [], "image_queries": ["Dakar Sénégal"]}], "places": []}
    result = fetch_topic_images(
        "Montre-moi des photos de Dakar",
        knowledge,
        normalize=lambda value: str(value).lower(),
        should_fetch_images=lambda value: True,
        topic_wikipedia_titles=lambda value, limit: [],
        fetch_commons_images=commons,
        fetch_google_images=google,
        fetch_city_image=lambda title: None,
        image_proxy_url=lambda src: src,
        logger=type("Logger", (), {"exception": lambda *args: None})(),
    )

    assert google_calls == [("Dakar", 8)]
    assert commons_calls == []
    assert len(result) == 8
    assert {item["search_query"] for item in result} == {"Dakar"}
