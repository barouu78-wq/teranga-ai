"""Fiabilité des boutons de l'accueil (bugs « le bouton ne répond plus »)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
HTML = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")


def test_listen_button_can_never_stay_stuck():
    # Avant : désactivé sur « … » puis jamais réactivé si la lecture était interrompue.
    assert "btn.disabled=true;btn.textContent='…'" not in HTML
    assert "function resetListenButton" in HTML and "const stale=()=>" in HTML
    assert "listen.dataset.speaking==='1'" in JS  # second appui = arrêt


def test_only_one_question_at_a_time():
    assert "if(inflight){send.classList.remove('nudge')" in JS


def test_long_answers_use_an_idle_timeout_and_offer_retry():
    assert "const kill=setTimeout(()=>ctrl.abort(),40000)" not in JS
    assert "if(done)break;\n      arm();" in JS
    assert "if(!aborted||timedOut)" in JS


def test_taps_have_no_300ms_delay():
    assert "touch-action:manipulation" in HTML
    assert "touch-action:manipulation" in (ROOT / "static" / "site.css").read_text(encoding="utf-8")
