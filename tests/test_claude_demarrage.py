"""Le premier mot du chat attendait 4 à 9 s après chaque mise en ligne (journaux « latence » du 15 au 18 novembre
2026) : chaque processus Gunicorn ne chargeait le SDK Anthropic qu'à la première question posée à Claude (1,7 s rien
que pour l'import sur une machine rapide, davantage sur Render). Il est chargé au démarrage, avant toute question."""

import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def test_le_sdk_claude_est_charge_au_demarrage_du_serveur():
    env = {**os.environ, "OPENAI_API_KEY": "test-key"}
    sortie = subprocess.run([sys.executable, "-c", "import sys, wsgi; print('anthropic' in sys.modules)"],
                            cwd=RACINE, env=env, capture_output=True, text=True, timeout=120)
    assert sortie.returncode == 0, sortie.stderr[-2000:]
    assert sortie.stdout.strip().splitlines()[-1] == "True"
