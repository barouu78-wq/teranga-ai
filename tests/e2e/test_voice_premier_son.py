"""Le premier son se joue pendant que /tts arrive encore : la voix est lue en flux.

Avant : la page attendait le fichier WAV entier, et le serveur attendait lui-même tout le fichier chez le
fournisseur (médiane 15,3 s, p95 21,9 s, lignes « latence route=tts » du 11 au 13 octobre 2026). Ici le faux
/tts répond lentement : le test livre le son morceau par morceau (voice_harness : stream_tts, tts_chunk,
tts_end, tts_fail) et vérifie que « Je parle… » s'affiche et que le son joue AVANT la fin de la réponse /tts.

Aucune attente de durée fixe avant une livraison : chaque étape attend ce que la page a réellement fait
(wait_tts_stream, attentes visibles), pour qu'un navigateur ralenti (E2E_CPU_THROTTLE=12) ne fasse rien échouer.
"""

import re

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - la fixture « browser » (conftest) ignore ou fait échouer selon E2E_REQUIRED
    expect = None

from .voice_harness import VoiceBench

T = 15000  # attentes visibles : larges, pour un navigateur ralenti
LISTENING = re.compile("écoute")
THINKING = re.compile("réfléchis")
SPEAKING = re.compile("parle")

FIRST = "Dakar est la capitale du Sénégal, une grande ville posée sur la presqu’île du Cap-Vert."
SECOND = "Le Plateau concentre les ministères, les banques et les ambassades, tandis que la Médina garde l’âme populaire de la ville."
THIRD = "Les Almadies, au nord-ouest, sont connues pour leurs plages, leurs restaurants et le point le plus occidental du continent africain."
CLOSING = "Bonne visite à Dakar !"
SHORT = "Il est midi à Dakar."


def streamed_voice(page, base_url, path="/"):
    """Page ouverte, micro lancé, une question posée ; /chat et /tts sont des flux pilotés par le test."""
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    bench.stream_tts()
    bench.open(path)
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    bench.wait_chat_stream(timeout=T)
    return bench


def first_part_streaming(page, base_url):
    """La 1re phrase est demandée en flux et son premier morceau de son est arrivé ; /chat et /tts restent ouverts."""
    bench = streamed_voice(page, base_url)
    for chunk in (FIRST + " ", SECOND + " ", THIRD + " "):  # plus de 240 caractères : la 1re partie part tout de suite
        bench.chat_event(d=chunk)
    bench.wait_tts_stream(1, timeout=T)
    bench.tts_chunk(3000)
    expect(page.locator("#voiceText")).to_have_text(SPEAKING, timeout=T)
    return bench


def test_the_first_sentence_plays_before_tts_has_finished_answering(page, base_url):
    """Le cœur du changement : on entend la 1re phrase alors que /tts n'a pas fini de l'envoyer."""
    bench = streamed_voice(page, base_url)
    text = page.locator("#voiceText")
    for chunk in (FIRST + " ", SECOND + " ", THIRD + " "):
        bench.chat_event(d=chunk)
    bench.wait_tts_stream(1, timeout=T)
    assert bench.tts_requests() == [{"text": FIRST, "flux": True, "ended": False}]
    expect(text).to_have_text(THINKING, timeout=T)  # aucun son reçu : pas de « Je parle »
    assert bench.sound_started() == 0

    bench.tts_chunk(600)  # le premier morceau de son ; le fournisseur n'a pas fini
    expect(text).to_have_text(SPEAKING, timeout=T)
    assert bench.sound_started() >= 1, "le son doit passer par la lecture en flux"
    assert bench.tts_requests()[0]["ended"] is False, "la réponse de /tts était déjà finie : rien ne prouve l'avance"
    assert not page.evaluate("() => window.__chat.ended")
    assert page.evaluate("() => window.__mic.audios.length") == 0  # pas d'attente du fichier entier

    bench.tts_chunk(600)
    bench.tts_end(0)
    bench.chat_event(d=CLOSING)
    bench.chat_end()
    bench.wait_tts_stream(2, timeout=T)  # la suite : UN seul appel, en flux lui aussi
    rest = bench.tts_requests()[1]
    assert rest["flux"] is True and rest["text"] == f"{SECOND} {THIRD} {CLOSING}"
    bench.tts_chunk(500, call=1)
    bench.tts_end(1)
    expect(text).to_have_text(LISTENING, timeout=20000)  # l'écoute reprend à la fin de la voix
    bench.wait_recording(timeout=T)
    assert len(bench.tts_requests()) == 2, "autant d'appels /tts qu'avant : deux pour une longue réponse"
    assert bench.sound_playing() == 0
    assert page.errors == []


def test_a_short_answer_is_still_one_call_and_plays_while_it_arrives(page, base_url):
    bench = streamed_voice(page, base_url)
    bench.chat_event(d=SHORT)
    bench.chat_end()
    bench.wait_tts_stream(1, timeout=T)
    bench.tts_chunk(400)
    expect(page.locator("#voiceText")).to_have_text(SPEAKING, timeout=T)
    bench.tts_end()
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=T)
    bench.wait_recording(timeout=T)
    page.wait_for_timeout(500)  # une seconde lecture éventuelle aurait déjà commencé
    assert bench.tts_requests() == [{"text": SHORT, "flux": True, "ended": True}]
    assert page.errors == []


def test_stop_cuts_a_streamed_voice_and_its_call(page, base_url):
    bench = first_part_streaming(page, base_url)
    assert bench.sound_playing() >= 1
    page.click("#voiceStop")
    bench.wait_tts_aborted(1, timeout=T)  # le flux /tts en cours est annulé, pas seulement ignoré
    page.wait_for_function("() => window.__mic.soundPlaying() === 0", timeout=T)  # plus aucun son
    expect(page.locator("#voiceBar")).to_be_hidden(timeout=T)
    calls = len(bench.tts_requests())
    # Le son et la réponse qui arrivent après l'arrêt n'ont plus d'effet : ni lecture, ni nouvel appel, ni écoute.
    assert bench.tts_chunk(2000, call=0) is False
    bench.chat_event(d=CLOSING)
    bench.chat_end()
    page.wait_for_timeout(1200)
    assert len(bench.tts_requests()) == calls
    assert bench.sound_playing() == 0 and bench.recording() == 0
    assert page.errors == []


def test_mic_tap_cuts_a_streamed_voice_and_listening_resumes(page, base_url):
    bench = first_part_streaming(page, base_url)
    assert page.get_attribute("#mic", "aria-label") == "Couper la voix et parler"
    page.click("#mic")  # couper la voix pour parler
    bench.wait_tts_aborted(1, timeout=T)
    page.wait_for_function("() => window.__mic.soundPlaying() === 0", timeout=T)
    bench.chat_event(d=CLOSING)  # la réponse finit d'arriver à l'écran, sans être lue
    bench.chat_end()
    bench.wait_recording(timeout=T)
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=T)
    page.wait_for_timeout(800)
    assert len(bench.tts_requests()) == 1, "la fin de la réponse a été lue après la coupure"
    assert page.errors == []


def test_a_stream_cut_in_the_middle_is_said_and_listening_resumes(page, base_url):
    bench = streamed_voice(page, base_url)
    text = page.locator("#voiceText")
    bench.chat_event(d=SHORT)
    bench.chat_end()
    bench.wait_tts_stream(1, timeout=T)
    bench.tts_chunk(400)
    expect(text).to_have_text(SPEAKING, timeout=T)
    bench.tts_fail()  # le réseau coupe : ce qui est arrivé est lu, puis la coupure est dite
    expect(text).to_have_text(re.compile("pas pu lire"), timeout=T)
    expect(text).to_have_text(LISTENING, timeout=20000)
    bench.wait_recording(timeout=T)
    assert page.evaluate("() => document.body.classList.contains('voice-active')"), "la conversation s'est arrêtée"
    assert page.errors == []


def test_without_a_running_audio_context_the_voice_waits_for_the_whole_sound_as_before(page, base_url):
    """iPhone sans geste récent : le contexte audio reste suspendu. Rien ne se perd : la voix se lit à la fin du flux,
    d'un seul fichier, comme avant (aucun gain dans ce cas, aucune régression)."""
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    bench.stream_tts()
    bench.open()
    page.evaluate(
        "() => { voiceOutputContext = new AudioContext(); voiceOutputContext.resume = () => Promise.resolve();"
        " return voiceOutputContext.suspend(); }"
    )
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    text = page.locator("#voiceText")
    bench.chat_event(d=SHORT)
    bench.chat_end()
    bench.wait_tts_stream(1, timeout=T)
    bench.tts_chunk(1500)
    expect(text).to_have_text(THINKING, timeout=T)
    page.wait_for_timeout(800)  # bien plus que l'attente du contexte : s'il devait jouer en flux, ce serait fait
    assert bench.sound_started() == 0 and page.evaluate("() => window.__mic.audios.length") == 0
    bench.tts_end()
    expect(text).to_have_text(SPEAKING, timeout=T)  # le fichier entier, par l'élément <audio> d'avant
    assert page.evaluate("() => window.__mic.audios.length") == 1
    expect(text).to_have_text(LISTENING, timeout=20000)
    bench.wait_recording(timeout=T)
    assert page.errors == []
