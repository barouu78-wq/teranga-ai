from pathlib import Path

HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_accessibility_has_visible_focus_and_reduced_motion():
    html = HOME.read_text(encoding="utf-8")
    assert ":focus-visible{outline:2px solid var(--nav-gold)" in html
    assert "@media(prefers-reduced-motion:reduce)" in html
    assert "scroll-behavior:auto!important" in html


def test_accessibility_supports_forced_colors():
    html = HOME.read_text(encoding="utf-8")
    assert "@media(forced-colors:active)" in html
    assert "border:2px solid ButtonText" in html


def test_mobile_safe_area_is_preserved():
    html = HOME.read_text(encoding="utf-8")
    assert "env(safe-area-inset-top)" in html
    assert "env(safe-area-inset-bottom)" in html


def test_journey_buttons_have_single_deterministic_handlers():
    html = HOME.read_text(encoding="utf-8")
    assert '[data-journey="travel"]?.addEventListener' in html
    assert '[data-journey="project"]?.addEventListener' in html
    assert '[data-journey="discover"]?.addEventListener' in html
    assert '[data-journey="chat"]?.addEventListener' in html
    assert "Journey buttons are wired individually above" in html
    assert "journey==='discover') window.location.href='/explorer'" not in html
