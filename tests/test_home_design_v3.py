from pathlib import Path

HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_navigation_has_active_state_and_keyboard_focus():
    html = HOME.read_text(encoding="utf-8")
    assert ".tabbar button.on" in html
    assert ".tabbar button.on:after" in html
    assert ".tabbar button:focus-visible" in html


def test_mobile_navigation_remains_visible_and_compact():
    html = HOME.read_text(encoding="utf-8")
    assert ".tabbar{display:grid!important}" in html
    assert "grid-template-columns:repeat(4,1fr)" in html
    assert "env(safe-area-inset-bottom)" in html


def test_journey_cards_keep_three_entry_points():
    html = HOME.read_text(encoding="utf-8")
    for marker in ('data-journey="travel"', 'data-journey="discover"', 'data-journey="chat"'):
        assert marker in html
    assert ".journey-strip button" in html
    assert "text-overflow:ellipsis" in html
