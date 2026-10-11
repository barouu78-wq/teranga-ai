"""Parler par-dessus la voix de l'assistant : la parole est entendue et envoyée, elle n'est pas prise pour du bruit.

Chaque attente passe par une condition visible (wait_stt_calls, wait_recording…), jamais par une pause de durée fixe :
un navigateur ralenti (E2E_CPU_THROTTLE=12) ne doit faire échouer aucun test.
"""

import re

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - la fixture « browser » (conftest) ignore ou fait échouer selon E2E_REQUIRED
    expect = None

from .voice_harness import VoiceBench, wav_bytes

T = 20000  # attentes visibles : larges, pour un navigateur ralenti


def interrupted_by_speech(page, base_url):
    """Une 1re question, sa réponse se lit longtemps, puis la personne parle par-dessus (niveau constant) jusqu'à ce que
    la voix se coupe et que l'écoute reprenne alors qu'elle parle encore. Renvoie le banc."""
    bench = VoiceBench(page, base_url)
    # 1re réponse : 15 s de voix (on l'interrompt) ; les suivantes sont courtes.
    bench.tts_handler = lambda route, n: route.fulfill(body=wav_bytes(15000 if n == 1 else 600), content_type="audio/wav")
    bench.open()
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    bench.wait_stt_calls(1, timeout=T)
    bench.wait_playing(timeout=T)
    expect(page.locator("#voiceText")).to_have_text(re.compile("parle"), timeout=T)
    bench.set_level(0.3)  # la personne parle par-dessus la voix, sans s'arrêter
    page.wait_for_function("() => window.__mic.playing() === 0", timeout=T)  # la voix se coupe
    bench.wait_recording(timeout=T)  # l'écoute reprend alors que la personne parle encore
    return bench


def test_speaking_over_the_voice_is_heard_and_sent(page, base_url):
    """Avant : l'écoute rouverte par l'interruption apprenait le « bruit de fond » pendant que la personne parlait déjà,
    prenait sa voix pour du bruit, ne détectait plus aucune parole et n'envoyait rien (il fallait répéter).

    Avec le faux micro, la voix de la personne est un son de niveau constant : c'est le cas le plus net. Une vraie voix
    varie, donc elle était reconnue par moments seulement (non mesuré ici)."""
    bench = interrupted_by_speech(page, base_url)
    expect(page.locator("#voiceText")).to_have_text(re.compile("entends"), timeout=T)  # sa parole est reconnue comme telle
    bench.set_level(0)  # elle a fini
    bench.wait_stt_calls(2, timeout=T)  # ... et sa phrase est envoyée
    assert page.errors == []


def test_after_a_barge_in_a_quiet_room_still_ends_the_turn_and_the_next_turn_works(page, base_url):
    """L'autre sens : après une interruption, un souffle très faible ne tient pas le tour ouvert (on n'attend pas en vain),
    et le tour suivant se passe comme d'habitude (écoute rouverte avec son propre calibrage du bruit)."""
    bench = interrupted_by_speech(page, base_url)
    page.wait_for_function("() => voiceSpeechStarted", timeout=T)  # la parole a été reconnue
    bench.set_level(0.004)  # presque le silence : bien en dessous du seuil de parole
    bench.wait_stt_calls(2, timeout=T)  # la phrase est envoyée une fois le silence tenu, malgré le souffle
    bench.wait_recording(timeout=T)  # réponse lue, écoute rouverte
    bench.set_level(0)
    bench.speak_one_turn()
    bench.wait_stt_calls(3, timeout=T)  # le tour suivant est entendu normalement
    assert page.errors == []
