"""Le son de /tts (MP3 en flux) se lit pendant qu'il arrive, sans attendre la fin du fichier.

Avant : la page attendait tout le WAV (11 à 18 s de génération mesurées sur Render) avant le premier son.
Le flux de /tts est livré en deux temps par le test (voice_harness : stream_tts, tts_push, tts_end) :
la première moitié du MP3 doit déjà s'entendre alors que la seconde n'est pas arrivée.
"""

import re

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - la fixture « browser » (conftest) ignore ou fait échouer selon E2E_REQUIRED
    expect = None

from .voice_harness import VoiceBench, mp3_bytes

T = 15000
LISTENING = re.compile("écoute")
SPEAKING = re.compile("parle")
REPLY = "Il est midi à Dakar."


def streamed_voice_turn(page, base_url):
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    bench.stream_tts()
    bench.open()
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    bench.wait_chat_stream(timeout=T)
    bench.chat_event(d=REPLY)
    bench.chat_end()
    bench.wait_tts_stream(timeout=T)
    return bench


def test_streamed_mp3_is_heard_before_the_end_of_the_file(page, base_url):
    bench = streamed_voice_turn(page, base_url)
    text = page.locator("#voiceText")
    audio = mp3_bytes()
    half = len(audio) // 2

    assert bench.tts_push(audio[:half])
    expect(text).to_have_text(SPEAKING, timeout=T)  # le son part avec la moitié du fichier
    bench.wait_playing(timeout=T)

    assert bench.tts_push(audio[half:])
    bench.tts_end()
    expect(text).to_have_text(LISTENING, timeout=T)  # la lecture va au bout, puis l'écoute reprend
    bench.wait_recording(timeout=T)
    assert page.evaluate("() => window.__tts.calls.length") == 1  # un seul appel, servi en flux
    assert page.errors == []


def test_stop_during_a_streamed_voice_cuts_the_stream(page, base_url):
    bench = streamed_voice_turn(page, base_url)
    audio = mp3_bytes()
    bench.tts_push(audio[: len(audio) // 2])
    bench.wait_playing(timeout=T)

    page.click("#voiceStop")
    bench.wait_tts_aborted(1, timeout=T)  # la suite du flux n'est plus lue
    assert bench.playing() == 0 and bench.recording() == 0
    assert not bench.tts_push(audio[len(audio) // 2:]), "le flux coupé accepte encore du son"
    assert page.errors == []
