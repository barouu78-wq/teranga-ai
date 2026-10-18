"""« À découvrir » de l'accueil : deux lieux de la base tirés au hasard à chaque visite.

Le tirage se fait côté serveur, à chaque affichage de l'accueil : les deux cartes changent d'une visite à l'autre,
sans script et sans saut d'affichage. Nom, région et requête photo viennent de data/senegal_knowledge.json, avec la
même requête que la fiche du lieu (services/places.py) : la carte montre la photo de la fiche.
"""

from __future__ import annotations

import secrets
from html import escape

# Vitrine : des lieux connus et photographiés, de régions variées (villes, patrimoine, nature, plages). Chaque
# identifiant doit exister dans la base (tests/test_discover.py).
DISCOVER_IDS = (
    "goree", "saint-louis", "lac-rose", "djoudj", "saloum", "touba", "cap-skirring", "joal-fadiouth",
    "dakar-renaissance", "dindefello", "niokolo-koba", "desert-de-lompoul", "langue-de-barbarie", "ile-de-ngor",
    "ziguinchor", "carabane", "bassari", "reserve-de-bandia", "podor", "mosquee-divinite", "thies",
)
# Noms trop longs pour une carte de 170 px de large : un alias de la base, ou le nom de la presqu'île pour la
# Langue de Barbarie (la fiche, elle, garde le nom complet).
_SHORT_NAMES = {
    "djoudj": "Djoudj",
    "niokolo-koba": "Niokolo-Koba",
    "dakar-renaissance": "Monument de la Renaissance",
    "langue-de-barbarie": "Langue de Barbarie",
}
# Fond affiché pendant le chargement de la photo (les deux teintes de la maquette).
_COLORS = ("#2e5d63", "#8a4b5c")
_RANDOM = secrets.SystemRandom()


def discover_pool(knowledge: dict) -> list[dict]:
    """Les lieux de la vitrine, dans l'ordre de DISCOVER_IDS, avec ce que la carte affiche."""
    unesco = set(knowledge.get("unesco_world_heritage") or ())
    by_id = {place.get("id"): place for place in knowledge.get("places") or ()}
    pool = []
    for place_id in DISCOVER_IDS:
        place = by_id.get(place_id)
        if not place:
            continue
        full_name = str(place.get("name", ""))
        region = str(place.get("region", ""))
        is_unesco = full_name in unesco
        pool.append({
            "id": place_id,
            # « Lac Rose / Lac Retba » → « Lac Rose ».
            "name": _SHORT_NAMES.get(place_id) or full_name.split(" / ")[0].strip(),
            "region": region,
            "unesco": is_unesco,
            "sub": f"{region} · UNESCO" if is_unesco else f"Région de {region}",
            "query": str((place.get("image_queries") or [full_name])[0]),
            "title": full_name,
        })
    return pool


def pick_two(pool: list[dict], rng=_RANDOM) -> list[dict]:
    """Deux lieux différents, de deux régions différentes quand c'est possible."""
    if len(pool) < 2:
        return list(pool)
    first = rng.choice(pool)
    others = [place for place in pool if place["region"] != first["region"]]
    others = others or [place for place in pool if place["id"] != first["id"]]
    return [first, rng.choice(others)]


def tiles_html(places: list[dict]) -> str:
    """Cartes de l'accueil ; home.js charge ensuite la photo (data-photo, data-title) et traduit la région."""
    tiles = []
    for index, place in enumerate(places):
        unesco = ' data-unesco="1"' if place.get("unesco") else ""
        tiles.append(
            f'<a class="place-tile" href="/lieux/{escape(place["id"])}" data-photo="{escape(place["query"])}" '
            f'data-title="{escape(place["title"])}" data-region="{escape(place["region"])}"{unesco}>'
            f'<span class="place-tile-img" style="background:{_COLORS[index % len(_COLORS)]}"></span>'
            f'<strong>{escape(place["name"])}</strong><small>{escape(place["sub"])}</small></a>'
        )
    return "\n    ".join(tiles)
