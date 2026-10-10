"""Micro, STT, chat et TTS simulés pour tester la conversation vocale dans Chromium.

Rien ne sort de la machine : getUserMedia renvoie un flux fabriqué (un son dont on règle le
volume), /stt, /chat et /tts sont servis par page.route. Le serveur Flask local ne répond que
pour la page, le jeton CSRF et les fichiers statiques.

Un « tour » de parole : tap_mic() puis say() (le volume monte, puis retombe : le silence qui suit
termine l'enregistrement), puis le site appelle /stt, /chat et /tts, que le test peut laisser en
attente avec hold() pour observer l'état pendant l'attente, puis libérer avec release().
"""

import json
import struct

# Installé avant le script de la page : faux micro, enregistreurs et lecteurs comptés.
FAKE_MIC = """
(() => {
  const mic = window.__mic = {
    level: 0, calls: 0, error: null, gains: [], recorders: [], contexts: [], audios: [],
    set(v) { mic.level = v; mic.gains.forEach(g => { g.gain.value = v; }); },
    recording() { return mic.recorders.filter(r => r.state === 'recording').length; },
    playing() { return mic.audios.filter(a => !a.paused && !a.ended).length; },
  };
  const Native = window.MediaRecorder;
  window.MediaRecorder = class extends Native {
    constructor(stream, options) { super(stream, options); mic.recorders.push(this); }
  };
  const NativeContext = window.AudioContext;
  window.AudioContext = class extends NativeContext {
    constructor(...args) { super(...args); mic.contexts.push(this); }
  };
  const NativeAudio = window.Audio;
  window.Audio = class extends NativeAudio {
    constructor(...args) { super(...args); mic.audios.push(this); }
  };
  navigator.mediaDevices.getUserMedia = async () => {
    mic.calls++;
    if (mic.error) throw new DOMException(mic.error.message || mic.error.name, mic.error.name);
    const context = new window.AudioContext();
    await context.resume().catch(() => {});
    const oscillator = context.createOscillator();
    oscillator.frequency.value = 220;
    const gain = context.createGain();
    gain.gain.value = mic.level;
    const destination = context.createMediaStreamDestination();
    oscillator.connect(gain);
    gain.connect(destination);
    oscillator.start();
    mic.gains.push(gain);
    return destination.stream;
  };
})();
"""


def wav_bytes(ms=400, rate=8000):
    """Un vrai fichier WAV (silence) : le lecteur le joue puis déclenche « ended »."""
    samples = rate * ms // 1000
    data = b"\x00\x00" * samples
    header = (
        b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
        + b"data" + struct.pack("<I", len(data))
    )
    return header + data


def stream(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


class VoiceBench:
    """Un navigateur avec faux micro et faux serveurs vocaux, et ce qu'ils ont reçu."""

    def __init__(self, page, base_url):
        self.page = page
        self.base_url = base_url
        self.stt_calls = []
        self.chat_calls = []
        self.tts_calls = []
        self.held = {"stt": [], "chat": [], "tts": []}
        self.stt_handler = lambda route, n: route.fulfill(json={"text": f"Question {n}"})
        self.chat_handler = lambda route, n: route.fulfill(
            body=stream({"d": f"Réponse {n}."}), content_type="application/x-ndjson"
        )
        self.tts_handler = lambda route, n: route.fulfill(body=wav_bytes(), content_type="audio/wav")
        page.add_init_script(FAKE_MIC)
        page.route(f"{base_url}/stt", self._stt)
        page.route(f"{base_url}/chat", self._chat)
        page.route(f"{base_url}/tts", self._tts)

    def _stt(self, route):
        self.stt_calls.append(route.request)
        self.stt_handler(route, len(self.stt_calls))

    def _chat(self, route):
        self.chat_calls.append(route.request)
        self.chat_handler(route, len(self.chat_calls))

    def _tts(self, route):
        self.tts_calls.append(route.request)
        self.tts_handler(route, len(self.tts_calls))

    def hold(self, name):
        """La requête reste en attente jusqu'à release() : on observe l'état pendant l'attente."""
        setattr(self, f"{name}_handler", lambda route, n: self.held[name].append(route))

    def release(self, name, **response):
        """Répond aux requêtes en attente. Si la page les a abandonnées entre-temps, c'est normal."""
        routes, self.held[name] = self.held[name], []
        for route in routes:
            try:
                route.fulfill(**response)
            except Exception:  # noqa: BLE001 - requête annulée par la page (arrêt demandé)
                pass

    def tts_texts(self):
        return [json.loads(r.post_data)["text"] for r in self.tts_calls]

    def open(self, path="/"):
        self.page.goto(self.base_url + path)
        return self

    def tap_mic(self):
        self.page.click("#mic")

    def set_level(self, value):
        self.page.evaluate("v => window.__mic.set(v)", value)

    def recording(self):
        return self.page.evaluate("() => window.__mic.recording()")

    def playing(self):
        return self.page.evaluate("() => window.__mic.playing()")

    def wait_recording(self, timeout=5000):
        self.page.wait_for_function("() => window.__mic.recording() === 1", timeout=timeout)

    def wait_playing(self, timeout=8000):
        self.page.wait_for_function("() => window.__mic.playing() === 1", timeout=timeout)

    def say(self, ms=500, level=1):
        """Parler pendant ms millisecondes, puis se taire."""
        self.set_level(level)
        self.page.wait_for_timeout(ms)
        self.set_level(0)

    def speak_one_turn(self, ms=600):
        """Attend la fin du calibrage du bruit de fond, puis parle."""
        self.page.wait_for_timeout(700)
        self.say(ms)
