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
