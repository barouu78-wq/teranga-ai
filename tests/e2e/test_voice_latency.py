"""Banc de latence SIMULÉ de la voix : de « la personne a fini de parler » au « premier son de la réponse ».

Ce banc ne mesure AUCUN vrai fournisseur ni vrai téléphone. /stt, /chat et /tts sont de faux serveurs auxquels le
harnais (voice_harness.delays) ajoute un retard fixe : tout ce qui dépasse ces retards vient donc du site lui-même
(attente du silence, travail de la page, attente voulue avant la première partie). Les chiffres sont « simulés ».

Les seuils ci-dessous sont des garde-fous de NON-RÉGRESSION de ce banc, pas des objectifs de latence réelle (l'objectif
se fixe sur de vraies lignes de la production, voir docs/MESURE-LATENCE.md). Ils sont larges exprès : le test doit
passer aussi sur une machine chargée et avec le navigateur ralenti (E2E_CPU_THROTTLE=12), et n'échouer que si une
régression dépasse nettement ce qui est constaté.

Le détail de chaque tour s'affiche avec ``pytest -s``.
"""

import re
import statistics

import pytest

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - la fixture « browser » (conftest) ignore ou fait échouer selon E2E_REQUIRED
    expect = None

from .voice_harness import VoiceBench, wav_bytes

T = 20000  # attentes visibles : larges, pour un navigateur ralenti
LISTENING = re.compile("écoute")
TURNS = 3  # tours par scénario : on juge la médiane, une machine qui hoquette une fois ne fait rien échouer

# Retards des faux fournisseurs (ms). Ils sont retranchés du total : il reste ce qui revient au site.
STT_MS, CHAT_MS, TTS_MS = 350, 450, 400

FIRST = "Dakar est la capitale du Sénégal, une grande ville posée sur la presqu’île du Cap-Vert."
SECOND = "Le Plateau concentre les ministères, les banques et les ambassades, tandis que la Médina garde l’âme populaire de la ville."
THIRD = "Les Almadies, au nord-ouest, sont connues pour leurs plages, leurs restaurants et le point le plus occidental du continent."
SHORT_REPLY = "Il est midi à Dakar."

# Garde-fous (ms), par morceau de la chaîne. « Constaté » = médianes du banc à la création de ce test, sur la machine
# de développement : d'abord navigateur normal, puis ralenti 12 fois (E2E_CPU_THROTTLE=12). Ce sont des chiffres
# SIMULÉS. Chaque seuil laisse une grande marge au-dessus : seule une régression nette fait échouer le test.
BUDGETS = {
    # fin de parole -> envoi vers /stt : VOICE_SILENCE_MS = 720, pas de 55 ms, arrêt de l'enregistreur. Constaté : ~800 ; ~825-860
    "silence": 1150,
    # réponse de /stt -> envoi vers /chat (travail de la page). Constaté : ~2 ; ~40-50
    "stt_to_chat": 450,
    # réponse de /chat -> envoi vers /tts
    "wait": {
        "bloc": 450,  # réponse reçue d'un bloc. Constaté : ~2 ; ~40
        "court": 1100,  # 1re phrase d'une réponse qui semble courte : attente voulue VOICE_FIRST_WAIT_MS = 700. Constaté : ~710 ; ~765
        "long": 450,  # 1re phrase d'une réponse assez longue : part tout de suite. Constaté : ~10 ; ~165 (le test livre le texte par morceaux)
    },
    # réponse de /tts -> son qui démarre. Constaté : ~5 ; ~115
    "sound_start": 700,
}
# Au total, ce qui revient au site (hors retards des faux fournisseurs) ne doit pas dépasser (constaté, normal ; ralenti) :
# bloc ~820 ; ~1040 · court ~1530 ; ~1780 · long ~840 ; ~1200
OWN_TOTAL = {"bloc": 2000, "court": 2900, "long": 2000}


def deliver_first_events(bench, shape, n):
    # Une réponse différente à chaque tour : une réponse déjà lue vient du cache de la page, sans appel à /tts.
    first_sentence = FIRST[:-1] + f", question {n}."
    first = {
        "court": [first_sentence + " ", SECOND[:12]],  # moins de 240 caractères reçus : la page attend un instant
        "long": [first_sentence + " ", SECOND + " ", THIRD + " "],  # plus de 240 caractères : la page n'attend pas
    }[shape]
    bench.page.wait_for_timeout(CHAT_MS)  # le « premier jeton » du faux modèle
    for chunk in first:
        bench.chat_event(d=chunk)


def one_turn(bench, shape, n):
    """Un tour de parole complet, jusqu'au retour de l'écoute (pour que le tour suivant parte d'un état propre)."""
    page = bench.page
    per_turn = 1 if shape == "bloc" else 2  # un son par morceau de voix : réponse d'un bloc = 1, première partie + suite = 2
    bench.wait_recording(timeout=T)
    bench.speak_one_turn()
    if shape == "bloc":
        bench.wait_sounds((n - 1) * per_turn + 1, timeout=T)
    else:
        bench.wait_chat_stream(calls=n, timeout=T)
        deliver_first_events(bench, shape, n)
        bench.wait_sounds((n - 1) * per_turn + 1, timeout=T)  # la 1re partie parle, le flux n'est pas fini
        bench.chat_event(d=" Bonne visite.")
        bench.chat_end()
    expect(page.locator("#voiceText")).to_have_text(LISTENING, timeout=T)
    bench.wait_sounds(n * per_turn, timeout=T)


def segments(line, shape):
    """Les morceaux de la chaîne pour un tour, en ms. Les trois premiers « fournisseurs » sont simulés."""
    chat_ready = line["chat-head"] if shape == "bloc" else line["chat-first-event"]
    return {
        "silence": line["stt-sent"],
        "stt_sim": line["stt-head"] - line["stt-sent"],
        "stt_to_chat": line["chat-sent"] - line["stt-head"],
        "chat_sim": chat_ready - line["chat-sent"],
        "wait": line["tts-sent"] - chat_ready,
        "tts_sim": line["tts-head"] - line["tts-sent"],
        "sound_start": line["sound"] - line["tts-head"],
        "total": line["sound"],
    }


def show(shape, rows):
    keys = ["silence", "stt_sim", "stt_to_chat", "chat_sim", "wait", "tts_sim", "sound_start", "total"]
    print(f"\n[banc SIMULÉ] {shape} : {TURNS} tours (ms depuis la fin de parole)")
    print("  " + "".join(f"{k:>13}" for k in keys))
    for row in rows:
        print("  " + "".join(f"{row[k]:>13.0f}" for k in keys))
    print("  " + "".join(f"{statistics.median(r[k] for r in rows):>13.0f}" for k in keys) + "   <- médiane")


@pytest.mark.parametrize("shape", ["bloc", "court", "long"])
def test_first_sound_stays_within_the_simulated_budget(page, base_url, shape):
    """Fin de parole -> premier son, avec des fournisseurs simulés de retard fixe : aucun morceau du site ne dérive."""
    bench = VoiceBench(page, base_url)
    bench.delays(stt=STT_MS, chat=CHAT_MS if shape == "bloc" else 0, tts=TTS_MS)
    bench.chat_handler = lambda route, n: route.fulfill(
        body='{"d": "%s"}\n' % f"Réponse {n} : {SHORT_REPLY[0].lower()}{SHORT_REPLY[1:]}", content_type="application/x-ndjson"
    )
    bench.tts_handler = lambda route, n: route.fulfill(body=wav_bytes(700), content_type="audio/wav")
    if shape != "bloc":
        bench.stream_chat()
    bench.open()
    bench.tap_mic()

    rows = []
    for n in range(1, TURNS + 1):
        one_turn(bench, shape, n)
        rows.append(segments(bench.turn_timeline(n), shape))
    show(shape, rows)

    median = {key: statistics.median(row[key] for row in rows) for key in rows[0]}
    own = median["total"] - median["stt_sim"] - median["chat_sim"] - median["tts_sim"]
    assert median["silence"] <= BUDGETS["silence"], f"attente du silence : {median['silence']:.0f} ms"
    assert median["stt_to_chat"] <= BUDGETS["stt_to_chat"], f"/stt -> /chat : {median['stt_to_chat']:.0f} ms"
    assert median["wait"] <= BUDGETS["wait"][shape], f"avant l'envoi à /tts : {median['wait']:.0f} ms"
    assert median["sound_start"] <= BUDGETS["sound_start"], f"/tts -> son : {median['sound_start']:.0f} ms"
    assert own <= OWN_TOTAL[shape], f"ce qui revient au site : {own:.0f} ms sur {median['total']:.0f} ms au total"
    # Garde-fou du banc lui-même : les retards simulés sont bien ceux qu'on a demandés (sinon les seuils ne veulent rien dire).
    assert median["stt_sim"] >= STT_MS and median["tts_sim"] >= TTS_MS
    assert page.errors == []
