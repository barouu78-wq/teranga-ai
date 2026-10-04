from pathlib import Path


HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_home_has_senegal_signature_visual():
    html = HOME.read_text(encoding="utf-8")
    assert 'class="hero-signature"' in html
    assert 'class="hero-lion"' not in html  # design v6 : signature sobre (drapeau), sans emoji
    assert 'class="hero-flag"' in html
    assert "background:#0f6a43" in html
    assert "background:#f0c63d" in html
    assert "background:#c93636" in html


def test_home_keeps_primary_journeys_and_chat_surface():
    html = HOME.read_text(encoding="utf-8")
    for marker in ("data-journey=\"travel\"", "data-journey=\"project\"", "data-journey=\"discover\"", "data-journey=\"chat\""):
        assert marker in html
    assert 'id="input"' in html
    assert 'id="send"' in html
    assert 'id="mic"' in html


def test_home_design_is_responsive():
    html = HOME.read_text(encoding="utf-8")
    assert "@media(max-width:680px)" in html
    assert ".journey-strip{grid-template-columns:repeat(2" in html
    assert "prefers-reduced-motion:reduce" in html
