"""Empreinte des fichiers statiques (?v=) : seul un vrai fichier du dossier static/ est lu (audit du 27 novembre 2026).

Le nom vient aussi de l'adresse demandée (en-têtes de cache d'app.py) : un nom qui sort de static/ ne doit jamais
faire lire un autre fichier du serveur, ni un fichier spécial qui ne finit pas.
"""

import hashlib
import os
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

ROOT = Path(__file__).resolve().parents[1]
B = "https://teranga-ai.fr"


@pytest.mark.parametrize("name", ["../config.py", "..\\config.py", "../../etc/passwd", "/etc/passwd",
                                  "fonts/../../app.py", "fonts", ""])
def test_un_nom_hors_de_static_n_est_jamais_lu(monkeypatch, name):
    from services import site_layout

    lus = []
    original = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: lus.append(str(self)) or original(self))
    assert site_layout.asset_version(name) == ""
    assert lus == [], lus


def test_un_vrai_fichier_garde_son_empreinte_et_une_seule_entree():
    from services import site_layout

    attendu = hashlib.sha256((ROOT / "static" / "site.css").read_bytes()).hexdigest()[:10]
    assert site_layout.asset_version("site.css") == attendu
    assert site_layout.asset_version("./site.css") == attendu
    assert site_layout.asset_version("fonts/../site.css") == attendu
    assert not [k for k in site_layout._VERSIONS if k != "site.css" and k.endswith("site.css")]


def test_une_adresse_qui_sort_de_static_n_a_pas_le_cache_d_un_an():
    from app import app

    empreinte = hashlib.sha256((ROOT / "config.py").read_bytes()).hexdigest()[:10]
    reponse = app.test_client().get(f"/static/..%2fconfig.py?v={empreinte}", base_url=B)
    assert "immutable" not in reponse.headers.get("Cache-Control", "")


def test_un_fichier_du_site_a_jour_garde_son_cache_d_un_an():
    from app import app
    from services.site_layout import asset_version

    reponse = app.test_client().get(f"/static/site.css?v={asset_version('site.css')}", base_url=B)
    assert reponse.status_code == 200
    assert "immutable" in reponse.headers.get("Cache-Control", "")
