from pathlib import Path

HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"


def test_home_conversation_layout_has_desktop_and_mobile_rules():
    html = HOME.read_text(encoding="utf-8")
    assert "body.has-chat #stage" in html
    assert "body.has-chat #messages" in html
    assert "body.has-chat .dock" in html
    assert "@media(max-width:680px)" in html


def test_home_conversation_keeps_accessible_focus_states():
    html = HOME.read_text(encoding="utf-8")
    assert ".journey-strip button:focus-visible" in html
    assert ".audience-btn:focus-visible" in html
    assert "outline:2px solid var(--sen-gold)" in html
