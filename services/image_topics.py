"""Topic image orchestration independent from Flask request handling."""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable, Mapping, Sequence

from .photo_search import term_position


# Clé : requête principale, titres cherchés, nombre de photos, fournisseurs.
_TOPIC_IMAGE_CACHE: dict[tuple, tuple[float, list[dict]]] = {}
_TOPIC_IMAGE_CACHE_TTL = 300.0
_TOPIC_IMAGE_CACHE_MAX = 128


def _cached_topic_images(key: tuple) -> list[dict] | None:
    cached = _TOPIC_IMAGE_CACHE.get(key)
    if not cached:
        return None
    stored_at, photos = cached
    if time.monotonic() - stored_at >= _TOPIC_IMAGE_CACHE_TTL:
        _TOPIC_IMAGE_CACHE.pop(key, None)
        return None
    return [dict(photo) for photo in photos]


def _store_topic_images(key: tuple, photos: list[dict]) -> None:
    if len(_TOPIC_IMAGE_CACHE) >= _TOPIC_IMAGE_CACHE_MAX:
        oldest_key = min(list(_TOPIC_IMAGE_CACHE.items()), key=lambda entry: entry[1][0])[0]
        _TOPIC_IMAGE_CACHE.pop(oldest_key, None)
    _TOPIC_IMAGE_CACHE[key] = (time.monotonic(), [dict(photo) for photo in photos])


def _term_position(text: object, candidate: object, normalize: Callable[[object], str]) -> int | None:
    """Où le lieu est cité dans le message (graphies équivalentes : Goree/Gorée, St/Saint-Louis)."""
    return term_position(normalize(text), normalize(candidate).strip())


# Lieux cités comme repère ou exclus : « près de Mbour », « pas de Dakar », « depuis Dakar »…
# Ce ne sont pas les lieux dont on veut des photos.
_SECONDARY_MARKER = re.compile(
    r"(?<!\w)(?:pas|sans|non|hors|sauf|a part|autre que|plutot que|loin|pres|proche|a cote|autour|"
    r"depuis|a partir|au depart|a proximite|not|without|except|excluding|instead of|rather than|"
    r"near|around|next to|close to|far from)(?!\w)"
)
_CLAUSE_END = re.compile(r"[,;.!?]|(?<!\w)(?:mais|but|plutot|rather)(?!\w)")


def _plain_letters(text: str) -> str:
    """Minuscules sans accents, de même longueur que `text` (pour repérer des positions)."""
    out = []
    for char in text:
        base = "".join(c for c in unicodedata.normalize("NFD", char) if not unicodedata.combining(c)).lower()
        out.append(base if len(base) == 1 else char)
    return "".join(out)


def _focus_clause(message: object) -> str:
    """Message sans les lieux de repère ou exclus.

    « photos de Saly près de Mbour » → « photos de Saly » ;
    « photos de Dakar et pas de Saly » → « photos de Dakar et ».
    """
    raw = str(message or "")
    flat = _plain_letters(raw)
    kept, cursor = [], 0
    for marker in _SECONDARY_MARKER.finditer(flat):
        if marker.start() < cursor:
            continue
        end = _CLAUSE_END.search(flat, marker.end())
        kept.append(raw[cursor:marker.start()])
        cursor = end.start() if end else len(raw)
    kept.append(raw[cursor:])
    return " ".join("".join(kept).split())


_SHORT_NAME = re.compile(r"^.*?\b(?:de|du|des|d')\s+(?:la\s+|l')?(.+)$", re.IGNORECASE)


def _short_place_name(name: str) -> str:
    """« Île de Gorée » → « Gorée » ; « Parc national de la Langue de Barbarie » → « Langue de Barbarie »."""
    match = _SHORT_NAME.match(str(name or "").strip())
    short = match.group(1).strip() if match else ""
    return short if len(short) >= 4 else ""


def knowledge_image_titles(
    message: object,
    knowledge: Mapping[str, object],
    *,
    normalize: Callable[[object], str],
    limit: int = 4,
) -> list[str]:
    text_value = normalize(message)
    titles: list[str] = []

    def add(title) -> bool:
        """Ajoute un titre ; True quand la liste est pleine."""
        if title and str(title) not in titles:
            titles.append(str(title))
        return len(titles) >= limit

    def position(candidate):
        return _term_position(text_value, candidate, normalize)

    region_names = {
        normalize(region.get("name", ""))
        for region in knowledge.get("regions", []) or []
        if isinstance(region, Mapping)
    }

    # Le lieu précis passe avant sa région (« désert de Lompoul » avant « Louga »).
    # Le nom court (« Gorée » pour « Île de Gorée ») sert aussi à reconnaître le
    # lieu, mais seules ses requêtes d'images sont proposées.
    place_hits = []
    for order, place in enumerate(knowledge.get("places", []) or []):
        if not isinstance(place, Mapping):
            continue
        name = str(place.get("name", ""))
        candidates = [name, *(place.get("image_queries", []) or [])]
        short = _short_place_name(name)
        if short and normalize(short) in region_names:
            # « Corniche de Dakar » ne doit pas capter toute demande sur Dakar.
            short = ""
        found = [p for p in (position(c) for c in candidates) if p is not None]
        if not found and short and position(short) is not None:
            found = [position(short)]
            candidates = [short, *(c for c in candidates if c)]
        if found:
            place_hits.append((min(found), order, candidates))
    # Dans l'ordre de la phrase, pas dans celui du fichier de données.
    for _position, _order, candidates in sorted(place_hits, key=lambda hit: hit[:2]):
        for candidate in candidates:
            if add(candidate):
                return titles

    # Une région n'apporte que ce qui est cité : « Pikine » ne devient ni « Dakar » ni
    # « Gorée » parce que la région Dakar les range ensemble. Un lieu de la région est
    # précisé par « Sénégal », comme les requêtes d'images de la base. Un thème écrit
    # tout en minuscules dans la base (« plages », « savane », « mangroves ») n'est pas
    # un lieu : il reste une recherche libre, sans article Wikipédia du monde entier.
    region_hits = []
    for order, region in enumerate(knowledge.get("regions", []) or []):
        if not isinstance(region, Mapping):
            continue
        for candidate in [
            region.get("name", ""),
            *(region.get("places", []) or []),
            *(region.get("highlights", []) or []),
            *(region.get("image_queries", []) or []),
        ]:
            if not candidate or str(candidate) == str(candidate).lower():
                continue
            where = position(candidate)
            if where is None:
                continue
            bare = normalize(candidate) in region_names or "senegal" in normalize(candidate)
            region_hits.append((where, order, str(candidate) if bare else f"{candidate} Sénégal"))
    for _position, _order, title in sorted(region_hits, key=lambda hit: hit[:2]):
        if add(title):
            return titles
    return titles


def _build_primary_query(
    message: object,
    specific_titles: Sequence[str],
    discovered_titles: Sequence[str],
    normalize: Callable[[object], str],
) -> str:
    """Build an image query from the actual request instead of a generic Dakar fallback."""
    specific = next((str(title).strip() for title in specific_titles if str(title).strip()), "")
    if specific:
        return specific

    discovered = next((str(title).strip() for title in discovered_titles if str(title).strip()), "")
    if discovered:
        return discovered

    raw = str(message or "").strip()
    normalized = normalize(raw)
    if not normalized:
        return "Sénégal"

    # Keep the user's visual intent while removing conversational filler.
    filler = (
        "montre moi", "montre-moi", "montre", "affiche", "affiche moi",
        "affiche-moi", "fais voir", "je veux voir", "donne moi", "donne-moi",
        "des photos de", "des photos du", "des photos d", "photo de", "photos de",
        "photo du", "photos du", "photo d", "photos d",
    )
    filler = filler + (
        "des photos", "des images de", "des images", "les photos de", "les photos",
        "photos", "photo", "images", "image", "stp", "s'il te plait", "svp",
    )
    query = raw
    # « montre moi des photos de plage » : on retire toutes les formules,
    # pas seulement la première (sinon « des photos de plage » partait à Google).
    changed = True
    while changed:
        changed = False
        for prefix in sorted(filler, key=len, reverse=True):
            if normalize(query).startswith(normalize(prefix) + " "):
                query = query[len(prefix):].strip(" :,-")
                changed = True
                break
    if not normalize(query):
        query = "Sénégal"
    if "senegal" not in normalize(query):
        query = f"{query} Sénégal"
    return query[:180]


# Recherches d'images en parallèle : la plus lente fixe la durée, pas la somme.
_PHOTO_POOL = None
PHOTO_SEARCH_BUDGET_SECONDS = 9.0
PHOTO_TOTAL_BUDGET_SECONDS = 10.5


def _run_parallel(jobs, logger, budget=None):
    """{(source, titre): résultat} ; une source en erreur ou trop lente est ignorée."""
    global _PHOTO_POOL
    if not jobs:
        return {}
    if len(jobs) == 1:
        kind, title, call = jobs[0]
        try:
            return {(kind, title): call()}
        except Exception:
            logger.exception("Erreur recherche photos %s pour %s", kind, title)
            return {}
    from concurrent.futures import ThreadPoolExecutor, wait

    if _PHOTO_POOL is None:
        _PHOTO_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="photos")
    futures = {_PHOTO_POOL.submit(call): (kind, title) for kind, title, call in jobs}
    done, _pending = wait(futures, timeout=PHOTO_SEARCH_BUDGET_SECONDS if budget is None else budget)
    results = {}
    for future in done:
        kind, title = futures[future]
        try:
            results[(kind, title)] = future.result()
        except Exception:
            logger.exception("Erreur recherche photos %s pour %s", kind, title)
    return results


def _specific_place_titles(
    text: object,
    knowledge: Mapping[str, object],
    normalize: Callable[[object], str],
) -> list[str]:
    """Requêtes d'images des lieux de la base cités dans `text`, dans l'ordre de la phrase."""
    text_value = normalize(text)
    hits = []
    goree_in_base = False
    places = [place for place in knowledge.get("places", []) or [] if isinstance(place, Mapping)]
    for order, place in enumerate(places):
        name = normalize(str(place.get("name", "")))
        aliases = [name]
        if name.startswith("ile de "):
            aliases.append(name[7:])
            if name == "ile de goree":
                aliases.append("gore")
        if name.startswith("île de "):
            aliases.append(name[7:])
        # Autres noms du lieu (« Pink Lake », « Goree Island »).
        aliases.extend(normalize(str(alias)) for alias in (place.get("aliases") or []) if str(alias).strip())
        found = [p for p in (_term_position(text_value, alias, normalize) for alias in aliases) if p is not None]
        if found:
            image_queries = [str(query) for query in (place.get("image_queries") or []) if query]
            # A recognized place must remain specific even when its optional
            # image_queries metadata is empty. This also handles short aliases
            # such as "gore" for Île de Gorée without falling back to Dakar.
            hits.append((min(found), order, image_queries or [str(place.get("name", "")).strip()]))
            goree_in_base = goree_in_base or term_position(place.get("name", ""), "goree") is not None

    # Keep a few high-value Senegal place aliases resilient even when
    # structured knowledge is incomplete. These are search hints, not a
    # replacement for the knowledge base: when the base already gave Gorée,
    # nothing is added.
    goree = [p for p in (_term_position(text_value, alias, normalize) for alias in ("gore", "goree")) if p is not None]
    if goree and not goree_in_base:
        hits.append((min(goree), len(places), ["Île de Gorée"]))

    # Dans l'ordre de la phrase, pas dans celui du fichier de données.
    return [title for _position, _order, queries in sorted(hits, key=lambda hit: hit[:2]) for title in queries]


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
    fetch_article_images: Callable[..., list[dict]] | None = None,
    fetch_city_image: Callable[[str], dict | None],
    image_proxy_url: Callable[[object], str],
    logger,
    max_photos: int = 8,
) -> list[dict] | None:
    if not should_fetch_images(message):
        return None

    def resolve(text):
        """(lieux précis de la base, sinon régions/sujets Wikipédia) cités dans `text`."""
        specific = _specific_place_titles(text, knowledge, normalize)
        if specific:
            return specific, []
        discovered = (
            knowledge_image_titles(text, 4)
            if knowledge_image_titles
            else globals()["knowledge_image_titles"](text, knowledge, normalize=normalize, limit=4)
        )
        return [], list(discovered) + list(topic_wikipedia_titles(text, 4))

    # Les lieux de repère ou exclus (« près de Mbour », « pas de Saly ») ne sont pas
    # ceux dont on veut des photos. Sans autre lieu cité, on garde le message entier.
    focus = _focus_clause(message)
    specific_titles, discovered_titles = resolve(focus)
    if not specific_titles and not discovered_titles and focus != " ".join(str(message or "").split()):
        specific_titles, discovered_titles = resolve(message)

    primary_title = _build_primary_query(message, specific_titles, discovered_titles, normalize)
    titles = list(specific_titles or discovered_titles or [primary_title])

    photos: list[dict] = []
    seen_urls: set[str] = set()

    # Cache by the actual visual request (query and places searched) so different
    # requests never reuse another place's gallery.
    cache_key = (
        normalize(primary_title),
        tuple(normalize(title) for title in titles[:4]),
        max_photos,
        id(fetch_google_images),
        id(fetch_article_images),
        id(fetch_commons_images),
        id(fetch_city_image),
    )
    cached = _cached_topic_images(cache_key)
    if cached is not None:
        return cached

    def add(candidates, query, proxied):
        for photo in candidates or []:
            src = (photo or {}).get("url", "")
            if not src or src in seen_urls or len(photos) >= max_photos:
                continue
            photo["search_query"] = query
            if proxied:
                photo["display_url"] = image_proxy_url(src)
            seen_urls.add(src)
            photos.append(photo)

    def finish():
        if photos:
            _store_topic_images(cache_key, photos)
            return [dict(photo) for photo in photos]
        return None

    # Étape 1, en parallèle : Google et les photos des articles Wikipédia des
    # lieux reconnus (choisies par des rédacteurs ; jamais pour une requête
    # libre comme « plage », dont l'article montrerait le monde entier).
    # Budget total (étapes 1 et 2) sous le délai d'attente du chat (12 s) : des
    # photos trouvées trop tard seraient perdues pour la réponse.
    deadline = time.monotonic() + PHOTO_TOTAL_BUDGET_SECONDS
    article_titles = [str(t or "").strip() for t in list(specific_titles or discovered_titles)[:2]]
    article_titles = [t for t in dict.fromkeys(article_titles) if t] if fetch_article_images else []
    jobs = []
    if fetch_google_images:
        jobs.append(("google", primary_title, lambda: fetch_google_images(primary_title, limit=max_photos)))
    for title in article_titles:
        jobs.append(("article", title, lambda title=title: fetch_article_images(title, limit=max_photos)))
    results = _run_parallel(jobs, logger)
    add(results.get(("google", primary_title)), primary_title, proxied=False)
    for title in article_titles:
        add(results.get(("article", title)), title, proxied=True)
    if len(photos) >= 4:
        return finish()

    # Étape 2 (seulement s'il manque des photos) : recherche Commons, en
    # parallèle sur les premiers titres.
    commons_titles = [t for t in dict.fromkeys(str(t or "").strip() for t in titles) if t][:4]
    remaining = deadline - time.monotonic()
    if remaining < 1:
        return finish()
    jobs = [("commons", t, lambda t=t: fetch_commons_images(t, limit=4)) for t in commons_titles]
    results = _run_parallel(jobs, logger, budget=min(PHOTO_SEARCH_BUDGET_SECONDS, remaining))
    for title in commons_titles:
        add(results.get(("commons", title)), title, proxied=True)
    for title in commons_titles:
        if photos or time.monotonic() >= deadline:
            break
        try:
            fallback = fetch_city_image(title)
        except Exception:
            logger.exception("Erreur fallback photo pour %s", title)
            fallback = None
        add([fallback] if fallback else [], title, proxied=True)
    return finish()
