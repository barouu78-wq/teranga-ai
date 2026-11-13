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


# Compétences reprises de GitHub le 1er novembre 2026 (choix du propriétaire, « A ») : hallmark (design, Nutlope/hallmark)
# et ponytail (code minimal, DietrichGebert/ponytail), toutes deux sous licence MIT. Texte seulement : ni script, ni
# image, ni génération d'images payante (Together AI) ; les règles d'AGENTS.md priment.
REPRISES = {
    "LICENCE-hallmark.txt": ("Nutlope/hallmark", ("hallmark",)),
    "LICENCE-ponytail.txt": ("DietrichGebert/ponytail", ("ponytail", "ponytail-review", "ponytail-audit", "ponytail-debt")),
    # 13 novembre 2026 (« installe ce skill », propriétaire) : find-skills de vercel-labs/skills, texte seulement ; le
    # programme `npx skills` n'est ni installé ni lancé.
    "LICENCE-vercel-skills.txt": ("vercel-labs/skills", ("find-skills",)),
}


@pytest.mark.parametrize("fichier", sorted(REPRISES))
def test_chaque_reprise_garde_sa_licence_mit(fichier):
    depot, noms = REPRISES[fichier]
    licence = (SKILLS / fichier).read_text(encoding="utf-8")
    assert "MIT License" in licence and "Copyright (c)" in licence
    assert "The above copyright notice and this permission notice shall be included" in licence
    assert f"https://github.com/{depot}" in licence and re.search(r"commit [0-9a-f]{40}", licence)
    for nom in noms:
        assert nom in NOMS and f"- {nom}" in licence
        assert fichier in (SKILLS / nom / "SKILL.md").read_text(encoding="utf-8")


def test_les_reprises_sont_du_texte_seulement():
    for _, noms in REPRISES.values():
        for nom in noms:
            fichiers = [p for p in (SKILLS / nom).rglob("*") if p.is_file()]
            assert fichiers and all(p.suffix in {".md", ".json"} for p in fichiers), (nom, fichiers)
    hallmark = (SKILLS / "hallmark" / "SKILL.md").read_text(encoding="utf-8")
    assert "AGENTS.md" in hallmark  # les règles du projet priment (polices, scripts, CSP, faits)


def test_find_skills_n_installe_rien_sans_accord_du_proprietaire():
    """Le texte d'origine conseille `npx skills add … -g -y` (installation globale sans confirmation) : dans ce projet,
    un skill trouvé se lit d'abord et ne s'ajoute qu'avec l'accord du propriétaire, comme celui-ci."""
    texte = (SKILLS / "find-skills" / "SKILL.md").read_text(encoding="utf-8")
    regle = texte.split("# Find Skills", 1)[0]
    assert "accord du propriétaire" in regle and "-y" in regle and "AGENTS.md" in regle


def test_chaque_passage_de_find_skills_qui_cite_npx_skills_rappelle_la_regle():
    """Relecture Gitar de #599 : la règle en tête ne suffit pas, les étapes d'origine (« run the find command », « npx
    skills add … -g -y ») restaient des ordres. Chaque section qui cite `npx skills` porte la note du projet."""
    texte = (SKILLS / "find-skills" / "SKILL.md").read_text(encoding="utf-8")
    corps = texte.split("# Find Skills", 1)[1]
    sections = re.split(r"\n#{2,3} ", corps)
    citees = [section for section in sections if "npx skills" in section]
    assert citees  # depuis la relecture Codex, seule la section qui présente le programme le cite encore
    for section in citees:
        assert "Projet Teranga AI" in section, section.splitlines()[0]


def test_find_skills_ne_contient_plus_de_commande_d_installation():
    """Relecture Codex de #599 : les commandes `npx skills add … -g -y`, `find` et `init` sont retirées des étapes ; le
    programme n'est plus que décrit, dans la section qui le présente."""
    texte = (SKILLS / "find-skills" / "SKILL.md").read_text(encoding="utf-8")
    corps = texte.split("# Find Skills", 1)[1]
    etapes = corps.split("## How to Help Users Find Skills", 1)[1]
    assert "npx skills" not in etapes
    assert "-g -y" not in texte.split("# Find Skills", 1)[1]
