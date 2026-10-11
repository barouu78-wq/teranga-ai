"""La voix démarre à la première phrase complète de la réponse, pendant que le reste arrive.

Le flux de /chat est livré en deux temps par le test (voice_harness : stream_chat, chat_event, chat_end) :
la première phrase arrive, le test observe /tts, puis seulement ensuite il livre la suite. Chaque attente
passe par wait_held / wait_tts_calls / une attente visible (jamais une pause de durée fixe avant un
release) : un navigateur ralenti (E2E_CPU_THROTTLE=12) ne doit faire échouer aucun test.

Les trois premiers tests de contrôle (constantes, mentions de coupure) ne lancent pas de navigateur.
"""

import re
from pathlib import Path

import pytest

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - la fixture « browser » (conftest) ignore ou fait échouer selon E2E_REQUIRED
    expect = None

from services.truncation import CUT_NOTICES

from .voice_harness import VoiceBench, stream, wav_bytes

ROOT = Path(__file__).resolve().parents[2]
HOME_TEMPLATE = ROOT / "templates" / "home.html"
T = 15000  # attentes visibles : larges, pour un navigateur ralenti
LISTENING = re.compile("écoute")
THINKING = re.compile("réfléchis")
SPEAKING = re.compile("parle")

FIRST = "Dakar est la capitale du Sénégal, une grande ville posée sur la presqu’île du Cap-Vert."
SECOND = "Le Plateau concentre les ministères, les banques et les ambassades, tandis que la Médina garde l’âme populaire de la ville."
THIRD = "Les Almadies, au nord-ouest, sont connues pour leurs plages, leurs restaurants et le point le plus occidental du continent africain."
CLOSING = "Bonne visite à Dakar !"
FIRST_2 = "Saint-Louis, ancienne capitale de l’Afrique-Occidentale française, est inscrite au patrimoine mondial de l’UNESCO."
SECOND_2 = "Le pont Faidherbe relie l’île au continent depuis la fin du dix-neuvième siècle."

# (livré avant la pause du flux, livré après). « court » : moins de 240 caractères reçus à la pause (la
# réponse semble courte : la 1re partie part après un court délai) ; « long » : plus de 240 (elle part tout de suite).
STREAMS = {
    "court": ([FIRST + " ", SECOND[:12]], [SECOND[12:] + " ", THIRD]),
    "long": ([FIRST + " ", SECOND + " ", THIRD + " "], [CLOSING]),
}


def said(*parts):
    """Le texte tel que la page l'envoie à la voix : espaces normalisés, sans blanc autour."""
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def rest_of(shape):
    before, after = STREAMS[shape]
    return said(*before[1:], *after)


def deliver(bench, chunks):
    for chunk in chunks:
        bench.chat_event(d=chunk)


def voice_turn(bench, calls=1):
    """Un tour de parole : le micro écoute, la personne parle, la page ouvre le flux de /chat."""
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    bench.wait_chat_stream(calls=calls, timeout=T)


def streamed_turn(page, base_url, path="/", hold_tts=True):
    """Page ouverte, micro lancé, une question posée ; /chat est un flux piloté, /tts est retenu."""
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    if hold_tts:
        bench.hold("tts")
    bench.open(path)
    bench.tap_mic()
    voice_turn(bench)
    return bench


# ── Garde-fous sans navigateur ──────────────────────────────────────────────────────────────────────


def test_spoken_cut_notices_are_the_ones_of_the_server():
    """La page retire de la voix les mentions du serveur : si on change leur texte, il faut changer la page."""
    source = HOME_TEMPLATE.read_text(encoding="utf-8")
    declared = re.search(r"const VOICE_CUT_NOTICES=\[(.*?)\];", source, re.S)
    assert declared, "VOICE_CUT_NOTICES introuvable dans le gabarit de l'accueil"
    for notice in CUT_NOTICES.values():
        assert f"'{notice}'" in declared.group(1), f"la page ne retire pas la mention « {notice} » de la voix"


def test_page_budget_follows_the_server_limit_of_tts():
    """Le budget horaire de /tts de la page doit rester égal à la limite du serveur (app.py)."""
    from app import TTS_HOURLY_LIMIT

    source = HOME_TEMPLATE.read_text(encoding="utf-8")
    declared = re.search(r"const VOICE_TTS_HOURLY_LIMIT=(\d+);", source)
    assert declared and int(declared.group(1)) == TTS_HOURLY_LIMIT, (
        "VOICE_TTS_HOURLY_LIMIT (accueil) et TTS_HOURLY_LIMIT (app.py) doivent rester égales : "
        "revoir le budget de découpage si la limite change"
    )


def test_service_worker_version_changed_with_the_voice_files():
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    match = re.search(r"const VERSION = 'teranga-v(\d+)';", sw)
    assert match and int(match.group(1)) >= 11


# ── Découpage en phrases ────────────────────────────────────────────────────────────────────────────

# (texte reçu, première phrase sûre ou None). « Ensuite » à la fin confirme la dernière fin de phrase.
BOUNDARY_CASES = [
    ("Il fait 3.5 degrés ce matin à Saint-Louis. Ensuite", "Il fait 3.5 degrés ce matin à Saint-Louis."),
    ("Le prix est de 3,5 millions de francs CFA par mois. Ensuite", "Le prix est de 3,5 millions de francs CFA par mois."),
    ("Les prix sont de 2.500 francs. Ensuite", "Les prix sont de 2.500 francs."),
    ("Version 2.0 disponible. Ensuite", "Version 2.0 disponible."),
    ("Va voir le Dr. Diop à la clinique de la Médina. Ensuite", "Va voir le Dr. Diop à la clinique de la Médina."),
    ("M. Fall et Mme Sy vendent des mangues. Ensuite", "M. Fall et Mme Sy vendent des mangues."),
    ("Voir St. Louis et Gorée. Ensuite", "Voir St. Louis et Gorée."),
    ("Il y a des mangues, des bananes, etc. Ensuite on part. Puis", "Il y a des mangues, des bananes, etc. Ensuite on part."),
    ("Voir www.teranga-ai.fr/lieux pour la liste. Ensuite", "Voir www.teranga-ai.fr/lieux pour la liste."),
    ("Je pense que... bon, on verra. Ensuite", "Je pense que... bon, on verra."),
    ("Il hésite… Mais il part. Ensuite", "Il hésite… Mais il part."),
    ("A. Diop et B. Ndiaye sont partis. Ensuite", "A. Diop et B. Ndiaye sont partis."),
    ("Il a dit « Bonjour. » puis il est parti. Ensuite", "Il a dit « Bonjour. » puis il est parti."),
    ("1. Visiter Gorée en ferry\n2. Voir le marché\nEnsuite", "1. Visiter Gorée en ferry"),
    ("Le tarif est affiché. Ensuite", "Le tarif est affiché."),
    ("Vraiment ? Oui ! Ensuite", "Vraiment ?"),
    ("Prix : 27. Ensuite", "Prix : 27."),
    # Pas de fin sûre : rien n'est dit tant que la phrase n'est pas finie et suivie d'autre chose.
    ("Pas de fin de phrase ici", None),
    ("Phrase terminée. ", None),
    ("Phrase terminée.", None),
    ("Mot. suite avec minuscule", None),
]


def test_sentence_ends_ignore_abbreviations_numbers_urls_and_ellipses(page, base_url):
    VoiceBench(page, base_url).open()
    got = page.evaluate(
        """cases => cases.map(([text]) => {
            const ends = voiceSentenceEnds(text);
            return ends.length ? text.slice(0, ends[0]).trim() : null;
        })""",
        BOUNDARY_CASES,
    )
    wrong = [(text, want, have) for (text, want), have in zip(BOUNDARY_CASES, got) if have != want]
    assert wrong == []


def test_a_very_long_rest_is_cut_between_sentences_and_a_normal_one_is_not(page, base_url):
    VoiceBench(page, base_url).open()
    long_text = " ".join(f"Phrase numéro {n} de la réponse, assez longue pour compter dans le découpage final." for n in range(60))
    chunks = page.evaluate("text => voiceSpeechChunks(text)", long_text)
    assert len(chunks) >= 2 and all(len(chunk) <= 1400 for chunk in chunks)
    assert all(chunk.rstrip().endswith(".") for chunk in chunks), "un morceau coupé au milieu d'une phrase"
    assert said(*chunks) == said(long_text), "du texte perdu ou répété entre les morceaux"
    assert page.evaluate("text => voiceSpeechChunks(text).length", said(*[SECOND, THIRD] * 4)) == 1


# ── La première phrase part avant la fin ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("shape", ["court", "long"])
def test_first_sentence_goes_to_tts_before_the_end_of_the_answer(page, base_url, shape):
    """Avant : jusqu'à quatre appels (une phrase chacun), et seule la 1re réponse de la conversation partait en flux."""
    before, after = STREAMS[shape]
    bench = streamed_turn(page, base_url)
    text = page.locator("#voiceText")
    deliver(bench, before)

    bench.wait_held("tts", timeout=T)  # la 1re phrase est demandée alors que le flux est encore ouvert
    assert bench.tts_texts() == [FIRST]
    assert not page.evaluate("() => window.__chat.ended"), "le flux était déjà fini : rien ne prouve l'avance"
    assert bench.playing() == 0
    expect(text).to_have_text(THINKING, timeout=T)  # pas de « Je parle » avant le son

    bench.release("tts", body=wav_bytes(4000), content_type="audio/wav")
    expect(text).to_have_text(SPEAKING, timeout=T)  # la voix parle, la suite n'est pas encore arrivée
    assert not page.evaluate("() => window.__chat.ended")

    deliver(bench, after)
    bench.chat_end()
    bench.wait_tts_calls(2, timeout=T)  # la suite : UN seul appel, demandé pendant que la 1re partie se lit
    bench.wait_held("tts", timeout=T)
    assert bench.tts_texts() == [FIRST, rest_of(shape)]
    bench.release("tts", body=wav_bytes(800), content_type="audio/wav")

    expect(text).to_have_text(LISTENING, timeout=20000)  # l'écoute reprend à la fin de la 2e partie
    bench.wait_recording(timeout=T)
    assert len(bench.tts_calls) == 2
    assert page.evaluate("() => window.__mic.audios.length") == 2
    assert page.errors == []


@pytest.mark.parametrize(
    "reply",
    ["Il est midi à Dakar.", "Il est midi à Dakar.\n", "Il est midi à Dakar. Il fait chaud."],
    ids=["une phrase", "une phrase et retour à la ligne", "deux phrases courtes"],
)
def test_a_short_answer_is_one_call_and_is_read_once(page, base_url, reply):
    """Avant : « Il est midi. » était lu deux fois (la 2e depuis le cache, donc sans 2e appel visible)."""
    bench = streamed_turn(page, base_url, hold_tts=False)
    bench.chat_event(d=reply)
    bench.chat_end()
    page.wait_for_function("() => window.__mic.audios.length >= 1", timeout=T)
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=T)  # la lecture est finie
    bench.wait_recording(timeout=T)
    page.wait_for_timeout(500)  # une seconde lecture éventuelle aurait déjà commencé
    assert bench.tts_texts() == [said(reply)]
    assert page.evaluate("() => window.__mic.audios.length") == 1, "la réponse a été lue plus d'une fois"
    assert page.errors == []


def test_the_second_answer_of_a_conversation_also_starts_before_its_end(page, base_url):
    """Avant : le compteur de phrases lues n'était jamais remis à zéro. Après trois phrases lues pendant le flux
    (la 1re réponse), plus aucune réponse de la conversation ne partait avant d'être complète."""
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    bench.open()
    bench.tap_mic()
    text = page.locator("#voiceText")
    voice_turn(bench, calls=1)
    before, after = STREAMS["long"]  # trois phrases terminées : le compteur d'avant atteignait sa limite
    deliver(bench, before + after)
    bench.chat_end()
    expect(text).to_have_text(LISTENING, timeout=20000)

    already = len(bench.tts_calls)
    voice_turn(bench, calls=2)
    deliver(bench, [FIRST_2 + " ", SECOND_2[:12]])
    bench.wait_tts_calls(already + 1, timeout=T)  # la 1re phrase de la 2e réponse, flux encore ouvert
    assert bench.tts_texts()[-1] == FIRST_2
    assert not page.evaluate("() => window.__chat.ended")
    deliver(bench, [SECOND_2[12:]])
    bench.chat_end()
    bench.wait_tts_calls(already + 2, timeout=T)
    assert bench.tts_texts()[-1] == said(SECOND_2)
    expect(text).to_have_text(LISTENING, timeout=20000)
    assert len(bench.tts_calls) == already + 2
    assert page.errors == []


def test_abbreviations_numbers_and_urls_do_not_cut_the_first_sentence(page, base_url):
    """Avant : « le Dr. » partait seul vers la voix, puis le reste de la phrase."""
    sentence = (
        "Pour tes soins à Dakar, prends rendez-vous avec le Dr. Diop de la Médina (consultation vers 3,5 euros, etc.), "
        "puis lis www.teranga-ai.fr/sante... Bon courage."
    )
    bench = streamed_turn(page, base_url)
    deliver(bench, [sentence + " ", "Ensuite"])
    bench.wait_held("tts", timeout=T)
    assert bench.tts_texts() == [sentence]


# ── « Arrêter » et le micro coupent tout, la deuxième partie comprise ─────────────────────────────────


@pytest.mark.parametrize("phase", ["first_part_preparing", "first_part_playing", "rest_in_flight"])
def test_stop_cuts_the_voice_the_calls_in_flight_and_the_rest(page, base_url, phase):
    """Avant : l'appel /tts en vol n'était jamais annulé, et la 2e partie n'était demandée qu'après la 1re."""
    before, after = STREAMS["court"]
    bench = streamed_turn(page, base_url)
    text = page.locator("#voiceText")
    deliver(bench, before)
    bench.wait_held("tts", timeout=T)
    if phase != "first_part_preparing":
        bench.release("tts", body=wav_bytes(8000), content_type="audio/wav")
        bench.wait_playing(timeout=T)
        expect(text).to_have_text(SPEAKING, timeout=T)
    if phase == "rest_in_flight":
        deliver(bench, after)
        bench.chat_end()
        bench.wait_tts_calls(2, timeout=T)
        bench.wait_held("tts", timeout=T)  # la suite est partie vers /tts, sa réponse est attendue
    calls = len(bench.tts_calls)
    in_flight = 0 if phase == "first_part_playing" else 1

    page.click("#voiceStop")

    if in_flight:
        bench.wait_tts_aborted(in_flight, timeout=T)  # l'appel en vol est annulé, pas seulement ignoré
    if phase != "rest_in_flight":
        page.wait_for_function("() => window.__chat.aborted", timeout=T)  # la réponse en cours aussi
    expect(page.locator("#voiceBar")).to_be_hidden(timeout=T)
    page.wait_for_function("() => window.__mic.playing() === 0", timeout=T)
    # La réponse du serveur arrive après l'arrêt, et la suite du flux aussi : rien ne repart.
    bench.release("tts", body=wav_bytes(), content_type="audio/wav")
    deliver(bench, after)
    bench.chat_end()
    page.wait_for_timeout(1200)
    assert len(bench.tts_calls) == calls, "une voix a été demandée après l'arrêt"
    assert bench.playing() == 0 and bench.recording() == 0
    assert page.errors == []


def test_mic_tap_during_the_first_part_cuts_the_rest_and_listening_resumes_after_the_answer(page, base_url):
    """Avant : après une coupure, la fin de la réponse se lisait quand même, à partir du milieu."""
    before, after = STREAMS["court"]
    bench = streamed_turn(page, base_url)
    text = page.locator("#voiceText")
    deliver(bench, before)
    bench.wait_held("tts", timeout=T)
    bench.release("tts", body=wav_bytes(8000), content_type="audio/wav")
    bench.wait_playing(timeout=T)
    expect(text).to_have_text(SPEAKING, timeout=T)
    assert page.get_attribute("#mic", "aria-label") == "Couper la voix et parler"

    page.click("#mic")  # couper la voix pour parler
    page.wait_for_function("() => window.__mic.playing() === 0", timeout=T)
    deliver(bench, after)  # la réponse continue d'arriver à l'écran
    bench.chat_end()
    page.wait_for_timeout(1200)
    assert len(bench.tts_calls) == 1, "la fin de la réponse a été lue après la coupure"
    bench.wait_recording(timeout=T)  # ... et l'écoute reprend quand la réponse est finie
    expect(text).to_have_text(LISTENING, timeout=T)
    assert page.errors == []


# ── Les états de la barre sur les deux parties ───────────────────────────────────────────────────────


def test_states_over_the_two_parts_and_listening_only_after_the_second(page, base_url):
    before, after = STREAMS["court"]
    bench = streamed_turn(page, base_url)
    text = page.locator("#voiceText")
    deliver(bench, before)
    bench.wait_held("tts", timeout=T)
    expect(text).to_have_text(THINKING, timeout=T)  # la voix se prépare : pas de « Je parle » sans son
    assert bench.playing() == 0 and page.evaluate("() => window.__mic.audios.length") == 0

    bench.release("tts", body=wav_bytes(1500), content_type="audio/wav")
    expect(text).to_have_text(SPEAKING, timeout=T)
    assert bench.recording() == 0
    # 1re partie finie, la suite n'est pas arrivée : on réfléchit encore, le micro reste fermé.
    page.wait_for_function("() => window.__mic.audios.length === 1 && window.__mic.playing() === 0", timeout=T)
    expect(text).to_have_text(THINKING, timeout=T)
    assert bench.recording() == 0

    deliver(bench, after)
    bench.chat_end()
    bench.wait_held("tts", timeout=T)  # la 2e partie se prépare
    expect(text).to_have_text(THINKING, timeout=T)
    assert bench.recording() == 0
    bench.release("tts", body=wav_bytes(2500), content_type="audio/wav")
    expect(text).to_have_text(SPEAKING, timeout=T)
    assert bench.recording() == 0, "le micro s'est ouvert pendant la voix"
    expect(text).to_have_text(LISTENING, timeout=20000)
    bench.wait_recording(timeout=T)
    assert len(bench.tts_calls) == 2 and page.errors == []


# ── Si la voix échoue : la suite est tentée, et l'erreur est dite ───────────────────────────────────


def failing(route):
    route.fulfill(status=502, json={"error": "Impossible de générer la voix pour le moment."})


def spoken(route):
    route.fulfill(body=wav_bytes(3000), content_type="audio/wav")


def limited(route):
    route.fulfill(status=429, headers={"Retry-After": "3"}, json={"error": "Trop de demandes vocales."})


def plan_tts(bench, *actions):
    """Un comportement par appel /tts, dans l'ordre (le dernier vaut pour les suivants)."""
    bench.tts_handler = lambda route, n: actions[min(n, len(actions)) - 1](route)


def test_a_failed_first_part_still_tries_the_rest_and_says_so(page, base_url):
    """Avant : une voix qui échoue en conversation ne disait rien (retour muet à l'écoute)."""
    before, after = STREAMS["court"]
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    plan_tts(bench, failing, spoken)
    bench.open()
    bench.tap_mic()
    voice_turn(bench)
    text = page.locator("#voiceText")
    deliver(bench, before)
    expect(text).to_have_text(re.compile("pas pu lire"), timeout=T)  # dit tout de suite, sans attendre la fin du flux
    deliver(bench, after)
    bench.chat_end()
    bench.wait_tts_calls(2, timeout=T)  # la suite est tentée malgré l'échec
    assert bench.tts_texts() == [FIRST, rest_of("court")]
    expect(text).to_have_text(SPEAKING, timeout=T)
    expect(text).to_have_text(LISTENING, timeout=20000)
    assert page.errors == []


@pytest.mark.parametrize(
    "path, failure, listening",
    [("/", "pas pu lire", "écoute"), ("/?lang=en", "couldn’t read", "listening")],
    ids=["fr", "en"],
)
def test_when_every_part_fails_the_error_is_shown_and_listening_resumes(page, base_url, path, failure, listening):
    before, after = STREAMS["court"]
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    plan_tts(bench, failing)
    bench.open(path)
    bench.tap_mic()
    voice_turn(bench)
    deliver(bench, before + after)
    bench.chat_end()
    text = page.locator("#voiceText")
    bench.wait_tts_calls(2, timeout=T)
    expect(text).to_have_text(re.compile(failure), timeout=T)
    expect(text).to_have_text(re.compile(listening), timeout=20000)  # le message passe, l'écoute reprend
    bench.wait_recording(timeout=T)
    assert page.evaluate("() => document.body.classList.contains('voice-active')"), "la conversation s'est arrêtée"
    assert page.errors == []


def test_a_rate_limited_voice_says_when_to_retry_and_stops_asking(page, base_url):
    before, after = STREAMS["court"]
    bench = VoiceBench(page, base_url)
    bench.stream_chat()
    plan_tts(bench, limited, spoken)
    bench.open()
    bench.tap_mic()
    voice_turn(bench)
    text = page.locator("#voiceText")
    deliver(bench, before)
    expect(text).to_have_text(re.compile(r"Trop de demandes vocales\. Réessaie dans \d+ s"), timeout=T)
    deliver(bench, after)
    bench.chat_end()
    expect(text).to_have_text(LISTENING, timeout=20000)
    bench.wait_recording(timeout=T)
    # Après un 429 la suite n'est pas redemandée : chaque essai compte contre le visiteur.
    assert len(bench.tts_calls) == 1
    assert page.errors == []


def test_audio_that_cannot_be_played_is_reported(page, base_url):
    """Un fichier de voix illisible (ou une lecture refusée par le navigateur) ne doit pas rester muet et sans explication."""
    bench = VoiceBench(page, base_url)
    bench.tts_handler = lambda route, n: route.fulfill(body=b"ceci n'est pas du son", content_type="audio/wav")
    bench.open()
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    text = page.locator("#voiceText")
    expect(text).to_have_text(re.compile("pas pu lire"), timeout=T)
    expect(text).to_have_text(LISTENING, timeout=20000)
    bench.wait_recording(timeout=T)
    assert page.errors == []


def test_a_typed_question_is_still_read_once_in_one_call(page, base_url):
    """Garde-fou (déjà vert avant) : hors conversation vocale, la réponse écrite se lit d'un seul appel, une seule fois."""
    bench = VoiceBench(page, base_url).open()
    page.fill("#input", "Bonjour")
    page.click("#send")
    bench.wait_tts_calls(1, timeout=T)
    page.wait_for_function("() => window.__mic.audios.length >= 1", timeout=T)
    page.wait_for_function("() => window.__mic.playing() === 0", timeout=T)
    page.wait_for_timeout(500)
    assert bench.tts_texts() == ["Réponse 1."]
    assert page.evaluate("() => window.__mic.audios.length") == 1
    expect(page.locator("#voiceBar")).to_be_hidden()


# ── Limites de débit : le budget de découpage ────────────────────────────────────────────────────────


@pytest.mark.parametrize("used, splits", [(28, True), (29, False)], ids=["28 appels : on découpe", "29 appels : un seul appel"])
def test_the_answer_is_split_only_while_the_hourly_budget_allows_it(page, base_url, used, splits):
    """/tts : 45 par heure et par visiteur. On ne découpe (2 appels) que jusqu'à 30 appels dans l'heure."""
    before, after = STREAMS["long"]
    bench = streamed_turn(page, base_url)
    page.evaluate("n => { voiceTtsLog = Array.from({length: n}, () => Date.now()); }", used)
    deliver(bench, before)
    if splits:
        bench.wait_held("tts", timeout=T)
        assert bench.tts_texts() == [FIRST]
    else:
        page.wait_for_timeout(1500)  # bien plus que le délai de grâce : si la page découpait, l'appel serait parti
        assert bench.tts_calls == [], "une réponse a été découpée alors que le budget de l'heure est presque épuisé"
    deliver(bench, after)
    bench.chat_end()
    if splits:
        bench.wait_tts_calls(2, timeout=T)
        assert bench.tts_texts() == [FIRST, rest_of("long")]
    else:
        bench.wait_held("tts", timeout=T)
        assert bench.tts_texts() == [said(*STREAMS["long"][0], *after)]
    page.wait_for_timeout(500)
    assert len(bench.tts_calls) == (2 if splits else 1)


# ── La mention « Réponse coupée » n'est jamais lue ──────────────────────────────────────────────────


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_the_cut_notice_is_never_sent_to_tts_in_voice_mode(page, base_url, lang):
    """Avant : la mention ajoutée par le serveur à la fin d'une réponse tronquée était lue à voix haute."""
    notice = CUT_NOTICES[lang]
    before, after = STREAMS["court"]
    bench = streamed_turn(page, base_url, path="/" if lang == "fr" else "/?lang=en")
    deliver(bench, before)
    bench.wait_held("tts", timeout=T)
    bench.release("tts", body=wav_bytes(3000), content_type="audio/wav")
    deliver(bench, after)
    bench.chat_event(d="\n\n" + notice)  # le serveur la livre dans un dernier événement
    bench.chat_end()
    bench.wait_tts_calls(2, timeout=T)
    bench.wait_held("tts", timeout=T)
    assert bench.tts_texts() == [FIRST, rest_of("court")]
    assert all("continue" not in sent and notice not in sent for sent in bench.tts_texts())
    expect(page.locator("#messages")).to_contain_text(notice, timeout=T)  # elle reste lisible à l'écran


def test_the_cut_notice_alone_after_the_first_part_is_not_spoken(page, base_url):
    """Réponse d'une phrase tronquée, livrée d'un bloc (réponse en cache ou de secours) : une seule lecture."""
    notice = CUT_NOTICES["fr"]
    bench = VoiceBench(page, base_url)
    bench.chat_handler = lambda route, n: route.fulfill(
        body=stream({"d": FIRST + "\n\n" + notice}), content_type="application/x-ndjson"
    )
    bench.open()
    bench.tap_mic()
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    bench.wait_tts_calls(1, timeout=T)
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=20000)
    page.wait_for_timeout(500)
    assert bench.tts_texts() == [FIRST]
    assert page.evaluate("() => window.__mic.audios.length") == 1


def test_the_listen_button_does_not_read_the_cut_notice(page, base_url):
    notice = CUT_NOTICES["fr"]
    page.add_init_script("localStorage.setItem('teranga-voice', '0')")  # pas de lecture automatique : on teste le bouton
    bench = VoiceBench(page, base_url)
    bench.chat_handler = lambda route, n: route.fulfill(
        body=stream({"d": FIRST + "\n\n" + notice}), content_type="application/x-ndjson"
    )
    bench.open()
    page.fill("#input", "Parle-moi de Dakar")
    page.click("#send")
    expect(page.locator("#messages")).to_contain_text(notice, timeout=T)
    page.locator(".acts button", has_text="Écouter").click()
    bench.wait_tts_calls(1, timeout=T)
    assert bench.tts_texts() == [FIRST]
