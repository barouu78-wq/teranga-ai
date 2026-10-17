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
    "voix", "seo-visibilite", "ops-infra", "mesure-latence",
    # Entreprise Teranga (15 octobre 2026) : les pôles qui manquaient pour gérer le projet de A à Z.
    "developpeur", "chef-produit", "partenariats", "communication", "analyste",
}
READ_ONLY = {"gardien-prod", "relecteur-pr", "securite", "ops-infra", "mesure-latence", "analyste"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
WRITERS = {
    "qualite-ia", "verificateur-reperes", "voix", "seo-visibilite",
    "developpeur", "chef-produit", "partenariats", "communication",
}
# Ces agents n'écrivent que des documents : ils n'ont pas besoin d'un shell.
DOCUMENTS_ONLY = {"chef-produit", "communication"}
POLES = ("Direction", "Pôle produit", "Pôle technique", "Pôle qualité", "Pôle visibilité", "Pôle commercial")
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


def test_les_quatorze_agents_sont_presents_et_pas_d_autres():
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


# --- Entreprise Teranga : organigramme et garde-fous des nouveaux pôles -------------------------------------


@pytest.mark.parametrize("nom", sorted(DOCUMENTS_ONLY))
def test_les_agents_de_documents_n_ont_pas_de_shell(nom):
    champs, _, _ = _agent(nom)
    assert "Bash" not in _outils(champs)


def test_l_analyste_ne_peut_que_lire_render():
    champs, corps, _ = _agent("analyste")
    outils = _outils(champs)
    assert all(t in {"Read", "Grep", "Glob", "Bash"} or RENDER_READ.match(t) for t in outils)
    assert "adresse IP" in corps and "contenu des questions" in corps


def test_partenariats_n_envoie_rien_et_n_annonce_aucun_partenaire_sans_accord():
    _, corps, _ = _agent("partenariats")
    minuscules = corps.lower()
    assert "tu n'envoies jamais" in minuscules
    assert "accord écrit" in minuscules
    assert "/go/" in corps


def test_communication_ne_publie_rien_et_cite_ses_sources():
    _, corps, _ = _agent("communication")
    minuscules = corps.lower()
    assert "tu ne publies jamais" in minuscules
    assert "source" in minuscules


def test_le_developpeur_ecrit_le_test_d_abord_et_ne_fusionne_pas():
    _, corps, _ = _agent("developpeur")
    assert "tester-d-abord" in corps and "preparer-une-pr" in corps
    assert "tu ne fusionnes jamais" in corps.lower()


def test_l_organigramme_place_chaque_agent_dans_un_pole():
    organigramme = DOC.split("## Organigramme", 1)[1].split("\n## ", 1)[0]
    for pole in POLES:
        assert pole in organigramme, pole
    for nom in EXPECTED:
        assert f"`{nom}`" in organigramme, nom


def test_la_reunion_hebdomadaire_est_decrite():
    assert "`conseil-hebdo`" in DOC
    assert (ROOT / ".claude" / "skills" / "conseil-hebdo" / "SKILL.md").exists()


@pytest.mark.parametrize("nom", sorted(EXPECTED))
def test_l_en_tete_reste_du_yaml_valide(nom):
    """Un « : » suivi d'une espace dans la description rend l'en-tête illisible pour un lecteur YAML strict.

    Claude Code le tolère aujourd'hui (l'agent `securite` se chargeait malgré ce défaut, corrigé le 15 octobre 2026),
    mais d'autres outils lisent ces fichiers et une tolérance peut disparaître.
    """
    champs, _, _ = _agent(nom)
    assert ": " not in champs["description"]


# Économie de quota (17 octobre 2026) : les agents qui lisent ou rédigent tournent sur un modèle moins coûteux.
LEGERS = {"analyste", "gardien-prod", "mesure-latence", "seo-visibilite", "communication", "chef-produit"}


@pytest.mark.parametrize("nom", sorted(EXPECTED))
def test_le_modele_suit_le_travail(nom):
    champs, _, _ = _agent(nom)
    if nom in LEGERS:
        assert champs.get("model") == "sonnet", nom
    else:
        assert "model" not in champs, f"{nom} écrit ou relit du code : il garde le modèle de la session"


def test_un_agent_a_la_fois_par_defaut():
    assert "Un agent à la fois" in DOC


def test_partenariats_trouve_des_partenaires_sur_des_sources_publiques_seulement():
    champs, corps, _ = _agent("partenariats")
    assert {"WebFetch", "WebSearch"} <= set(_outils(champs)), "trouver un partenaire demande d'ouvrir sa page"
    minuscules = corps.lower()
    assert "sources interdites" in minuscules and "airbnb" in minuscules
    assert "deviner un" in minuscules


def test_communication_couvre_le_marketing_sans_shell():
    champs, corps, _ = _agent("communication")
    assert "Bash" not in _outils(champs)
    for canal in ("WhatsApp", "TikTok", "Instagram", "diaspora"):
        assert canal in corps, canal
