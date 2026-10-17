"""Outils vidéo (scripts/video/, skill faire-une-video) : présents, sans chemin de machine, règles écrites.

Le rendu lui-même demande Chromium et ffmpeg : il n'est pas lancé ici. On vérifie ce qui casserait une vidéo sans bruit :
un modèle qui pointe vers un dossier d'une machine précise, ou un repère {{…}} que rendu.py ne remplace pas.
"""

import py_compile
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "scripts" / "video"
MODELES = sorted((VIDEO / "modeles").glob("*.html"))
SKILL = (ROOT / ".claude" / "skills" / "faire-une-video" / "SKILL.md").read_text(encoding="utf-8")


def test_les_deux_modeles_existent():
    assert {m.name for m in MODELES} == {"presentation.html", "clip-pub.html"}


@pytest.mark.parametrize("script", ["rendu.py", "ecrans.py"])
def test_les_scripts_se_compilent(script):
    py_compile.compile(str(VIDEO / script), doraise=True)


@pytest.mark.parametrize("modele", MODELES, ids=lambda m: m.name)
def test_modele_sans_chemin_de_machine_et_reperes_connus(modele):
    texte = modele.read_text(encoding="utf-8")
    assert "/home/" not in texte and "/tmp/" not in texte
    assert set(re.findall(r"\{\{(\w+)\}\}", texte)) <= {"LION", "FONTS", "ECRANS"}
    assert "{{LION}}" in texte and "teranga-ai.fr" in texte


def test_premiere_image_jamais_vide():
    """Le 17 octobre 2026, une vidéo a été livrée avec une première image vide (titre encore en fondu)."""
    for modele in MODELES:
        texte = modele.read_text(encoding="utf-8")
        premiere = re.search(r'<section class="sc(?:ene)?" (?:id="\w+" )?style="([^"]*)"', texte)
        regle = re.search(r"#s1\{\{?animation:(\w+)", texte)
        nom = (regle.group(1) if regle else premiere.group(1) if premiere else "")
        assert "first" in nom or "sc0" in nom, modele.name


def test_le_skill_rappelle_les_regles():
    for phrase in ("Aucune réponse de l'IA inventée", "aucune personne générée", "Première image", "Ne jamais publier"):
        assert phrase in SKILL, phrase
