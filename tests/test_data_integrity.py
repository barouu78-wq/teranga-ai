"""Garde-fous sur les fichiers de données : une erreur de saisie casse le test, pas le site."""

import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def _load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_places_ids_and_names_are_unique_and_regions_exist():
    data = _load("senegal_knowledge.json")
    regions = {r["name"] for r in data["regions"]}
    ids = [p["id"] for p in data["places"]]
    names = [p["name"] for p in data["places"]]
    assert len(ids) == len(set(ids)), "identifiant de lieu en double"
    assert len(names) == len(set(names)), "nom de lieu en double"
    assert all(re.fullmatch(r"[a-z0-9-]+", i) for i in ids), "identifiant invalide (URL /lieux/<id>)"
    assert {p["region"] for p in data["places"]} <= regions
    for place in data["places"]:
        assert place.get("image_queries"), place["id"]
        for field in ("summary", "history", "access"):
            value = place.get(field)
            assert value is None or (isinstance(value, str) and value.strip() and "<" not in value), (place["id"], field)


def test_dossiers_and_phrases_are_well_formed():
    data = _load("senegal_knowledge.json")
    titles = [d["title"] for d in data["history_dossiers"]]
    assert len(titles) == len(set(titles))
    for dossier in data["history_dossiers"]:
        assert dossier["triggers"] and dossier["sections"], dossier["title"]
    assert all(p.get("wo") and p.get("fr") for p in data["wolof_phrases"])
    assert all(p.get("pu") and p.get("fr") for p in data["pulaar_phrases"])
    assert all(d.get("name") and d.get("text") for d in data["dishes"])


def test_people_are_unique_and_described():
    people = _load("senegal_people.json")["people"]
    names = [p["name"] for p in people]
    assert len(names) == len(set(names))
    assert all(p.get("period") and len(p.get("text", "")) > 40 for p in people)


def test_partners_file_is_valid():
    partners = _load("partners.json")["partners"]
    ids = [p["id"] for p in partners]
    assert len(ids) == len(set(ids))
    for partner in partners:
        assert partner.get("name") and partner.get("places"), partner
        assert not partner.get("url") or partner["url"].startswith("https://"), partner["id"]
        assert not partner.get("until") or re.fullmatch(r"\d{4}-\d{2}-\d{2}", partner["until"]), partner["id"]
