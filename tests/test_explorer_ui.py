from pathlib import Path


HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"
IMAGES = Path(__file__).resolve().parents[1] / "services" / "images.py"


def test_explorer_prefers_wikimedia_thumbnail_for_fast_loading():
    source = IMAGES.read_text(encoding="utf-8")
    assert 'info.get("thumburl") or info.get("url")' in source


def test_visible_language_selector_excludes_pulaar():
    html = HOME.read_text(encoding="utf-8")
    assert 'data-lang="ff">PU' not in html
    assert 'data-lang="fr"' in html
    assert 'data-lang="en"' in html
    assert 'data-lang="wo"' in html


def test_explorer_uses_google_images_before_wikimedia_fallback():
    route = (Path(__file__).resolve().parents[1] / "routes" / "explorer.py").read_text(encoding="utf-8")
    assert "fetch_google_images(query, limit=4)" in route
    assert "if not images:" in route
    assert "fetch_commons_images(query, limit=4)" in route
