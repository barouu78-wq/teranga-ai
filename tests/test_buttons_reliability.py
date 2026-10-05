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


def test_mic_never_stays_in_a_dead_listening_state():
    assert "async function startVoiceOrExplain()" in JS
    start = JS.index("async function startVoiceOrExplain()")
    body = JS[start:JS.index("\n}", start)]
    assert "try{ok=await startRealtimeVoice();}catch(_){ok=false;}" in body
    assert "endVoiceMode();" in body and "voiceStatus(" in body


def test_blocked_storage_never_breaks_buttons():
    # Tous les accès passent par LS/SS (repli mémoire) : plus d'exception
    # quand le navigateur bloque le stockage.
    after_helpers = JS.split("const LS=safeStore('localStorage'),SS=safeStore('sessionStorage');", 1)[1]
    assert "localStorage." not in after_helpers and "sessionStorage." not in after_helpers
    start = JS.index("async function ask(")
    body_at = JS.index("const body=JSON.stringify({message:text", start)
    assert JS.index("try{", start) < body_at  # préparé dans le bloc protégé
