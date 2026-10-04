"""Widget partenaire : script public chargeable depuis un autre site."""

import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app import app

    return app.test_client()


def test_widget_script_can_be_loaded_by_partner_sites():
    response = _client().get("/widget.js", base_url="https://teranga-ai.fr")
    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert response.headers["Cross-Origin-Resource-Policy"] == "cross-origin"
    assert "max-age" in response.headers["Cache-Control"]


def test_other_resources_stay_same_origin():
    response = _client().get("/sw.js", base_url="https://teranga-ai.fr")
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_widget_reads_nothing_from_the_partner_page():
    source = (ROOT / "static" / "widget.js").read_text(encoding="utf-8")
    assert "attachShadow" in source
    assert "document.cookie" not in source and "localStorage" not in source
    assert "fetch(" not in source and "XMLHttpRequest" not in source
    # window.open avec « noopener » renverrait null et ouvrirait un second onglet.
    assert '"popup=yes,width=440,height=760"' in source and "popup.opener = null" in source


def test_business_page_shows_the_snippet_as_text():
    html = _client().get("/pour-les-entreprises", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert "&lt;script src=\"https://teranga-ai.fr/widget.js\"" in html
    assert '<script src="https://teranga-ai.fr/widget.js"' not in html


def test_home_prefills_question_and_language_from_the_url():
    source = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
    assert "urlParams.get('q')" in source and "urlParams.get('lang')" in source


def test_restored_history_keeps_share_links_and_paragraphs():
    source = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
    assert "share:shareToken" in source and "item.share||''" in source
    # « /\\s+/ » dans un fichier .js cherche une barre oblique inverse, pas un espace.
    assert "\\\\s" not in source
