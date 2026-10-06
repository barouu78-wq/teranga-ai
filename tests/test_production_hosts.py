"""Mode production : hôtes de confiance, sans bloquer le contrôle de santé de l'hébergeur."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SCRIPT = """
import json, logging
logging.disable(50)
import app as A
c = A.app.test_client()
out = {}
for host in ["teranga-ai.fr", "localhost:10000", "10.214.5.7:10000", "mon-site.onrender.com", "evil.example"]:
    out[host] = [c.get("/health", headers={"Host": host}).status_code, c.get("/", headers={"Host": host}).status_code]
print(json.dumps(out))
"""


def test_production_rejects_unknown_hosts_but_keeps_health_reachable():
    env = {
        **os.environ,
        "TERANGA_ENV": "production",
        "SECRET_KEY": "x" * 40,
        "OPENAI_API_KEY": "test-key",
        "RENDER_EXTERNAL_HOSTNAME": "mon-site.onrender.com",
    }
    env.pop("TRUSTED_HOSTS", None)
    result = subprocess.run([sys.executable, "-c", _SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    codes = json.loads(result.stdout.strip().splitlines()[-1])
    # Contrôle de santé par adresse interne : toujours 200.
    assert codes["10.214.5.7:10000"][0] == 200
    # Pages : seulement les hôtes de confiance (et l'adresse Render fournie automatiquement).
    assert codes["teranga-ai.fr"] == [200, 200]
    assert codes["mon-site.onrender.com"][1] == 200
    assert codes["10.214.5.7:10000"][1] == 400
    assert codes["evil.example"][1] == 400


def test_production_refuses_to_start_without_a_strong_secret():
    env = {**os.environ, "TERANGA_ENV": "production", "SECRET_KEY": "court", "OPENAI_API_KEY": "test-key"}
    result = subprocess.run([sys.executable, "-c", "import app"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode != 0 and "SECRET_KEY" in result.stderr
