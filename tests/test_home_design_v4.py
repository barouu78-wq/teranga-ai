from pathlib import Path

HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_composer_keeps_core_controls_and_focus_states():
    html = HOME.read_text(encoding="utf-8")
    for marker in ('id="input"', 'id="send"', 'id="mic"', 'id="voiceToggle"'):
        assert marker in html
    assert "#input:focus-visible" in html
    assert "#send:focus-visible" in html


def test_composer_is_responsive_and_keyboard_friendly():
    html = HOME.read_text(encoding="utf-8")
    assert "@media(max-width:680px)" in html
    assert "font-size:16px" in html
    assert "prefers-reduced-motion:reduce" in html


def test_suggestion_chips_remain_scrollable_on_mobile():
    html = HOME.read_text(encoding="utf-8")
    assert ".chips{gap:6px;overflow-x:auto" in html
    assert ".chips button{flex:0 0 auto" in html
