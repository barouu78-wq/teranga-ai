"""Garde-fou des agents (.claude/hooks/garde_fou.py), demandé par le propriétaire le 1er novembre 2026 (« Go hook »).

Avant chaque commande d'un agent Claude Code, il bloque ce qui casse sans retour : pousser sur main (la règle « ne
jamais pousser directement sur main »), une poussée forcée qui écrase l'historique, `git reset --hard`, et
`rm -r` sur la racine, le dossier personnel ou le projet. Il bloque aussi l'écriture directe sur main par les outils
GitHub. Tout le reste passe : branches, PR, tests, lecture, et le texte qui parle de ces commandes sans les lancer.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "hooks" / "garde_fou.py"
_spec = importlib.util.spec_from_file_location("garde_fou", SCRIPT)
garde_fou = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(garde_fou)

PROJET = "/srv/teranga"
MAISON = "/home/visiteur"


def motif(commande, cwd=PROJET):
    return garde_fou.motif("Bash", {"command": commande}, cwd, PROJET, MAISON)


@pytest.mark.parametrize("commande", [
    "git push origin main",
    "git push -u origin main",
    "git push origin HEAD:main",
    "git push origin outils/x:main",
    "git push origin refs/heads/main",
    "git push origin HEAD:refs/heads/main",
    "git push origin :main",
    "git push origin --delete main",
    "git push --all origin",
    "git push --mirror origin",
    "cd /tmp && git push origin main",
    "git -C /srv/teranga push origin main",
    "git --no-pager -c color.ui=never push origin main",
    "GIT_TRACE=1 git push origin main",
    "/usr/bin/git push origin main",
    "echo ok; git push origin main",
    "git push origin outils/x && git push origin main",
    "git status\ngit push origin main",
    "git push \\\n  origin main",
    "bash -c 'git push origin main'",
    "sh -c \"cd /tmp && git push origin main\"",
    "echo $(git push origin main)",
    "git push origin main 2>&1 | tail -3",
])
def test_pousser_sur_main_est_bloque(commande):
    raison = motif(commande)
    assert raison and "main" in raison


@pytest.mark.parametrize("commande", [
    "git push --force origin outils/x",
    "git push -f origin outils/x",
    "git push -uf origin outils/x",
    "git push origin +outils/x",
    "git push origin +HEAD:outils/x",
])
def test_la_poussee_forcee_est_bloquee(commande):
    raison = motif(commande)
    assert raison and "force" in raison


@pytest.mark.parametrize("commande", [
    "git reset --hard",
    "git reset --hard origin/main",
    "git -C /srv/teranga reset --hard HEAD~1",
    "git status && git reset --hard",
])
def test_reset_hard_est_bloque(commande):
    raison = motif(commande)
    assert raison and "reset --hard" in raison


# Remarques de Codex sur la PR #567 : une option avec valeur devant la commande (sudo -u root…) ou une variable dans la
# branche visée ne doivent pas cacher la commande bloquée.
@pytest.mark.parametrize("commande", [
    "sudo -u root rm -rf /",
    "sudo -u bot git push origin main",
    "sudo -u git rm -rf /",
    "timeout -s KILL 30 git push origin main",
    "env -u LANG git push origin main",
    "sudo -u bot bash -c 'git push origin main'",
    "DEST=main; git push origin HEAD:$DEST",
    "export DEST=main && git push origin HEAD:${DEST}",
    'git push origin "$BRANCHE_INCONNUE"',
    "git push origin ${B:-main}",
    "git push origin $(echo main)",
    "X=/; rm -rf $X",
])
def test_options_et_variables_ne_cachent_pas_la_commande(commande):
    assert motif(commande, "/tmp")


# Remarques de Gitar sur la PR #567 : une substitution entre guillemets et un heredoc lu par un shell sont exécutés.
@pytest.mark.parametrize("commande", [
    'echo "$(git push origin main)"',
    'OUT="$(git push origin main 2>&1)"',
    'echo "$(echo $(git push origin main))"',
    'echo "`git push origin main`"',
    'echo "x $(rm -rf /) y"',
    "bash <<EOF\ngit push origin main\nEOF",
    "sh <<'FIN'\nrm -rf /\nFIN",
    "cat <<EOF | bash\ngit reset --hard\nEOF",
    'echo "a <<EOF"\ngit push origin main',
    "cat > f.txt <<EOF\n$(git push origin main)\nEOF",
    "rm -rf $VIDE/*",
    'rm -rf "${D:-/}"',
    "sudo -Eu root rm -rf /",
    "sudo -uroot git push origin main",
])
def test_substitutions_heredocs_et_variables_executes_sont_examines(commande):
    assert motif(commande, "/tmp")


# Remarque de Gitar après 7f33c6f : $(…), bash -c et bash <<EOF tournent dans un sous-shell (un cd n'en ressort pas),
# et ils tournent à leur place dans la commande (après le cd qui les précède).
@pytest.mark.parametrize("commande,cwd", [
    ('echo "$(cd /tmp && pwd)"; rm -rf ./*', PROJET),
    ("X=$(cd /tmp); rm -rf ./*", PROJET),
    ('bash -c "cd /tmp"; rm -rf ./*', PROJET),
    ("bash <<EOF\ncd /tmp\nEOF\nrm -rf ./*", PROJET),
    ('cd /srv/teranga && echo "$(rm -rf .)"', "/tmp"),
    ("cd /srv/teranga && bash <<EOF\nrm -rf .\nEOF", "/tmp"),
    ("(cd /tmp); rm -rf ./*", PROJET),
    ("(cd /srv/teranga && rm -rf .)", "/tmp"),
])
def test_un_sous_shell_garde_son_dossier_et_tourne_a_sa_place(commande, cwd):
    assert motif(commande, cwd)


@pytest.mark.parametrize("commande", [
    "env GIT_TRACE=1 git rm -r --cached .",
    "time git rm -r --cached .",
    "S=/tmp/essai; rm -rf \"$S/build\"",
    "python3 - <<'PY'\nprint('git push origin main')\nPY",
    "git commit -m 'Ne lance jamais $(git push origin main)'",
    "sudo -Eu bot git status",
])
def test_ce_qui_n_est_pas_lance_passe(commande):
    assert motif(commande) is None


def test_une_variable_connue_vers_une_branche_de_travail_passe():
    assert motif('B=outils/x; git push -u origin "$B"', "/tmp") is None
    assert motif("sudo -u bot git status", "/tmp") is None


@pytest.mark.parametrize("commande,cwd", [
    ("rm -rf /", PROJET),
    ("rm -rf /*", PROJET),
    ("rm -rf ~", PROJET),
    ("rm -rf ~/", PROJET),
    ("rm -rf $HOME", PROJET),
    ('rm -fr "$HOME"/', PROJET),
    ("rm -r -f /", PROJET),
    ("rm --recursive --force /", PROJET),
    ("sudo rm -rf /", PROJET),
    ("rm -rf /srv/teranga", "/tmp"),
    ("rm -rf /srv/teranga/", "/tmp"),
    ("rm -rf /srv", "/tmp"),
    ("rm -rf .", PROJET),
    ("rm -rf *", PROJET),
    ("rm -rf ./*", PROJET),
    ("rm -rf .git", PROJET),
    ("rm -rf ..", PROJET + "/static"),
    ("cd /srv/teranga && rm -rf .", "/tmp"),
    ("rm -rf -- /", PROJET),
])
def test_rm_recursif_sur_la_racine_la_maison_ou_le_projet_est_bloque(commande, cwd):
    raison = motif(commande, cwd)
    assert raison and "rm" in raison


@pytest.mark.parametrize("commande", [
    "git push -u origin outils/garde-fou-commandes",
    "git push origin outils/x",
    "git push --force-with-lease origin outils/x",
    "git push origin main:outils/x",
    "git status",
    "git log --oneline main -5",
    "git checkout -B outils/x origin/main",
    "git fetch origin main",
    "git pull origin main",
    "git merge origin/main",
    "git diff origin/main",
    "git reset --soft HEAD~1",
    "git reset HEAD static/home.js",
    "rm -rf build",
    "rm -rf /tmp/essai",
    "rm -rf .claude/worktrees/wt-x",
    "rm -rf static/__pycache__ tests/__pycache__",
    "rm -f /srv/teranga/notes.txt",
    "rm /",
    'echo "git push origin main"',
    'git commit -m "Ne jamais lancer git push origin main ni rm -rf /"',
    'grep -rn "reset --hard" .',
    "cat > corps.md <<'EOF'\ngit push origin main\nrm -rf /\ngit reset --hard\nEOF\necho fini",
    'git commit -m "$(cat <<\'EOF\'\nÉviter git push --force\nEOF\n)"',
    "python -m pytest -q tests/test_garde_fou.py",
])
def test_le_travail_normal_passe(commande):
    assert motif(commande) is None


def test_rm_recursif_dans_un_dossier_de_travail_passe(tmp_path):
    assert motif("rm -rf .", str(tmp_path)) is None
    assert motif("rm -rf *", str(tmp_path)) is None


def _depot(dossier, branche):
    subprocess.run(["git", "init", "-q", "-b", "main", str(dossier)], check=True)
    subprocess.run(["git", "-C", str(dossier), "symbolic-ref", "HEAD", f"refs/heads/{branche}"], check=True)
    return str(dossier)


@pytest.mark.parametrize("commande", [
    "git push", "git push origin", "git push -u origin HEAD", "git push origin @", "git push 2>&1",
    'git push -u origin "$(git branch --show-current)"', "git push origin $(git rev-parse --abbrev-ref HEAD)",
    'echo "$(cd /tmp)"; git push',
])
def test_pousser_sans_branche_nommee_depuis_main_est_bloque(tmp_path, commande):
    depot = _depot(tmp_path / "depot", "main")
    raison = motif(commande, depot)
    assert raison and "main" in raison
    # Même chose quand la commande entre d'abord dans le dépôt, ou le vise avec -C.
    assert motif(f"cd {depot} && {commande}", "/tmp")
    assert motif(commande.replace("git push", f"git -C {depot} push"), "/tmp")


@pytest.mark.parametrize("commande", ["git push", "git push origin", "git push -u origin HEAD",
                                      'git push -u origin "$(git branch --show-current)"'])
def test_pousser_sans_branche_nommee_depuis_une_branche_de_travail_passe(tmp_path, commande):
    assert motif(commande, _depot(tmp_path / "depot", "outils/x")) is None


@pytest.mark.parametrize("outil", ["mcp__github__push_files", "mcp__github__create_or_update_file",
                                   "mcp__github__delete_file"])
@pytest.mark.parametrize("branche", ["main", "refs/heads/main", "", None])
def test_les_outils_github_n_ecrivent_jamais_sur_main(outil, branche):
    entree = {"owner": "barouu78-wq", "repo": "teranga-ai", "path": "README.md", "message": "m"}
    if branche is not None:
        entree["branch"] = branche  # sans branche, GitHub écrirait sur la branche par défaut : main
    raison = garde_fou.motif(outil, entree, PROJET, PROJET, MAISON)
    assert raison and "main" in raison


def test_les_outils_github_ecrivent_sur_une_branche_de_travail():
    entree = {"owner": "barouu78-wq", "repo": "teranga-ai", "branch": "outils/x", "files": [], "message": "m"}
    assert garde_fou.motif("mcp__github__push_files", entree, PROJET, PROJET, MAISON) is None
    assert garde_fou.motif("Read", {"file_path": "/srv/teranga/app.py"}, PROJET, PROJET, MAISON) is None


def _lancer(entree):
    return subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(entree), capture_output=True, text=True,
                          timeout=20, env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(ROOT)})


def test_le_script_bloque_avec_le_code_2_et_explique_pourquoi():
    resultat = _lancer({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}, "cwd": str(ROOT)})
    assert resultat.returncode == 2  # code 2 : Claude Code annule la commande et montre la raison à l'agent
    assert "main" in resultat.stderr and "garde-fou" in resultat.stderr.lower()


def test_le_script_laisse_passer_le_reste_sans_rien_ecrire():
    resultat = _lancer({"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(ROOT)})
    assert (resultat.returncode, resultat.stdout, resultat.stderr) == (0, "", "")


def test_le_garde_fou_est_declare_avant_chaque_commande_et_outil_github():
    reglages = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    avant = reglages["hooks"]["PreToolUse"]
    assert len(avant) == 1
    assert set(avant[0]["matcher"].split("|")) == {"Bash", "mcp__github__push_files",
                                                   "mcp__github__create_or_update_file", "mcp__github__delete_file"}
    assert [c["command"] for c in avant[0]["hooks"]] == ['python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/garde_fou.py"']
    assert reglages["hooks"]["SessionStart"]  # le hook de démarrage reste en place


def test_agents_md_presente_le_garde_fou():
    assert "garde_fou.py" in (ROOT / "AGENTS.md").read_text(encoding="utf-8")
