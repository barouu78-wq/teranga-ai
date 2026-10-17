"""Un mot commun du nom d'un lieu (« village », « musée », « Senghor ») ne suffit pas à le nommer."""

import json
from pathlib import Path

import pytest

from services.senegal_knowledge import format_senegal_knowledge, load_senegal_knowledge

DATA = Path(__file__).resolve().parents[1] / "data" / "senegal_knowledge.json"

# Deux fiches de test au nom fait de mots communs, ajoutées en fin de base comme le seraient de nouveaux lieux.
EXTRA = [
    {"id": "test-village-des-arts", "name": "Village des Arts", "type": "cultural_site", "region": "Dakar",
     "summary": "Ateliers d'artistes.", "sources": ["https://example.org"]},
    {"id": "test-musee-senghor", "name": "Musée Léopold Sédar Senghor", "type": "museum", "region": "Dakar",
     "summary": "Maison du président-poète.", "sources": ["https://example.org"]},
]


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    base = json.loads(DATA.read_text(encoding="utf-8"))
    base["places"] += EXTRA
    path = tmp_path_factory.mktemp("base") / "senegal_knowledge.json"
    path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    return load_senegal_knowledge(path)


def _lieux(context: str) -> list[str]:
    """Noms des lieux retenus (section « LIEUX PERTINENTS »)."""
    section = context.split("LIEUX PERTINENTS :", 1)[1].split("\n")[1:]
    names = []
    for line in section:
        if not line.startswith("- "):
            break
        names.append(line[2:].split(":", 1)[0])
    return names


def test_un_village_a_visiter_ramene_de_vrais_villages(data):
    lieux = _lieux(format_senegal_knowledge(data, "un village à visiter au Sénégal"))
    assert len(lieux) >= 3, lieux
    assert lieux[0] != "Village des Arts", lieux


def test_ou_est_ne_senghor_garde_joal(data):
    assert any("Joal" in lieu for lieu in _lieux(format_senegal_knowledge(data, "Où est né Senghor ?")))


def test_le_lieu_reste_nomme_avec_deux_mots_de_son_nom(data):
    assert "Village des Arts" in format_senegal_knowledge(data, "le Village des Arts")
    assert "Musée Léopold Sédar Senghor" in format_senegal_knowledge(data, "visiter le musée Senghor")


def test_une_question_sur_les_musees_ramene_les_musees(data):
    lieux = _lieux(format_senegal_knowledge(data, "quels musées visiter à Dakar ?"))
    assert lieux[0].startswith("Musée"), lieux
    assert "Musée Léopold Sédar Senghor" in lieux, lieux


def test_un_musee_nomme_ne_ramene_que_lui(data):
    lieux = _lieux(format_senegal_knowledge(data, "musée des civilisations noires"))
    assert lieux == ["Musée des Civilisations Noires"], lieux
