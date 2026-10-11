"""Voix fluide : pas de blanc entre deux morceaux de la réponse, et une interruption est entendue.

Chaque attente passe par wait_held / wait_tts_calls / une condition visible, jamais par une pause de durée fixe avant un
release : un navigateur ralenti (E2E_CPU_THROTTLE=12) ne doit faire échouer aucun test.
"""

import re

import pytest

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - la fixture « browser » (conftest) ignore ou fait échouer selon E2E_REQUIRED
    expect = None

from .voice_harness import VoiceBench, wav_bytes

T = 20000  # attentes visibles : larges, pour un navigateur ralenti
LISTENING = re.compile("écoute")

FIRST = "Dakar est la capitale du Sénégal, une grande ville posée sur la presqu’île du Cap-Vert."
SECOND = "Le Plateau concentre les ministères, les banques et les ambassades, tandis que la Médina garde l’âme populaire de la ville."
THIRD = "Les Almadies, au nord-ouest, sont connues pour leurs plages, leurs restaurants et le point le plus occidental du continent."


# Les fichiers de voix sont les seuls à recevoir une URL de fichier (URL.createObjectURL) : on compte celles qui restent ouvertes.
LIVE_URLS = """
(() => {
  const live = window.__liveUrls = new Set();
  const make = URL.createObjectURL.bind(URL), drop = URL.revokeObjectURL.bind(URL);
  URL.createObjectURL = (blob) => { const url = make(blob); live.add(url); return url; };
  URL.revokeObjectURL = (url) => { live.delete(url); drop(url); };
})();
"""


def two_part_answer(page, base_url, first_ms=6000, rest_ms=900):
    """Une réponse en deux parties : la 1re parle (first_ms), la suite est déjà arrivée et sa voix est prête (rest_ms)."""
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    bench.hold("tts")
    bench.open()
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    bench.wait_chat_stream(timeout=T)
    bench.chat_event(d=FIRST + " ")
    bench.chat_event(d=SECOND[:12])
    bench.wait_held("tts", timeout=T)
    bench.release("tts", body=wav_bytes(first_ms), content_type="audio/wav")
    bench.wait_playing(timeout=T)  # la 1re partie parle
    bench.chat_event(d=SECOND[12:] + " " + THIRD)
    bench.chat_end()
    bench.wait_tts_calls(2, timeout=T)
    bench.wait_held("tts", timeout=T)
    bench.release("tts", body=wav_bytes(rest_ms), content_type="audio/wav")
    return bench


def test_the_second_part_is_ready_while_the_first_one_is_still_speaking(page, base_url):
    """Avant : le lecteur du morceau suivant n'était monté qu'à la fin du précédent, donc le navigateur ouvrait le fichier
    (et l'audio se préparait) au moment où la voix devait déjà continuer : un blanc entre les deux morceaux."""
    bench = two_part_answer(page, base_url)
    # La 1re partie parle encore (6 s) ; la suite est arrivée : son lecteur existe déjà et a chargé son fichier.
    page.wait_for_function(
        "() => window.__mic.audios.length === 2 && window.__mic.audios[1].readyState >= 3", timeout=T
    )
    state = page.evaluate(
        """() => ({
            playing: window.__mic.playing(),
            firstEnded: window.__mic.audios[0].ended,
            secondPaused: window.__mic.audios[1].paused,
        })"""
    )
    assert state == {"playing": 1, "firstEnded": False, "secondPaused": True}, state
    # ... puis elle prend le relais sans rien lire deux fois.
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=30000)
    bench.wait_recording(timeout=T)
    assert len(bench.tts_calls) == 2 and page.evaluate("() => window.__mic.audios.length") == 2
    assert page.errors == []


@pytest.mark.parametrize("phase", ["first_part_playing", "rest_ready"])
def test_stop_cuts_a_second_part_that_was_already_prepared(page, base_url, phase):
    """Un morceau préparé à l'avance ne doit pas survivre à « Arrêter » : ni son, ni lecteur ou fichier resté ouvert."""
    page.add_init_script(LIVE_URLS)
    bench = two_part_answer(page, base_url)
    page.wait_for_function("() => window.__mic.audios.length === 2", timeout=T)
    if phase == "rest_ready":
        page.wait_for_function("() => window.__mic.audios[1].readyState >= 3", timeout=T)
    assert page.evaluate("() => window.__liveUrls.size") == 2, "les deux fichiers de voix devraient être ouverts avant l'arrêt"
    page.click("#voiceStop")
    expect(page.locator("#voiceBar")).to_be_hidden(timeout=T)
    page.wait_for_function("() => window.__mic.playing() === 0", timeout=T)
    page.wait_for_timeout(1500)  # la 1re partie aurait fini, la suite aurait pris le relais
    assert bench.playing() == 0 and bench.recording() == 0
    assert page.evaluate("() => window.__mic.audios.every(a => a.paused || a.ended)")
    assert page.evaluate("() => window.__liveUrls.size") == 0, "un fichier de voix est resté ouvert après l'arrêt"
    assert len(bench.tts_calls) == 2, "une voix a été demandée après l'arrêt"
    assert page.errors == []


def test_the_gap_between_two_parts_stays_short(page, base_url):
    """Garde-fou du banc SIMULÉ : du dernier instant de la 1re partie au premier son de la 2e. Large exprès (navigateur
    ralenti 12 fois compris) ; il n'échoue que si le relais redevient nettement lent."""
    bench = two_part_answer(page, base_url, first_ms=1500)
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=30000)
    sounds = [at for name, at in bench.marks() if name == "sound"]
    ends = [at for name, at in bench.marks() if name == "sound-end"]
    assert len(sounds) == 2 and len(ends) >= 1, (sounds, ends)
    gap = sounds[1] - ends[0]  # le 2e son démarre, moins la fin du 1er
    print(f"\n[banc SIMULÉ] blanc entre les deux morceaux : {gap:.0f} ms")
    assert gap <= 450, f"blanc entre les deux morceaux : {gap:.0f} ms"
