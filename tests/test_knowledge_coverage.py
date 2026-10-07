"""Chaque lieu, plat et région de la base est retrouvé quand on le nomme.

Un nouveau lieu ajouté à data/senegal_knowledge.json est testé automatiquement :
s'il n'est pas dans les 3 premiers « LIEUX PERTINENTS » quand on demande
« Que voir à <nom> ? », l'IA risque de répondre sur un autre lieu.
"""

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app, parse_chat_payload  # noqa: E402

KNOWLEDGE = json.loads((Path(__file__).resolve().parents[1] / "data" / "senegal_knowledge.json").read_text(encoding="utf-8"))


def _context(question, lang="fr"):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    return payload["instructions"].replace(question, " ")


@pytest.mark.parametrize("place", KNOWLEDGE["places"], ids=[p["id"] for p in KNOWLEDGE["places"]])
def test_each_place_is_found_by_name(place):
    context = _context(f"Que voir à {place['name']} ?")
    assert "LIEUX PERTINENTS :" in context
    top = [line for line in context.split("LIEUX PERTINENTS :", 1)[1].splitlines() if line.startswith("- ")][:3]
    assert any(line.startswith(f"- {place['name']}:") for line in top), top


@pytest.mark.parametrize("dish", KNOWLEDGE["dishes"], ids=[d["name"] for d in KNOWLEDGE["dishes"]])
def test_each_dish_is_found_by_name(dish):
    assert dish["name"] in _context(f"C'est quoi le {dish['name'].split(' (')[0]} ?")


@pytest.mark.parametrize("region", KNOWLEDGE["regions"], ids=[r["id"] for r in KNOWLEDGE["regions"]])
def test_each_region_is_found_by_name(region):
    assert f"- {region['name']}:" in _context(f"Que faire dans la région de {region['name']} ?")
