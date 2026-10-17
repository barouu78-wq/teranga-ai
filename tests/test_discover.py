"""« À découvrir » de l'accueil : deux lieux de la base, tirés au hasard à chaque visite (services/discover.py)."""

import os
import random
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from home_source import home_source  # noqa: E402
from services import discover  # noqa: E402

POOL = discover.discover_pool(app_module.SENEGAL_KNOWLEDGE)
TILE = re.compile(
    r'<a class="place-tile" href="/lieux/([a-z0-9-]+)" data-photo="([^"]+)" data-title="([^"]+)" '
    r'data-region="([^"]+)"( data-unesco="1")?>'
)


def test_chaque_lieu_de_la_vitrine_existe_dans_la_base_et_a_sa_fiche():
    ids = {place["id"] for place in app_module.SENEGAL_KNOWLEDGE["places"]}
    assert set(discover.DISCOVER_IDS) <= ids, set(discover.DISCOVER_IDS) - ids
    assert len(POOL) == len(discover.DISCOVER_IDS) >= 12
    client = app_module.app.test_client()
    for place in POOL:
        assert client.get(f"/lieux/{place['id']}").status_code == 200, place["id"]


def test_la_vitrine_couvre_plusieurs_regions_et_des_villes():
    assert len({place["region"] for place in POOL}) >= 6
    assert {"saint-louis", "ziguinchor", "touba"} <= set(discover.DISCOVER_IDS)


def test_nom_court_et_sous_titre_viennent_de_la_base():
    by_id = {place["id"]: place for place in POOL}
    assert by_id["goree"]["name"] == "Île de Gorée" and by_id["goree"]["sub"] == "Dakar · UNESCO"
    assert by_id["lac-rose"]["name"] == "Lac Rose" and by_id["lac-rose"]["sub"] == "Région de Dakar"
    assert by_id["lac-rose"]["query"] == "Lac Rose Sénégal"  # même photo que la fiche du lieu
    assert by_id["saint-louis"]["unesco"] is True and by_id["touba"]["unesco"] is False


def test_deux_lieux_differents_de_deux_regions():
    rng = random.Random(7)
    for _ in range(200):
        first, second = discover.pick_two(POOL, rng)
        assert first["id"] != second["id"] and first["region"] != second["region"]


def test_les_noms_sont_echappes():
    piege = [{"id": "x", "name": 'A<b>"', "region": "R&D", "unesco": False, "sub": "Région de R&D",
              "query": 'q"<', "title": "t<"}]
    html = discover.tiles_html(piege)
    assert "<b>" not in html and 'q"<' not in html and "R&amp;D" in html


def test_l_accueil_montre_deux_lieux_de_la_vitrine():
    html = app_module.app.test_client().get("/").get_data(as_text=True)
    assert "__DISCOVER_TILES__" not in html
    tiles = TILE.findall(html)
    assert len(tiles) == 2
    assert {tile[0] for tile in tiles} <= set(discover.DISCOVER_IDS)


def test_les_lieux_changent_d_une_visite_a_l_autre():
    client = app_module.app.test_client()
    vus = set()
    for _ in range(40):
        vus.update(tile[0] for tile in TILE.findall(client.get("/").get_data(as_text=True)))
    assert len(vus) >= 6


def test_le_script_demande_la_photo_de_la_fiche_et_traduit_la_region():
    source = home_source()
    assert "'&title='+encodeURIComponent(tile.dataset.title" in source
    assert "regionOf:'Région de {r}'" in source and "regionOf:'{r} region'" in source
