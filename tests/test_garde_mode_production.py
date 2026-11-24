"""Audit de sécurité du 1er novembre 2026 (constat 3) : TERANGA_ENV absent ou mal écrit coupait sans prévenir les
protections de production (longueur de SECRET_KEY, TRUSTED_HOSTS, redirection des hôtes alias).

Render pose RENDER=true sur chaque service (https://render.com/docs/environment-variables). Sur Render, le site
refuse donc de démarrer si TERANGA_ENV ne vaut pas « production », avec un message qui dit quoi régler. Un
déploiement refusé laisse en ligne la version précédente. En local (sans RENDER), rien ne change.
L'application est importée dans un interpréteur neuf : la vérification se fait à l'import de `app`.
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = "import logging; logging.disable(50); import app; print('demarre', app.RUNTIME_ENV)"
SECRET = "s" * 40


def _start(**variables):
    env = {**os.environ, "OPENAI_API_KEY": "test-key"}
    for name in ("TERANGA_ENV", "RENDER", "SECRET_KEY", "REDIS_URL"):
        env.pop(name, None)
    env.update(variables)
    return subprocess.run([sys.executable, "-c", _SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


def test_on_render_the_site_refuses_to_start_without_production_mode():
    cases = [{"RENDER": "true"}, {"RENDER": "true", "TERANGA_ENV": "prod"}, {"RENDER": "true", "TERANGA_ENV": "development"}]
    with ThreadPoolExecutor(max_workers=len(cases)) as pool:
        results = list(pool.map(lambda variables: _start(SECRET_KEY=SECRET, **variables), cases))
    for variables, result in zip(cases, results):
        assert result.returncode != 0, variables
        assert "TERANGA_ENV=production" in result.stderr, (variables, result.stderr[-500:])


def test_on_render_production_mode_starts():
    result = _start(RENDER="true", TERANGA_ENV="Production ", SECRET_KEY=SECRET)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "demarre production" in result.stdout


def test_outside_render_nothing_changes():
    result = _start()
    assert result.returncode == 0, result.stderr[-2000:]
    assert "demarre development" in result.stdout
