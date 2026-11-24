"""Cache des réponses : changer de modèle configuré ne doit jamais resservir l'ancienne réponse.

L'empreinte (`_CACHE_MODEL_BASE`) est calculée à l'import de `app` : chaque cas démarre donc
un interpréteur neuf avec ses propres variables d'environnement.
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from services.answer_cache import cache_key

ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = "import logging; logging.disable(50); import app; print(app._CACHE_MODEL_BASE)"


def _fingerprint(**variables):
    env = {**os.environ, "OPENAI_API_KEY": "test-key"}
    for name in ("OPENAI_MODEL", "OPENAI_COMPLEX_MODEL", "OPENAI_TRIP_MODEL", "REDIS_URL", "TERANGA_ENV"):
        env.pop(name, None)
    env.update(variables)
    result = subprocess.run([sys.executable, "-c", _SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout.strip().splitlines()[-1]


def test_cache_fingerprint_changes_with_the_configured_models():
    cases = [
        {},
        {},
        {"OPENAI_MODEL": "autre-modele-rapide"},
        {"OPENAI_COMPLEX_MODEL": "autre-modele-complexe"},
    ]
    with ThreadPoolExecutor(max_workers=len(cases)) as pool:
        default, again, other_fast, other_complex = pool.map(lambda variables: _fingerprint(**variables), cases)

    assert default == again, "l'empreinte doit être stable tant que rien ne change"
    assert default.startswith("gpt-5.6-luna:")
    assert other_fast.startswith("autre-modele-rapide:")
    assert len({default, other_fast, other_complex}) == 3


def test_answer_cache_key_depends_on_the_model_fingerprint():
    payload = {"message": "Que visiter à Dakar ?", "language": "fr"}
    key = cache_key(payload, {}, model="gpt-5.6-luna:abc")
    assert key is not None
    assert cache_key(payload, {}, model="autre-modele:abc") != key
    assert cache_key(payload, {}, model="gpt-5.6-luna:abc") == key


def test_cache_fingerprint_follows_the_choice_of_places():
    # services/intelligence.py construit le texte qui choisit les lieux envoyés à l'IA (contextual_query) :
    # le corriger doit invalider les anciennes réponses, comme pour senegal_knowledge.py.
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    block = source.split("_CACHE_MODEL_BASE = ", 1)[1].split("\n\n", 1)[0]
    assert '"intelligence.py"' in block
