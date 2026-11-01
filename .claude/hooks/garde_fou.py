"""Garde-fou des agents Claude Code de Teranga AI (hook PreToolUse, déclaré dans .claude/settings.json).

Avant chaque commande Bash et chaque écriture par les outils GitHub, il bloque ce qui casse sans retour :
- pousser sur main (règle du propriétaire : « ne jamais pousser directement sur main » ; main ne change que par une
  fusion de PR) ;
- une poussée forcée qui écrase l'historique distant (--force, -f, +branche ; --force-with-lease reste permis) ;
- git reset --hard, qui efface le travail non enregistré ;
- rm -r sur la racine, le dossier personnel, le projet, un dossier qui les contient, ou le .git du projet.

Code de sortie 2 : Claude Code annule l'outil et montre la raison à l'agent. Code 0 : l'outil passe. Une erreur du
script lui-même n'arrête pas l'agent (Claude Code l'affiche seulement). Bibliothèque standard seulement (Python 3.8
et plus), pour tourner partout où tourne Claude Code. Tests : tests/test_garde_fou.py.
"""

import json
import os
import re
import shlex
# subprocess sert seulement à lire la branche courante (git symbolic-ref), sans shell.
import subprocess  # nosec B404
import sys

PROTEGEE = "main"
OUTILS_GITHUB = {"mcp__github__push_files", "mcp__github__create_or_update_file", "mcp__github__delete_file"}
PREFIXES = {"sudo", "env", "command", "builtin", "exec", "nohup", "nice", "time", "timeout"}
COQUILLES = {"bash", "sh", "zsh", "dash"}
SURVEILLES = {"git", "rm", "eval"} | COQUILLES
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
AFFECTATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
BRANCHE_COURANTE = re.compile(r"\$\(\s*git\s+(?:branch\s+--show-current|rev-parse\s+--abbrev-ref\s+HEAD"
                              r"|symbolic-ref\s+--short\s+HEAD)\s*\)")
OPTIONS_GIT_AVEC_VALEUR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix"}
OPTIONS_PUSH_AVEC_VALEUR = {"--repo", "--push-option", "--receive-pack", "--exec"}

SUR_MAIN = ("cette commande pousserait sur main. Pousse ta branche de travail (git push -u origin <branche>) et ouvre "
            "une PR : main ne change que par la fusion d'une PR aux contrôles verts.")
INCONNUE = ("la branche visée dépend d'une variable ou d'une commande ($…) que le garde-fou ne peut pas lire : ce "
            "pourrait être main. Écris le nom de la branche en clair.")
TOUT = "git push --all, --mirror ou --branches pousserait aussi main. Pousse seulement ta branche de travail."
GITHUB = ("cet outil GitHub écrirait directement sur main (branche « main » ou absente). Crée une branche de travail "
          "et ouvre une PR.")
FORCE = ("poussée forcée (--force, -f ou +branche) : elle écrase l'historique distant. Si c'est voulu sur ta propre "
         "branche, utilise --force-with-lease.")
RESET = ("git reset --hard efface le travail non enregistré. Utilise git stash, ou git checkout -B <branche> "
         "origin/main pour repartir de main.")
RM = "rm -r viserait {} (racine, dossier personnel, projet ou .git). Supprime un sous-dossier précis."


class _Lieu:
    """Dossier courant de la commande (suit les « cd ») et variables posées par la commande (DEST=main; …)."""

    def __init__(self, dossier, projet, maison):
        self.dossier = os.path.normpath(dossier)
        self.projet = os.path.normpath(projet)
        self.maison = os.path.normpath(maison)
        self.variables = {"HOME": self.maison, "CLAUDE_PROJECT_DIR": self.projet}

    def developpe(self, texte):
        """Remplace $NOM et ${NOM} connus ; une variable inconnue reste telle quelle (avec son $)."""
        def valeur(trouve):
            nom = trouve.group(1) or trouve.group(2)
            return self.variables.get(nom, os.environ.get(nom, trouve.group(0)))
        return VARIABLE.sub(valeur, texte)

    def chemin(self, texte, base=None):
        texte = self.developpe(texte)
        if texte == "~" or texte.startswith("~/"):
            texte = self.maison + texte[1:]
        return os.path.normpath(os.path.join(base or self.dossier, texte))


def motif(outil, entree, cwd, projet, maison):
    """Raison de bloquer cet appel d'outil, ou None s'il peut passer."""
    if outil in OUTILS_GITHUB:
        branche = _court(str(entree.get("branch") or "").strip())
        return GITHUB if branche in ("", PROTEGEE) else None  # sans branche, GitHub écrit sur main
    if outil == "Bash":
        return _commande(str(entree.get("command") or ""), _Lieu(cwd, projet, maison))
    return None


def _court(ref):
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref


def _sans_heredoc(texte):
    """Retire le corps des « << EOF » : c'est du texte (message, fichier), pas des commandes."""
    gardees, fin = [], None
    for ligne in texte.split("\n"):
        if fin is not None:
            if ligne.strip() == fin:
                fin = None
            continue
        gardees.append(ligne)
        trouve = HEREDOC.search(ligne)
        if trouve:
            fin = trouve.group(2)
    return "\n".join(gardees)


def _commande(texte, lieu):
    texte = _sans_heredoc(texte.replace("\\\n", " ")).replace("\n", " ; ").replace("`", " ; ")
    texte = BRANCHE_COURANTE.sub("HEAD", texte)  # "$(git branch --show-current)" : la branche courante
    try:
        lexeur = shlex.shlex(texte, posix=True, punctuation_chars=True)
        lexeur.whitespace_split = True
        mots = list(lexeur)
    except ValueError:  # guillemet non fermé : le shell refuserait aussi ; découpage simple
        mots = texte.split()
    for segment in _segments(mots):
        raison = _segment(segment, lieu)
        if raison:
            return raison
    return None


def _segments(mots):
    """Découpe aux ; && || | & ( ) et saute les redirections (> f, 2>&1, << EOF)."""
    segment, sauter = [], False
    for mot in mots:
        if sauter:
            sauter = False
        elif mot and all(c in "();<>|&" for c in mot):
            if "<" in mot or ">" in mot:
                if segment and segment[-1].isdigit():
                    segment.pop()  # le 2 de 2>&1
                sauter = True
            else:
                if segment:
                    yield segment
                segment = []
        else:
            segment.append(mot)
    if segment:
        yield segment


def _segment(mots, lieu):
    if mots[0] == "export":
        mots = mots[1:]
    i = 0
    while i < len(mots) and AFFECTATION.match(mots[i]):
        i += 1
    if i >= len(mots):  # « DEST=main » seul : la variable vaut pour la suite de la commande
        for mot in mots:
            nom, _, valeur = mot.partition("=")
            lieu.variables[nom] = lieu.developpe(valeur)
        return None
    nom, args = os.path.basename(mots[i]), mots[i + 1:]
    if nom in PREFIXES:
        # sudo -u root rm…, timeout -s KILL 30 git… : les options et leurs valeurs varient ; chaque commande
        # surveillée qui suit est examinée.
        for k, mot in enumerate(args):
            if os.path.basename(mot) in SURVEILLES:
                raison = _segment(args[k:], lieu)
                if raison:
                    return raison
        return None
    if nom in ("cd", "pushd"):
        if not args:
            lieu.dossier = lieu.maison
        elif args[0] != "-":
            lieu.dossier = lieu.chemin(args[0])
        return None
    if nom in COQUILLES:
        for k, mot in enumerate(args[:-1]):
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", mot):
                return _commande(args[k + 1], lieu)
        return None
    if nom == "eval":
        return _commande(" ".join(args), lieu)
    if nom == "git":
        return _git(args, lieu)
    if nom == "rm":
        return _rm(args, lieu)
    return None


def _git(args, lieu):
    dossier, i = lieu.dossier, 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] in OPTIONS_GIT_AVEC_VALEUR and i + 1 < len(args):
            if args[i] == "-C":
                dossier = lieu.chemin(args[i + 1], dossier)
            i += 1
        i += 1
    if i >= len(args):
        return None
    if args[i] == "reset":
        return RESET if "--hard" in args[i + 1:] else None
    if args[i] == "push":
        return _push(args[i + 1:], dossier, lieu)
    return None


def _push(args, dossier, lieu):
    positions, force, tout, i = [], False, False, 0
    while i < len(args):
        mot = args[i]
        if mot == "--":
            positions += args[i + 1:]
            break
        if mot.startswith("--"):
            nom = mot.split("=", 1)[0]
            force = force or nom == "--force"
            tout = tout or nom in ("--all", "--mirror", "--branches")
            if nom in OPTIONS_PUSH_AVEC_VALEUR and "=" not in mot:
                i += 1
        elif mot.startswith("-") and len(mot) > 1:
            lettres, o, valeur = mot[1:].partition("o")  # -o <option> : la suite est une valeur
            force = force or "f" in lettres
            if o and not valeur:
                i += 1
        else:
            positions.append(mot)
        i += 1
    if tout:
        return TOUT
    # Le premier mot est le dépôt distant ; sans branche nommée, git pousse la branche courante.
    for refspec in positions[1:] or ["HEAD"]:
        refspec = lieu.developpe(refspec)
        if "$" in refspec:  # variable inconnue, ${B:-main}, $(…) : la cible ne se lit pas
            return INCONNUE
        force = force or refspec.startswith("+")
        source, deux_points, cible = refspec.lstrip("+").partition(":")
        cible = cible if deux_points else source
        if cible in ("HEAD", "@"):
            cible = _branche(dossier)
        if _court(cible) == PROTEGEE:
            return SUR_MAIN
    return FORCE if force else None


def _branche(dossier):
    try:
        # git sans shell, arguments fixes (le dossier est un seul argument).
        sortie = subprocess.run(  # nosec B603 B607
            ["git", "-C", dossier, "symbolic-ref", "--short", "-q", "HEAD"],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return sortie.stdout.strip()


def _rm(args, lieu):
    recursif, cibles, options = False, [], True
    for mot in args:
        if options and mot == "--":
            options = False
        elif options and mot.startswith("--"):
            recursif = recursif or mot == "--recursive"
        elif options and mot.startswith("-") and len(mot) > 1:
            recursif = recursif or "r" in mot or "R" in mot
        else:
            cibles.append(mot)
    if not recursif:
        return None
    for cible in cibles:
        if cible == "*" or cible.endswith("/*"):
            cible = cible[:-1] or "."  # « rm -rf dossier/* » vide le dossier lui-même
        chemin = lieu.chemin(cible)
        dessous = chemin.rstrip("/") + "/"
        if chemin == os.path.join(lieu.projet, ".git") or any(
                garde == chemin or garde.startswith(dessous) for garde in (lieu.maison, lieu.projet)):
            return RM.format(chemin)
    return None


def main():
    donnees = json.load(sys.stdin)
    raison = motif(donnees.get("tool_name", ""), donnees.get("tool_input") or {}, donnees.get("cwd") or os.getcwd(),
                   os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(), os.path.expanduser("~"))
    if raison:
        print(f"Bloqué par le garde-fou du projet (.claude/hooks/garde_fou.py) : {raison}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
