"""Skills du projet (`.claude/skills/`) : chargeables, listés dans AGENTS.md, et licence respectée pour les emprunts.

Un skill dont l'en-tête est faux n'est pas chargé par Claude Code. Un skill absent du tableau d'AGENTS.md n'est pas
connu des autres agents de code. Les méthodes adaptées de Superpowers (licence MIT, choix du propriétaire du
12 octobre 2026) doivent garder la mention de copyright et ne jamais ajouter de crochet de session.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
LICENCE = SKILLS / "LICENCE-superpowers.txt"
ADAPTES = ("deboguer-methodiquement", "tester-d-abord", "verifier-avant-d-annoncer", "recevoir-une-relecture")
NOMS = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))


def en_tete(nom):
    texte = (SKILLS / nom / "SKILL.md").read_text(encoding="utf-8")
    bloc = re.match(r"---\n(.*?)\n---\n", texte, re.S)
    assert bloc, f"{nom} : en-tête --- absent"
    return dict(re.findall(r"^(\w+):\s*(.+)$", bloc.group(1), re.M)), texte


def test_les_methodes_adaptees_sont_presentes():
    assert set(ADAPTES) <= set(NOMS)


@pytest.mark.parametrize("nom", NOMS)
def test_chaque_skill_a_un_en_tete_chargeable(nom):
    champs, _ = en_tete(nom)
    assert champs.get("name") == nom  # le nom doit être celui du dossier
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nom) and len(nom) <= 64
    assert 20 <= len(champs.get("description", "")) <= 1024
    # Un « : » suivi d'une espace rend l'en-tête illisible pour un lecteur YAML strict (cas d'ajouter-un-lieu,
    # corrigé le 15 octobre 2026) ; Claude Code le tolère aujourd'hui, d'autres outils non.
    assert ": " not in champs["description"]


@pytest.mark.parametrize("nom", NOMS)
def test_chaque_skill_est_dans_le_tableau_d_agents_md(nom):
    assert f"| `{nom}` |" in AGENTS


@pytest.mark.parametrize("nom", ADAPTES)
def test_chaque_methode_adaptee_cite_sa_licence(nom):
    _, texte = en_tete(nom)
    assert "Superpowers" in texte and ".claude/skills/LICENCE-superpowers.txt" in texte
    assert f"- {nom}" in LICENCE.read_text(encoding="utf-8")


def test_la_licence_mit_d_origine_est_conservee():
    licence = LICENCE.read_text(encoding="utf-8")
    assert "MIT License" in licence and "Copyright (c) 2025 Jesse Vincent" in licence
    assert "The above copyright notice and this permission notice shall be included" in licence
    assert re.search(r"commit [0-9a-f]{40}", licence)  # version exacte reprise


def test_aucun_script_ni_crochet_de_superpowers():
    for nom in ADAPTES:
        fichiers = sorted(p.name for p in (SKILLS / nom).iterdir())
        assert fichiers == ["SKILL.md"], (nom, fichiers)  # seulement le texte, aucun script
    reglages = ROOT / ".claude" / "settings.json"
    if reglages.exists():
        assert "superpowers" not in reglages.read_text(encoding="utf-8").lower()
