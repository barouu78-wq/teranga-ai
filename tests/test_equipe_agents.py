"""Équipe d'agents : les fichiers de .claude/agents/ respectent leurs garde-fous.

Ces tests ne prouvent pas qu'un agent travaille bien : ils empêchent qu'un agent « en lecture seule » reçoive
par inadvertance un outil d'écriture, qu'un outil Render de modification soit ajouté, ou qu'un identifiant ou un
secret soit écrit dans un fichier d'agent.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude" / "agents"
DOC = (ROOT / "docs" / "EQUIPE-AGENTS.md").read_text(encoding="utf-8")

EXPECTED = {
    "gardien-prod", "relecteur-pr", "securite", "qualite-ia", "verificateur-reperes",
    "voix", "seo-visibilite", "ops-infra", "mesure-latence", "contenu-reseaux", "prospection",
}
READ_ONLY = {"gardien-prod", "relecteur-pr", "securite", "ops-infra", "mesure-latence"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
WRITERS = {
    "qualite-ia", "verificateur-reperes", "voix", "seo-visibilite", "contenu-reseaux", "prospection",
}
BASE_TOOLS = {"Read", "Grep", "Glob", "Bash", "Edit", "Write", "WebFetch", "WebSearch"}
RENDER_READ = re.compile(r"^mcp__Render__(list|get)_[a-z_]+$")
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{16,}", r"AKIA[0-9A-Z]{12,}", r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"Bearer [A-Za-z0-9._-]{24,}", r"srv-[a-z0-9]{12,}", r"\btea-[a-z0-9]{12,}", r"\bred-[a-z0-9]{12,}",
]


def _agent(name):
    texte = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    assert texte.startswith("---\n"), f"{name} : en-tête manquant"
    en_tete, _, corps = texte[4:].partition("\n---\n")
    champs = {}
    for ligne in en_tete.splitlines():
        cle, _, valeur = ligne.partition(":")
        champs[cle.strip()] = valeur.strip()
    return champs, corps, texte


def _outils(champs):
    return [t.strip() for t in champs.get("tools", "").split(",") if t.strip()]


def test_les_onze_agents_sont_presents_et_pas_d_autres():
    assert {p.stem for p in AGENTS.glob("*.md")} == EXPECTED


@pytest.mark.parametrize("nom", sorted(EXPECTED))
def test_nom_description_et_consigne(nom):
    champs, corps, _ = _agent(nom)
    assert champs.get("name") == nom
    assert len(champs.get("description", "")) >= 80, "la description décide quand l'agent est lancé"
    assert "AGENTS.md" in corps, "consigne : lire AGENTS.md d'abord"
    assert "français" in corps


@pytest.mark.parametrize("nom", sorted(EXPECTED))
def test_outils_connus_seulement(nom):
    champs, _, _ = _agent(nom)
    outils = _outils(champs)
    assert outils, "liste d'outils explicite obligatoire (pas d'héritage de tous les outils)"
    for outil in outils:
        assert outil in BASE_TOOLS or RENDER_READ.match(outil), f"{nom} : outil non autorisé {outil}"


@pytest.mark.parametrize("nom", sorted(READ_ONLY))
def test_agents_en_lecture_seule_sans_outil_d_ecriture(nom):
    champs, _, _ = _agent(nom)
    assert not WRITE_TOOLS & set(_outils(champs)), f"{nom} ne doit avoir aucun outil d'écriture de fichiers"


def test_gardien_prod_ne_peut_que_lire_render():
    champs, _, _ = _agent("gardien-prod")
    outils = _outils(champs)
    assert outils and all(t in {"Read", "Grep", "Glob"} or RENDER_READ.match(t) for t in outils)
    assert "Bash" not in outils


def test_ops_infra_ne_fait_que_des_get_et_ne_montre_pas_les_jetons():
    _, corps, _ = _agent("ops-infra")
    minuscules = corps.lower()
    assert "get" in minuscules and "n'affiche jamais un jeton" in minuscules
    assert "jamais `post`" in minuscules


@pytest.mark.parametrize("nom", sorted(EXPECTED))
def test_aucun_secret_ni_identifiant_dans_un_fichier_d_agent(nom):
    _, _, texte = _agent(nom)
    for motif in SECRET_PATTERNS:
        assert not re.search(motif, texte), f"{nom} : motif suspect {motif}"


@pytest.mark.parametrize("nom", sorted(EXPECTED))
def test_le_document_presente_chaque_agent(nom):
    assert f"`{nom}`" in DOC


def test_regles_de_securite_repetees_dans_la_doc():
    for phrase in ("jamais de fusion", "Pousser après chaque étape", "Trois agents en parallèle au maximum"):
        assert phrase.lower() in DOC.lower(), phrase


@pytest.mark.parametrize("nom", sorted(WRITERS))
def test_les_agents_qui_ecrivent_travaillent_dans_leur_propre_copie(nom):
    champs, _, _ = _agent(nom)
    assert WRITE_TOOLS & set(_outils(champs)), f"{nom} est censé écrire des fichiers"
    assert champs.get("isolation") == "worktree", "deux agents lancés ensemble ne doivent pas partager l'index Git"


def test_tout_agent_qui_peut_ecrire_est_isole():
    for nom in EXPECTED:
        champs, _, _ = _agent(nom)
        if WRITE_TOOLS & set(_outils(champs)):
            assert champs.get("isolation") == "worktree", nom


def test_le_document_explique_l_isolation():
    assert "isolation: worktree" in DOC


def test_gardien_prod_lit_la_limite_de_memoire_et_ne_la_suppose_pas():
    _, corps, _ = _agent("gardien-prod")
    assert "memory_limit" in corps
    assert "la limite est de 512" not in corps.lower()


def test_gardien_prod_ne_traite_pas_le_nombre_de_processus_comme_une_invariante():
    _, corps, _ = _agent("gardien-prod")
    assert "GUNICORN_WORKERS" in corps and "par défaut" in corps


@pytest.mark.parametrize("nom", ["contenu-reseaux", "prospection"])
def test_les_agents_commerciaux_ne_publient_ni_n_envoient_rien(nom):
    _, corps, _ = _agent(nom)
    minuscules = corps.lower()
    assert "ne publies rien" in minuscules or "n'envoies aucun message" in minuscules
    assert "aucun fait inventé" in minuscules or "pas de faux chiffres" in minuscules
