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


def test_photo_query_strips_every_conversational_prefix():
    from services.image_topics import _build_primary_query

    def norm(value):
        import unicodedata
        text = unicodedata.normalize("NFD", str(value or "").lower())
        return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

    assert _build_primary_query("montre moi des photos de plage", [], [], norm) == "plage Sénégal"
    assert _build_primary_query("Affiche-moi des images de pirogues", [], [], norm) == "pirogues Sénégal"


def test_article_photos_come_before_raw_commons_search():
    from services.image_topics import fetch_topic_images

    calls = []

    def article(title, limit=6):
        calls.append(("article", title))
        return [{"url": f"https://upload.wikimedia.org/a{i}.jpg", "alt": "Dakar"} for i in range(5)]

    def commons(title, limit=4):
        calls.append(("commons", title))
        return [{"url": "https://upload.wikimedia.org/random.jpg"}]

    photos = fetch_topic_images(
        "photos de Dakar unique-test-key",
        {"places": []},
        normalize=lambda v: str(v or "").lower(),
        should_fetch_images=lambda m: True,
        topic_wikipedia_titles=lambda m, n: ["Dakar"],
        knowledge_image_titles=lambda m, n: [],
        fetch_commons_images=commons,
        fetch_google_images=lambda t, limit=4: [],
        fetch_article_images=article,
        fetch_city_image=lambda t: None,
        image_proxy_url=lambda u: "/image-proxy?url=" + u,
        logger=__import__("logging").getLogger("test"),
    )
    assert [c[0] for c in calls] == ["article"]
    assert len(photos) == 5 and photos[0]["search_query"] == "Dakar"
    assert photos[0]["display_url"].startswith("/image-proxy?url=")


def test_fetch_article_images_filters_maps_flags_and_small_files():
    import io
    import json as _json
    from services.images import _ARTICLE_CACHE, fetch_article_images

    _ARTICLE_CACHE.clear()

    def page(title, mime="image/jpeg", w=2000, h=1300):
        return {"title": title, "imageinfo": [{"mime": mime, "width": w, "height": h,
                "url": "https://upload.wikimedia.org/" + title, "thumburl": "https://upload.wikimedia.org/t/" + title}]}

    pages = [page("Fichier:Dakar Plateau.jpg"), page("Fichier:Carte Dakar.jpg"), page("Fichier:Flag of Senegal.svg", "image/svg+xml"),
             page("Fichier:Petit.jpg", w=300, h=200), page("Fichier:Corniche de Dakar.jpg")]
    requested = []

    def opener(req, timeout=5):
        requested.append(req.full_url)
        return io.BytesIO(_json.dumps({"query": {"pages": {str(i): p for i, p in enumerate(pages)}}}).encode())

    photos = fetch_article_images("Dakar Sénégal", urlopen_fn=opener)
    assert "titles=Dakar+%28S%C3%A9n%C3%A9gal%29" in requested[0]
    names = [p["page_url"].rsplit("/", 1)[-1] for p in photos]
    assert names == ["File:Corniche_de_Dakar.jpg", "File:Dakar_Plateau.jpg"]


def test_photo_sources_run_in_parallel_within_budget():
    import time

    from services import image_topics

    def slow(seconds, result):
        def call(title, limit=4):
            time.sleep(seconds)
            return result
        return call

    started = time.perf_counter()
    photos = image_topics.fetch_topic_images(
        "photos de Kaolack parallel-test",
        {"places": []},
        normalize=lambda v: str(v or "").lower(),
        should_fetch_images=lambda m: True,
        topic_wikipedia_titles=lambda m, n: ["Kaolack", "Saloum"],
        knowledge_image_titles=lambda m, n: [],
        fetch_commons_images=slow(0.1, []),
        fetch_google_images=slow(0.4, [{"url": "https://g/1.jpg"}]),
        fetch_article_images=slow(0.4, [{"url": "https://upload.wikimedia.org/k%d.jpg" % i} for i in range(3)]),
        fetch_city_image=lambda t: None,
        image_proxy_url=lambda u: u,
        logger=__import__("logging").getLogger("test"),
    )
    elapsed = time.perf_counter() - started
    # Google + 2 articles en parallèle : ~0,4 s et non 1,2 s.
    assert elapsed < 0.9
    assert photos[0]["url"] == "https://g/1.jpg" and len(photos) == 4


def test_slow_photo_source_is_abandoned_after_budget(monkeypatch):
    import time

    from services import image_topics

    monkeypatch.setattr(image_topics, "PHOTO_SEARCH_BUDGET_SECONDS", 0.3)
    started = time.perf_counter()
    photos = image_topics.fetch_topic_images(
        "photos de Thiès budget-test",
        {"places": []},
        normalize=lambda v: str(v or "").lower(),
        should_fetch_images=lambda m: True,
        topic_wikipedia_titles=lambda m, n: ["Thiès"],
        knowledge_image_titles=lambda m, n: [],
        fetch_commons_images=lambda t, limit=4: [{"url": "https://upload.wikimedia.org/c.jpg"}],
        fetch_google_images=lambda t, limit=4: time.sleep(2) or [],
        fetch_article_images=lambda t, limit=4: [],
        fetch_city_image=lambda t: None,
        image_proxy_url=lambda u: u,
        logger=__import__("logging").getLogger("test"),
    )
    assert time.perf_counter() - started < 1.5
    assert photos and photos[0]["url"].endswith("c.jpg")


def test_wikimedia_requests_identify_the_site_with_a_contact(monkeypatch):
    # Wikimédia refuse (403) les agents génériques venant d'hébergeurs cloud.
    from services import images

    monkeypatch.setenv("CONTACT_EMAIL", "contact@teranga-ai.fr")
    agent = images.wikimedia_user_agent()
    assert agent.startswith("TerangaAI/1.0 (https://teranga-ai.fr/; contact@teranga-ai.fr)")
    monkeypatch.setenv("CONTACT_EMAIL", "pas un mail (injection)")
    assert "injection" not in images.wikimedia_user_agent()

    seen = []

    def opener(req, timeout=5):
        seen.append(req.get_header("User-agent"))
        raise OSError("réseau coupé")

    try:
        images.fetch_article_images("Lieu_sans_cache_ua", urlopen_fn=opener)
    except OSError:
        pass
    assert seen and all(agent.startswith("TerangaAI/1.0 (https://teranga-ai.fr/") for agent in seen)
