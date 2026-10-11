"""Réglages Gunicorn : le fichier `gunicorn.conf.py` est celui qui s'applique en production.

Constat du 10 octobre 2026 (journaux Render) : le service tournait avec `gunicorn app:app`, c'est-à-dire un
seul processus « sync » et un délai de 30 s, alors que `Procfile`, `render.yaml` et `Dockerfile` demandent
2 processus × 4 fils et 120 s. Le planificateur de voyage était coupé par `WORKER TIMEOUT`.
"""
import re
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
FICHIER = RACINE / "gunicorn.conf.py"


def _lire(monkeypatch, **env):
    for nom in ("GUNICORN_WORKERS", "GUNICORN_THREADS"):
        monkeypatch.delenv(nom, raising=False)
    for nom, valeur in env.items():
        monkeypatch.setenv(nom, valeur)
    return runpy.run_path(str(FICHIER))


def test_valeurs_par_defaut(monkeypatch):
    conf = _lire(monkeypatch)
    assert conf["workers"] == 2
    assert conf["threads"] == 4
    assert conf["timeout"] == 120
    assert conf["graceful_timeout"] == 30
    assert conf["keepalive"] == 30


def test_le_delai_depasse_le_defaut_de_gunicorn(monkeypatch):
    # Le défaut de Gunicorn (30 s) coupait les générations longues.
    assert _lire(monkeypatch)["timeout"] > 30


def test_variables_d_environnement_valides(monkeypatch):
    conf = _lire(monkeypatch, GUNICORN_WORKERS="3", GUNICORN_THREADS="2")
    assert (conf["workers"], conf["threads"]) == (3, 2)


@pytest.mark.parametrize("valeur", ["", "abc", "0", "-1", "17", "2.5"])
def test_valeurs_invalides_ignorees(monkeypatch, valeur):
    conf = _lire(monkeypatch, GUNICORN_WORKERS=valeur, GUNICORN_THREADS=valeur)
    assert (conf["workers"], conf["threads"]) == (2, 4)


def test_gunicorn_applique_le_fichier_sans_option_en_ligne_de_commande():
    """Reproduit le démarrage de Render (`gunicorn app:app`, sans option) depuis la racine du dépôt."""
    script = (
        "import sys\n"
        "sys.argv = ['gunicorn', 'app:app']\n"
        "from gunicorn.app.wsgiapp import WSGIApplication\n"
        "cfg = WSGIApplication('%(prog)s [OPTIONS] [APP_MODULE]').cfg\n"
        "print(cfg.workers, cfg.threads, cfg.timeout, cfg.worker_class.__name__)\n"
    )
    env = {"PATH": "/usr/bin:/bin", "HOME": str(RACINE)}
    resultat = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=RACINE, env=env, capture_output=True, text=True, timeout=60, check=False,
    )
    assert resultat.returncode == 0, resultat.stderr
    assert resultat.stdout.split() == ["2", "4", "120", "ThreadWorker"]


def _option(texte, nom):
    """Valeur numérique d'une option, y compris `--workers ${GUNICORN_WORKERS:-2}` (valeur par défaut)."""
    trouve = re.search(rf"--{nom}[ =](?:\$\{{\w+:-(\d+)\}}|(\d+))", texte)
    assert trouve, f"--{nom} introuvable"
    return int(trouve.group(1) or trouve.group(2))


@pytest.mark.parametrize("nom", ["Procfile", "render.yaml", "Dockerfile"])
def test_les_trois_demarrages_du_depot_disent_la_meme_chose(nom, monkeypatch):
    conf = _lire(monkeypatch)
    # Uniquement la ligne de démarrage (le Dockerfile a aussi un `HEALTHCHECK --timeout=5s`).
    lignes = (RACINE / nom).read_text(encoding="utf-8").splitlines()
    texte = "\n".join(ligne for ligne in lignes if "gunicorn" in ligne and "--workers" in ligne)
    assert texte, f"commande gunicorn introuvable dans {nom}"
    assert _option(texte, "workers") == conf["workers"]
    assert _option(texte, "threads") == conf["threads"]
    assert _option(texte, "timeout") == conf["timeout"]
    assert _option(texte, "graceful-timeout") == conf["graceful_timeout"]
