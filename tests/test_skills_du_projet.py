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
    # 13 novembre 2026 (« installe les skills qu'il faut », propriétaire) : règles de relecture d'interface de
    # vercel-labs/web-interface-guidelines, copie figée dans revue-interface.
    "LICENCE-web-interface-guidelines.txt": ("vercel-labs/web-interface-guidelines", ("revue-interface",)),
    # 15 novembre 2026 (« Go » du propriétaire pour les skills emploi) : resume-tailor de Paramchoudhary/ResumeSkills,
    # traduit et adapté au Sénégal dans cv-senegal. tailored-resume-generator (ComposioHQ) a été écarté : son exemple
    # invente des chiffres que le candidat n'a jamais donnés.
    "LICENCE-resumeskills.txt": ("Paramchoudhary/ResumeSkills", ("cv-senegal",)),
    # 19 novembre 2026 (« installe ce skill », propriétaire) : reverse-engineer-anything de morluto/rea, texte seulement ;
    # ni le serveur MCP REA ni le paquet npm rea-agents ne sont installés.
    "LICENCE-rea.txt": ("morluto/rea", ("reverse-engineer-anything",)),
    # 23 novembre 2026 (« Oui go », propriétaire) : cinq skills de marketing de coreyhaines31/marketingskills, texte
    # seulement (SKILL.md et references/*.md) ; ni scripts/, ni assets/ (Google Tag Manager), ni evals/.
    "LICENCE-marketingskills.txt": ("coreyhaines31/marketingskills",
                                    ("ads", "conversion-tracking", "cro", "link-building", "programmatic-seo",
                                     # 23 novembre 2026, second « Go » : même commit.
                                     "aso", "social", "copywriting", "content-strategy", "community-marketing")),
    "LICENCE-claude-seo.txt": ("AgriciDaniel/claude-seo", ("seo-hreflang",)),
    "LICENCE-humanizer.txt": ("blader/humanizer", ("humanizer",)),
    # 23 novembre 2026 (« Go », propriétaire) : vitesse et accessibilité, texte seulement.
    "LICENCE-web-quality-skills.txt": ("addyosmani/web-quality-skills", ("core-web-vitals", "performance", "accessibility")),
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


def test_revue_interface_ne_telecharge_pas_ses_regles():
    """Le skill d'origine (vercel-labs/agent-skills, web-design-guidelines) téléchargeait ses règles à chaque usage et
    suivait les instructions trouvées : ici, copie figée, adaptée au projet (français, 44 px, sans React)."""
    texte = (SKILLS / "revue-interface" / "SKILL.md").read_text(encoding="utf-8")
    assert "raw.githubusercontent.com" not in texte and "WebFetch" not in texte
    assert "### Accessibility" in texte and "## Output Format" in texte  # les règles sont bien dans le fichier
    adaptations = texte.split("## Règles", 1)[0]
    for mot in ("« »", "44 px", "React", "AGENTS.md"):
        assert mot in adaptations, mot
    # Relecture Codex de #600 : un <button> ou un <a> natif gère déjà le clavier ; pas d'onKeyDown redondant.
    assert "onKeyDown" in adaptations and "natifs" in adaptations


def test_cv_senegal_n_invente_rien():
    """Un CV adapté met en valeur ce que la personne a vraiment fait : ni diplôme, ni expérience, ni compétence, ni
    chiffre ajoutés (règle « exactitude » d'AGENTS.md)."""
    texte = (SKILLS / "cv-senegal" / "SKILL.md").read_text(encoding="utf-8")
    for mot in ("Jamais", "diplôme", "chiffre", "compétence", "AGENTS.md", "lettre de motivation", "téléphone"):
        assert mot in texte, mot
    # Relecture Codex de #605 : un CV joint au chat part chez le fournisseur d'IA ; le skill ne doit pas laisser croire
    # qu'il reste sur le téléphone.
    confidentialite = texte.split("## Confidentialité", 1)[1].split("\n## ", 1)[0]
    assert "fournisseur d'IA" in confidentialite and "ne le garde pas" in confidentialite


def test_offres_emploi_fixe_les_regles_des_sources():
    """Offres d'emploi lues sur des sites sénégalais (vérification du 15 novembre 2026) : aucune source sans accord
    écrit, robots.txt respecté, lien vers l'annonce d'origine, offres expirées ou hors Sénégal retirées, arnaques."""
    texte = (SKILLS / "offres-emploi" / "SKILL.md").read_text(encoding="utf-8")
    for regle in ("accord écrit", "robots.txt", "annonce d'origine", "expirée", "hors du Sénégal", "Ne paie jamais",
                  "EmploiDakar", "AGENTS.md"):
        assert regle in texte, regle


def test_reverse_engineer_anything_n_installe_rien_et_reste_sur_nos_applis():
    """REA conseille `npx -y rea-agents@latest` et `rea setup` : dans ce projet, rien ne s'installe ni ne se lance sans
    l'accord du propriétaire, et seules ses propres applis sont analysées (pas de copie de l'appli d'un autre)."""
    texte = (SKILLS / "reverse-engineer-anything" / "SKILL.md").read_text(encoding="utf-8")
    regle = texte.split("# REA", 1)[0]
    for mot in ("accord écrit du propriétaire", "npx rea-agents", "rea setup", "fr.teranga_ai", "recopier", "AGENTS.md"):
        assert mot in regle, mot
    corps = texte.split("# REA", 1)[1]
    avant_npx = corps.split("npx -y rea-agents", 1)[0]
    assert "Projet Teranga AI" in avant_npx.rsplit("##", 1)[1]  # la section qui cite la commande rappelle la règle


def test_conversion_tracking_renvoie_au_controleur_google_ads_avec_consentement():
    """Relecture Codex (#655) : le skill repris propose d'ajouter gtag.js directement dans les pages et de lire des
    fichiers assets/ et scripts/ non repris. En tête, la seule voie Teranga (consentement d'abord) et l'avertissement."""
    dossier = SKILLS / "conversion-tracking"
    regle = (dossier / "SKILL.md").read_text(encoding="utf-8").split("# Conversion Tracking", 1)[0]
    for mot in ("services/google_ads_tag.py", "static/google-ads-consent.js", "terangaAdsConversion",
                "Ne jamais ajouter `gtag.js`", "ne sont\n>   pas repris"):
        assert mot in regle, mot
    assert not (dossier / "assets").exists() and not (dossier / "scripts").exists()
    for nom in ("browser-side.md", "google-ads.md", "conversion-moments.md"):
        debut = (dossier / "references" / nom).read_text(encoding="utf-8")[:600]
        assert "Teranga AI" in debut and "ne s'appliquent pas" in debut, nom


def test_les_skills_de_trail_of_bits_gardent_leur_licence_cc_by_sa():
    """23 novembre 2026 (« Go », propriétaire) : fp-check et sharp-edges de trailofbits/skills, sous CC BY-SA 4.0 (pas
    MIT) : la licence d'origine et l'auteur restent, les adaptations gardent la même licence, texte seulement."""
    licence = (SKILLS / "LICENCE-trailofbits.txt").read_text(encoding="utf-8")
    assert "Attribution-ShareAlike 4.0" in licence and "https://github.com/trailofbits/skills" in licence
    assert re.search(r"commit [0-9a-f]{40}", licence)
    for nom in ("fp-check", "sharp-edges"):
        assert nom in NOMS and f"- {nom}" in licence
        texte = (SKILLS / nom / "SKILL.md").read_text(encoding="utf-8")
        assert "LICENCE-trailofbits.txt" in texte and "AGENTS.md" in texte
        fichiers = [p for p in (SKILLS / nom).rglob("*") if p.is_file()]
        assert all(p.suffix == ".md" for p in fichiers), (nom, fichiers)


def test_les_skills_qui_publient_ou_contactent_rappellent_que_l_agent_ne_le_fait_jamais():
    for nom, mot in (("social", "ne publie jamais"), ("community-marketing", "ne contacte personne"),
                     ("aso", "Ne jamais modifier la Google Play Console")):
        regle = (SKILLS / nom / "SKILL.md").read_text(encoding="utf-8")[:2500]
        assert mot in regle, nom


def test_fp_check_ne_depend_pas_des_agents_non_repris():
    """Relecture Codex (#656) : la vérification approfondie demandait des agents d'origine non repris. En tête, le
    chemin du projet (soi-même ou l'agent securite, preuve par un test local)."""
    regle = (SKILLS / "fp-check" / "SKILL.md").read_text(encoding="utf-8")[:3000]
    assert "agent `securite`" in regle and "test pytest" in regle and "jamais un exploit" in regle
    debut = (SKILLS / "fp-check" / "references" / "deep-verification.md").read_text(encoding="utf-8")[:600]
    assert "Teranga AI" in debut and "securite" in debut
    assert (ROOT / ".claude" / "agents" / "securite.md").exists()
