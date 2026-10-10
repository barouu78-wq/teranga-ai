"""Conversation vocale : l'état est visible et annoncé, et « Arrêter » coupe tout, quelle que soit l'étape."""

import re

import pytest
from playwright.sync_api import expect

from .voice_harness import VoiceBench, stream, wav_bytes

PHONE = {"width": 390, "height": 844}
LISTENING = re.compile("écoute")


def long_voice(bench, ms=4000):
    bench.tts_handler = lambda route, n: route.fulfill(body=wav_bytes(ms), content_type="audio/wav")


def test_phone_home_shows_each_step_of_the_voice_turn(page, base_url):
    """Sur l'accueil téléphone (barre du bas cachée) : J'écoute, Je transcris, Je réfléchis, Je parle."""
    page.set_viewport_size(PHONE)
    bench = VoiceBench(page, base_url)
    bench.hold("stt")
    bench.hold("chat")
    bench.hold("tts")
    bench.open()
    page.click("#heroMic")

    text = page.locator("#voiceText")
    expect(page.locator("#voiceBar")).to_be_visible()
    expect(text).to_have_text(LISTENING)
    live = page.locator("#voiceState")
    assert live.get_attribute("role") == "status"
    assert live.get_attribute("aria-live") == "polite"
    expect(live).to_have_text(LISTENING)

    bench.wait_recording()
    page.wait_for_timeout(700)
    bench.set_level(1)
    expect(text).to_have_text(re.compile("entends"))
    bench.set_level(0)
    expect(text).to_have_text(re.compile("transcris"))
    expect(live).to_have_text(re.compile("transcris"))

    bench.release("stt", json={"text": "Quelle heure est-il à Dakar ?"})
    expect(text).to_have_text(re.compile("réfléchis"))

    bench.release("chat", body=stream({"d": "Il est midi."}), content_type="application/x-ndjson")
    expect(text).to_have_text(re.compile("réfléchis"))  # la voix se prépare : on ne dit pas « je parle » avant le son

    bench.release("tts", body=wav_bytes(2500), content_type="audio/wav")
    expect(text).to_have_text(re.compile("parle"))
    # Pendant la voix, un appui sur le micro la coupe et écoute : le libellé le dit.
    assert page.get_attribute("#heroMic", "aria-label") == "Couper la voix et parler"

    expect(text).to_have_text(LISTENING, timeout=10000)  # l'écoute reprend toute seule
    bench.wait_recording()
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    assert page.errors == []


def test_state_and_mic_labels_follow_the_page_language(page, base_url):
    bench = VoiceBench(page, base_url)
    bench.hold("stt")
    bench.open("/?lang=en")
    assert page.get_attribute("#mic", "aria-label") == "Speak"
    page.click("#mic")
    expect(page.locator("#voiceText")).to_have_text(re.compile("listening"))
    assert page.get_attribute("#mic", "aria-label") == "Stop the voice conversation"
    assert page.get_attribute("#heroMic", "aria-label") == "Stop the voice conversation"
    bench.wait_recording()
    bench.speak_one_turn()
    expect(page.locator("#voiceText")).to_have_text(re.compile("Transcribing"))  # et non « I'm listening… »


def test_mic_label_is_not_the_label_of_the_listen_button(page, base_url):
    """Après un tour, le micro s'appelait « Écouter » (le libellé du bouton de lecture)."""
    bench = VoiceBench(page, base_url).open()
    bench.tap_mic()
    bench.wait_recording()
    page.click("#mic")  # arrêt
    expect(page.locator("#voiceBar")).to_be_hidden()
    assert page.get_attribute("#mic", "aria-label") == "Parler"
    assert page.get_attribute("#heroMic", "aria-label") == "Parler"


def test_touch_targets_of_the_voice_controls_are_44px(page, base_url):
    page.set_viewport_size(PHONE)
    bench = VoiceBench(page, base_url).open()
    page.click("#heroMic")
    expect(page.locator("#voiceStop")).to_be_visible()
    for selector in ["#voiceStop", "#heroMic"]:
        box = page.locator(selector).bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, (selector, box)
    bench.page.click("#voiceStop")
    page.fill("#heroInput", "Bonjour")
    page.click("#heroSend")
    page.locator("#voiceToggle").wait_for()
    box = page.locator("#voiceToggle").bounding_box()
    assert box["height"] >= 44, box


@pytest.mark.parametrize("phase", ["listening", "transcribing", "thinking", "speaking"])
def test_stop_button_stops_everything_in_every_phase(page, base_url, phase):
    bench = VoiceBench(page, base_url)
    if phase in ("transcribing", "thinking"):
        bench.hold("stt")
    if phase == "thinking":
        bench.hold("chat")
    if phase == "speaking":
        long_voice(bench, 6000)
    bench.open()
    bench.tap_mic()
    bench.wait_recording()
    if phase != "listening":
        bench.speak_one_turn()
    if phase == "transcribing":
        expect(page.locator("#voiceText")).to_have_text(re.compile("transcris"))
    if phase == "thinking":
        expect(page.locator("#voiceText")).to_have_text(re.compile("transcris"))
        bench.release("stt", json={"text": "Bonjour"})
        expect(page.locator("#voiceText")).to_have_text(re.compile("réfléchis"))
    if phase == "speaking":
        bench.wait_playing()
        expect(page.locator("#voiceText")).to_have_text(re.compile("parle"))

    page.click("#voiceStop")

    assert page.evaluate("() => document.activeElement && document.activeElement.id") == "mic", (
        "le focus clavier doit revenir sur le micro quand le bouton « Arrêter » disparaît"
    )
    assert not page.evaluate("() => document.body.classList.contains('voice-active')")
    expect(page.locator("#voiceBar")).to_be_hidden()
    page.wait_for_timeout(600)
    assert bench.recording() == 0, "le micro est resté ouvert après « Arrêter »"
    assert bench.playing() == 0, "la voix continue après « Arrêter »"
    # Les réponses qui arrivent après l'arrêt n'ont plus d'effet : ni question, ni voix, ni écoute.
    chats, voices = len(bench.chat_calls), len(bench.tts_calls)
    bench.release("stt", json={"text": "Bonjour"})
    bench.release("chat", body=stream({"d": "Trop tard."}), content_type="application/x-ndjson")
    bench.release("tts", body=wav_bytes(), content_type="audio/wav")
    page.wait_for_timeout(1200)
    assert len(bench.chat_calls) == chats, "une question est partie après l'arrêt"
    assert len(bench.tts_calls) == voices, "une voix a été demandée après l'arrêt"
    assert bench.playing() == 0 and bench.recording() == 0
    assert page.evaluate("() => document.activeElement && document.activeElement.id") != "input", (
        "le clavier ne doit pas s'ouvrir quand on arrête la conversation vocale"
    )
    assert page.errors == []


@pytest.mark.parametrize("phase", ["transcribing", "thinking"])
def test_mic_button_stops_while_the_answer_is_prepared(page, base_url, phase):
    """Le micro rouge restait sans effet pendant la transcription et la réflexion."""
    bench = VoiceBench(page, base_url)
    bench.hold("stt")
    if phase == "thinking":
        bench.hold("chat")
    bench.open()
    bench.tap_mic()
    bench.wait_recording()
    bench.speak_one_turn()
    expect(page.locator("#voiceText")).to_have_text(re.compile("transcris"))
    if phase == "thinking":
        bench.release("stt", json={"text": "Bonjour"})
        expect(page.locator("#voiceText")).to_have_text(re.compile("réfléchis"))
    page.click("#mic")
    assert not page.evaluate("() => document.body.classList.contains('voice-active')")
    page.wait_for_timeout(500)
    assert bench.recording() == 0


def test_stopping_a_pending_question_says_so_instead_of_timing_out(page, base_url):
    bench = VoiceBench(page, base_url)
    bench.hold("chat")
    bench.open()
    bench.tap_mic()
    bench.wait_recording()
    bench.speak_one_turn()
    expect(page.locator("#voiceText")).to_have_text(re.compile("réfléchis"))
    page.click("#voiceStop")
    expect(page.locator("#messages")).to_contain_text("Réponse interrompue.")
    assert "Délai dépassé" not in page.inner_text("#messages")


def test_unclear_speech_is_announced_visibly(page, base_url):
    bench = VoiceBench(page, base_url)
    bench.stt_handler = lambda route, n: route.fulfill(json={"text": ""})
    bench.open()
    bench.tap_mic()
    bench.wait_recording()
    bench.speak_one_turn()
    expect(page.locator("#voiceText")).to_have_text(re.compile("pas bien entendu"))
    expect(page.locator("#voiceState")).to_have_text(re.compile("pas bien entendu"))
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=8000)


def failing_turn(bench, failure):
    """Un premier tour qui échoue (texte vide, transcription ou chat en panne), puis un tour normal."""
    state = {"failed": False}
    ok_stt, ok_chat = bench.stt_handler, bench.chat_handler

    def stt(route, n):
        if failure == "unclear" and not state["failed"]:
            state["failed"] = True
            return route.fulfill(json={"text": ""})
        if failure == "stt_error" and not state["failed"]:
            state["failed"] = True
            return route.fulfill(status=500, json={"error": "Erreur de transcription."})
        return ok_stt(route, n)

    def chat(route, n):
        if failure == "chat_error" and not state["failed"]:
            state["failed"] = True
            return route.fulfill(status=503, json={"error": "Service indisponible."})
        return ok_chat(route, n)

    bench.stt_handler, bench.chat_handler = stt, chat


@pytest.mark.parametrize("failure", ["unclear", "stt_error", "chat_error"])
def test_listening_resumes_by_itself_after_a_turn_that_failed(page, base_url, failure):
    """Avant : après un texte vide, une erreur de transcription ou du chat, le micro restait fermé."""
    bench = VoiceBench(page, base_url)
    failing_turn(bench, failure)
    bench.open()
    bench.tap_mic()
    bench.wait_recording()
    bench.speak_one_turn()
    page.wait_for_function("() => window.__mic.recording() === 0", timeout=5000)  # la parole a bien été envoyée
    bench.wait_recording(timeout=8000)  # ... et l'écoute reprend sans toucher l'écran
    expect(page.locator("#voiceText")).to_have_text(re.compile("écoute|entends|pas bien"), timeout=5000)
    bench.speak_one_turn()
    expect(page.locator("#messages")).to_contain_text("Réponse", timeout=10000)  # le tour suivant aboutit
    bench.wait_recording(timeout=10000)


def test_listening_stops_by_itself_after_three_turns_in_a_row_without_text(page, base_url):
    """Un lieu bruyant ne doit pas épuiser les transcriptions (45 par heure) en boucle."""
    bench = VoiceBench(page, base_url)
    bench.stt_handler = lambda route, n: route.fulfill(json={"text": ""})
    bench.open()
    bench.tap_mic()
    for turn in range(3):
        bench.wait_recording(timeout=10000)
        bench.speak_one_turn()
        if turn < 2:
            expect(page.locator("#voiceText")).to_have_text(re.compile("pas bien entendu"))
    expect(page.locator("#voiceText")).to_have_text(re.compile("Touche le micro pour reprendre"))
    assert len(bench.stt_calls) == 3
    assert not page.evaluate("() => document.body.classList.contains('voice-active')")
    page.wait_for_timeout(800)
    assert bench.recording() == 0
    page.click("#voiceStop")  # « Fermer » : le message disparaît
    expect(page.locator("#voiceBar")).to_be_hidden()
    page.click("#mic")  # un nouvel appui reprend la conversation
    bench.wait_recording()
    expect(page.locator("#voiceText")).to_have_text(LISTENING)
