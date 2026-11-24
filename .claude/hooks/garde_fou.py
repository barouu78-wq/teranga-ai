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

import copy
import json
import os
import re
import shlex
# subprocess sert seulement à lire la branche courante (git symbolic-ref), sans shell.
import subprocess  # nosec B404
import sys

PROTEGEE = "main"
OUTILS_GITHUB = {"mcp__github__push_files", "mcp__github__create_or_update_file", "mcp__github__delete_file"}
# Commandes qui en lancent une autre : options suivies d'une valeur, puis nombre de mots à sauter (la durée de timeout).
PREFIXES = {
    "sudo": ({"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "--user", "--group", "--chdir", "--host",
              "--prompt", "--role", "--type", "--other-user", "--command-timeout", "--close-from"}, 0),
    "env": ({"-u", "-C", "-S", "--unset", "--chdir", "--split-string"}, 0),
    "timeout": ({"-s", "-k", "--signal", "--kill-after"}, 1),
    "nice": ({"-n", "--adjustment"}, 0),
    "time": ({"-f", "-o", "--format", "--output"}, 0),
    "exec": ({"-a"}, 0),
    "command": (set(), 0), "builtin": (set(), 0), "nohup": (set(), 0),
}
COQUILLES = {"bash", "sh", "zsh", "dash"}
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
LECTEUR = re.compile(r"(?:^|[\s;&|(])(?:bash|sh|zsh|dash|eval)(?=[\s;&|)]|$)")  # bash <<EOF, … | sh
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
DOSSIER_INCONNU = ("la branche courante se lit dans un dossier que le garde-fou ne connaît pas (cd vers $…, cd -) : ce "
                   "pourrait être main. Nomme la branche en clair : git push -u origin <branche>.")
RM_DOSSIER = ("rm -r sur « {} » dans un dossier que le garde-fou ne connaît pas (cd vers $…, cd -) : ce pourrait être "
              "le projet. Écris le chemin en clair.")
RM_VARIABLE = ("rm -r sur « {} » : ce chemin dépend d'une variable que le garde-fou ne peut pas lire ; vide, elle "
               "pourrait viser la racine. Écris le chemin en clair.")


class _Lieu:
    """Dossier courant de la commande (suit les « cd ») et variables posées par la commande (DEST=main; …)."""

    def __init__(self, dossier, projet, maison):
        self.dossier = os.path.normpath(dossier)
        self.projet = os.path.normpath(projet)
        self.maison = os.path.normpath(maison)
        self.variables = {"HOME": self.maison, "CLAUDE_PROJECT_DIR": self.projet}
        self.inconnu = False  # après cd "$(…)", cd $INCONNUE ou cd - : on ne sait plus quel est le dossier

    def developpe(self, texte):
        """Remplace $NOM et ${NOM} connus ; une variable inconnue reste telle quelle (avec son $)."""
        def valeur(trouve):
            nom = trouve.group(1) or trouve.group(2)
            return self.variables.get(nom, os.environ.get(nom, trouve.group(0)))
        return VARIABLE.sub(valeur, texte)

    def enfant(self, dossier=None, inconnu=None):
        """Copie pour un sous-shell ($(…), bash -c, heredoc lu par bash) : ses cd et ses variables n'en ressortent pas."""
        copie = copy.copy(self)
        copie.variables = dict(self.variables)
        copie.dossier = dossier or self.dossier
        copie.inconnu = self.inconnu if inconnu is None else inconnu
        return copie

    def aller(self, cible, base=None):
        """Dossier et état « inconnu » après cd cible (depuis base) : illisible si un $ reste ou si c'est « - »."""
        texte = self.developpe(cible)
        if cible == "-" or "$" in texte:
            return base or self.dossier, True
        absolu = texte.startswith(("/", "~"))
        return self.chemin(texte, base), self.inconnu and not absolu

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


def _guillemets(texte, guillemet=""):
    """Pour chaque caractère, le guillemet ouvert à cet endroit ("", "'" ou '"') ; et celui encore ouvert à la fin."""
    etats, i = [], 0
    while i < len(texte):
        c = texte[i]
        if guillemet == "'":
            etats.append("'")
            guillemet = "" if c == "'" else "'"
        elif guillemet == '"':
            etats.append('"')
            if c == '"':
                guillemet = ""
            elif c == "\\" and i + 1 < len(texte):
                etats.append('"')
                i += 1
        elif c in "'\"":
            etats.append(c)
            guillemet = c
        else:
            etats.append("")
            if c == "\\" and i + 1 < len(texte):
                etats.append("")
                i += 1
        i += 1
    return etats, guillemet


def _heredocs(texte):
    """Retire le corps des « << EOF », hors guillemets. Ce corps est du texte (message, fichier), sauf quand un
    shell le lit (bash <<EOF, … | sh) : il est alors rendu comme commandes à examiner. Sans apostrophes autour de
    EOF, ses $(…) sont lancés : ils sont rendus aussi."""
    gardees, a_examiner, ouvert, guillemet = [], [], None, ""

    def fermer(ouvert):
        corps = "\n".join(ouvert[3])
        if ouvert[1]:
            a_examiner.append(corps)
        elif ouvert[2]:
            a_examiner.extend(interieur for _, _, interieur in _substitutions(corps))

    for ligne in texte.split("\n"):
        if ouvert is not None:
            if ligne.strip() == ouvert[0]:
                fermer(ouvert)
                ouvert = None
            else:
                ouvert[3].append(ligne)
            continue
        gardees.append(ligne)
        etats, suite = _guillemets(ligne, guillemet)
        for trouve in HEREDOC.finditer(ligne):
            if not etats[trouve.start()]:
                ouvert = (trouve.group(2), bool(LECTEUR.search(ligne)), not trouve.group(1), [])
                break
        guillemet = suite
    if ouvert is not None:  # heredoc jamais fermé : le shell le lit jusqu'au bout
        fermer(ouvert)
    return "\n".join(gardees), a_examiner


def _substitutions(texte):
    """Les $(…) et `…` lancés (sans guillemets ou entre guillemets doubles, pas entre apostrophes) :
    (début, fin, commande) pour chacun, fin incluse."""
    etats, _ = _guillemets(texte)
    trouvees, i = [], 0
    while i < len(texte):
        if etats[i] != "'" and texte.startswith("$(", i) and not texte.startswith("$((", i):
            debut, profondeur, fin = i + 2, 1, len(texte)
            for j in range(debut, len(texte)):
                profondeur += {"(": 1, ")": -1}.get(texte[j], 0)
                if profondeur == 0:
                    fin = j
                    break
        elif etats[i] != "'" and texte[i] == "`":
            debut, fin = i + 1, texte.find("`", i + 1)
            fin = len(texte) if fin < 0 else fin
        else:
            i += 1
            continue
        trouvees.append((i, fin, texte[debut:fin]))
        i = fin + 1
    return trouvees


def _commande(texte, lieu):
    texte, a_examiner = _heredocs(texte.replace("\\\n", " "))
    texte = BRANCHE_COURANTE.sub("HEAD", texte)  # "$(git branch --show-current)" : la branche courante
    # Chaque $(…) est mis de côté et remplacé par une valeur illisible : son cd ne doit pas compter pour la suite.
    for debut, fin, interieur in reversed(_substitutions(texte)):
        a_examiner.append(interieur)
        texte = texte[:debut] + "${_SOUS_COMMANDE_}" + texte[fin + 1:]
    try:
        lexeur = shlex.shlex(texte.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexeur.whitespace_split = True
        mots = list(lexeur)
    except ValueError:  # guillemet non fermé : le shell refuserait aussi ; découpage simple
        mots = texte.replace("\n", " ; ").split()
    dossiers, sous_shells = [(lieu.dossier, lieu.inconnu)], []
    for segment in _segments(mots):
        if segment == "(":  # ( cd x && … ) : ce qui change dedans ne ressort pas
            sous_shells.append((lieu.dossier, lieu.inconnu, dict(lieu.variables)))
        elif segment == ")":
            if sous_shells:
                lieu.dossier, lieu.inconnu, lieu.variables = sous_shells.pop()
        else:
            raison = _segment(segment, lieu)
            if raison:
                return raison
        if (lieu.dossier, lieu.inconnu) not in dossiers:
            dossiers.append((lieu.dossier, lieu.inconnu))
    # $(…), `…` et heredocs lus par un shell tournent dans un sous-shell, après les cd qui les précèdent : chacun est
    # examiné dans une copie du lieu, pour chaque dossier où passe la commande. Chaque bout est plus court : la
    # récursion s'arrête.
    for interieur in a_examiner:
        for dossier, inconnu in dossiers:
            raison = _commande(interieur, lieu.enfant(dossier, inconnu))
            if raison:
                return raison
    return None


def _segments(mots):
    """Découpe aux ; && || | & et saute les redirections (> f, 2>&1, << EOF). Rend « ( » et « ) » à part."""
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
                yield from (c for c in mot if c in "()")
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
    if nom in PREFIXES:  # sudo -u root rm…, env A=1 git…, timeout -s KILL 30 git… : la vraie commande suit
        valeurs, a_sauter = PREFIXES[nom]
        k = 0
        while k < len(args) and args[k].startswith("-") and args[k] != "-":
            if args[k] == "--":
                k += 1
                break
            k += 2 if _prend_une_valeur(args[k], valeurs) else 1
        while k < len(args) and AFFECTATION.match(args[k]):
            k += 1
        k += a_sauter
        return _segment(args[k:], lieu) if k < len(args) else None
    if nom in ("cd", "pushd"):
        cibles = [mot for mot in args if not (mot.startswith("-") and mot != "-")]  # cd -P x : x
        lieu.dossier, lieu.inconnu = lieu.aller(cibles[0] if cibles else "~")
        return None
    if nom in COQUILLES:
        for k, mot in enumerate(args[:-1]):
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", mot):
                return _commande(args[k + 1], lieu.enfant())  # bash -c : un sous-shell
        return None
    if nom == "eval":
        return _commande(" ".join(args), lieu)
    if nom == "git":
        return _git(args, lieu)
    if nom == "rm":
        return _rm(args, lieu)
    return None


def _prend_une_valeur(option, valeurs):
    """-u root, -Eu root, --user root : la valeur est le mot suivant ; -uroot et --user=root la portent déjà."""
    if option.startswith("--"):
        return "=" not in option and option in valeurs
    for k, lettre in enumerate(option[1:]):
        if "-" + lettre in valeurs:
            return k == len(option) - 2  # dernière lettre : la valeur suit ; sinon elle est collée
    return False


def _git(args, lieu):
    dossier, inconnu, i = lieu.dossier, lieu.inconnu, 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] in OPTIONS_GIT_AVEC_VALEUR and i + 1 < len(args):
            if args[i] == "-C":
                dossier, inconnu = lieu.enfant(dossier, inconnu).aller(args[i + 1])
            i += 1
        i += 1
    if i >= len(args):
        return None
    if args[i] == "reset":
        return RESET if "--hard" in args[i + 1:] else None
    if args[i] == "push":
        return _push(args[i + 1:], dossier, lieu, inconnu)
    return None


def _push(args, dossier, lieu, inconnu=False):
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
            if inconnu:
                return DOSSIER_INCONNU
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
        if "$" in lieu.developpe(cible):  # $VIDE/*, ${D:-/} : une variable vide ou inconnue peut viser /
            return RM_VARIABLE.format(cible)
        if cible == "*" or cible.endswith("/*"):
            cible = cible[:-1] or "."  # « rm -rf dossier/* » vide le dossier lui-même
        relatif = os.path.normpath(lieu.developpe(cible))
        if lieu.inconnu and not relatif.startswith(("/", "~")) and (
                relatif in (".", ".git") or all(partie == ".." for partie in relatif.split("/"))):
            return RM_DOSSIER.format(cible)  # le dossier inconnu lui-même, ou au-dessus : peut-être le projet
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
