"""Topic image orchestration independent from Flask request handling."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence


def knowledge_image_titles(
    message: object,
    knowledge: Mapping[str, object],
    *,
    normalize: Callable[[object], str],
    limit: int = 4,
) -> list[str]:
    text_value = normalize(message)
    titles: list[str] = []

    for region in knowledge.get("regions", []) or []:
        if not isinstance(region, Mapping):
            continue
        candidates = [
            region.get("name", ""),
            *(region.get("places", []) or []),
            *(region.get("highlights", []) or []),
            *(region.get("image_queries", []) or []),
        ]
        if any(normalize(candidate) and normalize(candidate) in text_value for candidate in candidates):
            for candidate in candidates:
                if candidate and str(candidate) not in titles:
                    titles.append(str(candidate))
                    if len(titles) >= limit:
                        return titles

    for place in knowledge.get("places", []) or []:
        if not isinstance(place, Mapping):
            continue
        candidates = [place.get("name", ""), *(place.get("image_queries", []) or [])]
        if any(normalize(candidate) and normalize(candidate) in text_value for candidate in candidates):
            for candidate in candidates:
                if candidate and str(candidate) not in titles:
                    titles.append(str(candidate))
                    if len(titles) >= limit:
                        return titles
    return titles


def fetch_topic_images(
    message: object,
    knowledge: Mapping[str, object],
    *,
    normalize: Callable[[object], str],
    should_fetch_images: Callable[[object], bool],
    topic_wikipedia_titles: Callable[[object, int], Sequence[str]],
    knowledge_image_titles: Callable[[object, int], Sequence[str]] | None = None,
    fetch_commons_images: Callable[..., list[dict]],
    fetch_google_images: Callable[..., list[dict]] | None = None,
    fetch_city_image: Callable[[str], dict | None],
    image_proxy_url: Callable[[object], str],
    logger,
    max_photos: int = 8,
) -> list[dict] | None:
    text_value = normalize(message)
    if not should_fetch_images(message):
        return None

    specific_titles: list[str] = []
    for place in knowledge.get("places", []) or []:
        if not isinstance(place, Mapping):
            continue
        name = normalize(str(place.get("name", "")))
        aliases = [name]
        if name.startswith("ile de "):
            aliases.append(name[7:])
            if name == "ile de goree":
                aliases.append("gore")
        if name.startswith("île de "):
            aliases.append(name[7:])
        if any(alias and alias in text_value for alias in aliases):
            specific_titles.extend(
                str(query)
                for query in (place.get("image_queries") or [])
                if query
            )

    titles = (
        specific_titles
        if specific_titles
        else (knowledge_image_titles(message, 4) if knowledge_image_titles else globals()["knowledge_image_titles"](message, knowledge, normalize=normalize, limit=4))
        + list(topic_wikipedia_titles(message, 4))
    )
    if not titles:
        titles = ["Dakar Sénégal"]

    photos: list[dict] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()

    # Google Images is the primary provider for chat visual requests. One
    # focused query is enough to return a larger, faster gallery without
    # multiplying outbound image-search calls.
    primary_title = next((str(title or "").strip() for title in titles if str(title or "").strip()), "Dakar Sénégal")
    if fetch_google_images:
        try:
            candidates = fetch_google_images(primary_title, limit=max_photos)
        except Exception:
            logger.exception("Erreur recherche Google Images pour %s", primary_title)
            candidates = []
        for photo in candidates:
            if not photo:
                continue
            photo["search_query"] = primary_title
            src = photo.get("url", "")
            if not src or src in seen_urls:
                continue
            seen_urls.add(src)
            photos.append(photo)
            if len(photos) >= max_photos:
                return photos

    # Wikimedia remains a relevance-oriented fallback when Google returns too
    # few results or is temporarily unavailable.
    for title in titles:
        title = str(title or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        try:
            candidates = fetch_commons_images(title, limit=min(4, max_photos - len(photos)))
        except Exception:
            logger.exception("Erreur recherche photos Commons pour %s", title)
            candidates = []
        if not candidates and len(photos) == 0:
            try:
                fallback = fetch_city_image(title)
                candidates = [fallback] if fallback else []
            except Exception:
                logger.exception("Erreur fallback photo pour %s", title)
                candidates = []
        for photo in candidates:
            if not photo:
                continue
            photo["search_query"] = title
            photo["display_url"] = image_proxy_url(photo.get("url", ""))
            src = photo.get("url", "")
            if not src or src in seen_urls:
                continue
            seen_urls.add(src)
            photos.append(photo)
            if len(photos) >= max_photos:
                return photos

    return photos or None
