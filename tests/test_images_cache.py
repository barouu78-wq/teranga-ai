import services.images as images


def test_fetch_city_image_uses_fresh_cache(monkeypatch):
    images._IMAGE_CACHE.clear()
    calls = []

    def wiki_summary(lang, title):
        calls.append((lang, title))
        return {"title": title, "thumbnail": {"source": "https://upload.wikimedia.org/example.jpg"}}

    first = images.fetch_city_image("Dakar", wiki_summary, images.usable_wiki_image, lambda value, limit: value[:limit])
    second = images.fetch_city_image("Dakar", wiki_summary, images.usable_wiki_image, lambda value, limit: value[:limit])

    assert first == second
    assert len(calls) == 1


def test_fetch_city_image_expires_cache(monkeypatch):
    images._IMAGE_CACHE.clear()
    clock = iter((100.0, 100.0, 1000.0, 1000.0))
    monkeypatch.setattr(images.time, "monotonic", lambda: next(clock))

    calls = []
    def wiki_summary(lang, title):
        calls.append((lang, title))
        return {"title": title, "thumbnail": {"source": "https://upload.wikimedia.org/example.jpg"}}

    images.fetch_city_image("Dakar", wiki_summary, images.usable_wiki_image, lambda value, limit: value[:limit])
    images.fetch_city_image("Dakar", wiki_summary, images.usable_wiki_image, lambda value, limit: value[:limit])

    assert len(calls) == 2


def test_fetch_city_image_cache_is_bounded(monkeypatch):
    images._IMAGE_CACHE.clear()
    monkeypatch.setattr(images, "_IMAGE_CACHE_MAX_ENTRIES", 2)
    monkeypatch.setattr(images.time, "monotonic", lambda: 100.0)

    def wiki_summary(lang, title):
        return {"title": title, "thumbnail": {"source": "https://upload.wikimedia.org/example.jpg"}}

    for title in ("Dakar", "Thiès", "Saint-Louis"):
        images.fetch_city_image(title, wiki_summary, images.usable_wiki_image, lambda value, limit: value[:limit])

    assert len(images._IMAGE_CACHE) == 2
    assert "Dakar" not in images._IMAGE_CACHE
