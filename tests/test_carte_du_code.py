"""Carte du code (graphify) : installée de façon sûre, sans crochet ni appel à un modèle.

Choix du propriétaire du 12 octobre 2026 : version fixée, analyse locale, aucun des crochets que `graphify install`
ajouterait (ils exécuteraient le code d'un tiers avant chaque action de Claude et des agents).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / ".claude" / "skills" / "carte-du-code" / "SKILL.md").read_text(encoding="utf-8")
COMMANDES = "\n".join(re.findall(r"```bash\n(.*?)```", SKILL, re.S))


def test_la_version_de_graphify_est_fixee():
    assert re.search(r"pip install -q graphifyy==\d+\.\d+\.\d+", COMMANDES)


def test_aucune_commande_n_installe_de_crochet_ni_ne_va_sur_le_web():
    for interdite in ("graphify install", "graphify add", "graphify clone", "API_KEY"):
        assert interdite not in COMMANDES, interdite
    # Mode « /graphify » avec un modèle (commande de Claude), à ne pas confondre avec le chemin /tmp/graphify-venv.
    assert not re.search(r"(?<![\w/.-])/graphify\b", COMMANDES)


def test_chaque_mention_d_une_commande_interdite_est_une_interdiction():
    for ligne in SKILL.splitlines():
        if any(mot in ligne for mot in ("graphify install", "graphify add", "GEMINI_API_KEY")):
            assert "jamais" in ligne.lower(), ligne


def test_la_carte_n_est_jamais_commitee():
    assert "graphify-out/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_aucun_crochet_graphify_dans_les_reglages_du_projet():
    reglages = ROOT / ".claude" / "settings.json"
    if reglages.exists():
        assert "graphify" not in reglages.read_text(encoding="utf-8")


def test_la_fiche_est_listee_dans_agents_md():
    assert "`carte-du-code`" in (ROOT / "AGENTS.md").read_text(encoding="utf-8")
