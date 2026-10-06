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
for host in ["mon-site.onrender.com", "www.teranga-ai.fr"]:
    r = c.get("/lieux?q=goree", headers={"Host": host})
    out["redirect " + host] = [r.status_code, r.headers.get("Location")]
out["post onrender"] = c.post("/chat", headers={"Host": "mon-site.onrender.com"}).status_code
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
    # L'adresse Render et www. redirigent définitivement vers le domaine principal
    # (une seule copie du site pour Google) ; /health et les POST ne sont pas redirigés.
    assert codes["mon-site.onrender.com"] == [200, 301]
    assert codes["redirect mon-site.onrender.com"] == [301, "https://teranga-ai.fr/lieux?q=goree"]
    assert codes["redirect www.teranga-ai.fr"] == [301, "https://teranga-ai.fr/lieux?q=goree"]
    assert codes["post onrender"] != 301
    assert codes["10.214.5.7:10000"][1] == 400
    assert codes["evil.example"][1] == 400


def test_production_refuses_to_start_without_a_strong_secret():
    env = {**os.environ, "TERANGA_ENV": "production", "SECRET_KEY": "court", "OPENAI_API_KEY": "test-key"}
    result = subprocess.run([sys.executable, "-c", "import app"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode != 0 and "SECRET_KEY" in result.stderr


def test_health_survives_a_custom_trusted_hosts_list():
    """TRUSTED_HOSTS remplacé (nouveau domaine) : le contrôle de santé interne répond toujours."""
    env = {
        **os.environ,
        "TERANGA_ENV": "production",
        "SECRET_KEY": "x" * 40,
        "OPENAI_API_KEY": "test-key",
        "TRUSTED_HOSTS": "teranga-ai.fr,nouveau-domaine.sn",
    }
    script = (
        "import logging; logging.disable(50)\n"
        "import app as A\n"
        "c = A.app.test_client()\n"
        "print(c.get('/health', headers={'Host': '10.0.0.9:10000'}).status_code)\n"
        "print('https://www.teranga-ai.fr' in A.ALLOWED_ORIGINS)\n"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.split() == ["200", "True"]
