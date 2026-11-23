"""Fiches de lieux : « À voir aussi » par distance réelle (23 novembre 2026).

Search Console (30 jours, via Windsor.ai) : /lieux/mbacke (position 12), /lieux/kaffrine (10) et
/lieux/reserve-de-bandia (53) sont les pages que Google montre le plus, mais seules 3 ou 4 pages du site y menaient :
« À voir aussi » prenait les 6 premiers lieux de la région dans l'ordre du fichier, si bien que Saly ou Mbour, à
quelques kilomètres de Bandia, n'y renvoyaient pas. Les coordonnées de la base suffisent à trier par distance.
"""

import json
import math
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app  # noqa: E402
from services.places import nearby_places  # noqa: E402

PLACES = json.loads((Path(__file__).resolve().parent.parent / "data" / "senegal_knowledge.json").read_text())["places"]
B = "http://localhost"


def _place(pid):
    return next(p for p in PLACES if p["id"] == pid)


def _km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def test_les_lieux_proches_sont_tries_par_distance_et_sans_le_lieu_lui_meme():
    for place in PLACES:
        proches = nearby_places(place, PLACES)
        assert place not in proches and len(proches) <= 6
        distances = [_km(place, o) for o in proches]
        assert distances == sorted(distances), place["id"]


def test_les_pages_proches_menent_aux_fiches_que_google_montre():
    client = app.test_client()
    attendus = {"saly": "/lieux/reserve-de-bandia", "touba": "/lieux/mbacke", "koungheul": "/lieux/kaffrine"}
    for source, lien in attendus.items():
        html = client.get(f"/lieux/{source}", base_url=B).get_data(as_text=True)
        assert f'href="{lien}"' in html, (source, lien)
    html = client.get("/lieux/saly", base_url=B).get_data(as_text=True)
    assert "À voir aussi à proximité" in html


def test_plus_de_pages_menent_a_bandia_mbacke_et_kaffrine():
    client = app.test_client()
    pages = ["/lieux/" + p["id"] for p in PLACES]
    for cible, minimum in (("/lieux/reserve-de-bandia", 5), ("/lieux/mbacke", 4), ("/lieux/kaffrine", 4)):
        n = sum(f'href="{cible}"' in client.get(u, base_url=B).get_data(as_text=True) for u in pages if u != cible)
        assert n >= minimum, (cible, n)
