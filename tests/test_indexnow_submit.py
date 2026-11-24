"""Envoi IndexNow (scripts/indexnow_submit.py et .github/workflows/indexnow-submit.yml), vérifié sans réseau.

Constat du 8 novembre 2026 : le workflow ne partait que si le message de fusion contenait « submit IndexNow URLs »
(jamais depuis sa création) et ne signalait que 6 adresses écrites à la main, sur 206 pages dans le plan du site.
Le script lit maintenant le plan du site publié et signale toutes ses pages, sur demande (bouton « Run workflow »).
"""

import json
from pathlib import Path

from app import INDEXNOW_KEY
from scripts.indexnow_submit import KEY, build_payload

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "indexnow-submit.yml").read_text(encoding="utf-8")

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://teranga-ai.fr/</loc></url>
  <url><loc>https://teranga-ai.fr/lieux/ile-de-goree</loc></url>
  <url><loc>https://teranga-ai.fr/lieux/ile-de-goree</loc></url>
  <url><loc>https://teranga-ai.onrender.com/</loc></url>
  <url><loc>http://teranga-ai.fr/non-securise</loc></url>
</urlset>"""


def test_toutes_les_pages_du_plan_du_site_sont_signalees_une_fois():
    payload = build_payload(SITEMAP)
    assert payload["urlList"] == ["https://teranga-ai.fr/", "https://teranga-ai.fr/lieux/ile-de-goree"]


def test_l_envoi_vise_le_domaine_et_la_cle_que_le_site_publie():
    payload = build_payload(SITEMAP)
    assert payload["host"] == "teranga-ai.fr"
    assert KEY == INDEXNOW_KEY  # le site sert /<clé>.txt : une autre clé serait refusée
    assert payload["key"] == KEY
    assert payload["keyLocation"] == f"https://teranga-ai.fr/{KEY}.txt"
    json.dumps(payload)  # corps JSON valide


def test_le_workflow_se_lance_a_la_main_et_lit_le_plan_du_site_publie():
    trigger = WORKFLOW.split("jobs:")[0]
    assert "workflow_dispatch" in trigger
    assert "push:" not in trigger  # pas d'envoi à chaque fusion : IndexNow demande de ne signaler que les changements
    assert "python scripts/indexnow_submit.py" in WORKFLOW
    assert "onrender.com" not in WORKFLOW
