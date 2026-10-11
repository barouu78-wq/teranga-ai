"""Micro, STT, chat et TTS simulés pour tester la conversation vocale dans Chromium.

Rien ne sort de la machine : getUserMedia renvoie un flux fabriqué (un son dont on règle le
volume), /stt, /chat et /tts sont servis par page.route. Le serveur Flask local ne répond que
pour la page, le jeton CSRF et les fichiers statiques.

Un « tour » de parole : tap_mic() puis say() (le volume monte, puis retombe : le silence qui suit
termine l'enregistrement), puis le site appelle /stt, /chat et /tts, que le test peut laisser en
attente avec hold() pour observer l'état pendant l'attente, puis libérer avec release().

Flux de /chat en deux temps : page.route répond d'un seul bloc (route.fulfill n'envoie pas la réponse
par morceaux), ce qui ne permet pas de prouver qu'une action part AVANT la fin du flux. Avec
stream_chat(), la page reçoit à la place un vrai flux (ReadableStream) que le test alimente morceau par
morceau (chat_event) puis termine (chat_end) : la première phrase est livrée, le test observe /tts, puis
seulement ensuite livre la suite.

Appels de voix coupés : la page peut annuler un appel /tts en vol (« Arrêter »). page.route ne le dit
pas au test ; window.__tts.calls note donc, pour chaque appel, si la page l'a annulé (tts_calls_aborted).
"""

import json
import struct

# Flux de /chat piloté par le test : remplace fetch('/chat') par une réponse dont le corps est un
# ReadableStream alimenté par window.__chat.event(...) et fermé par window.__chat.end().
# Ne s'active que si le test a demandé stream_chat() ; la demande « mode json » (repli) passe au réseau.
# Les appels à /tts sont seulement notés (annulés ou non), puis transmis tels quels.
FAKE_CHAT_STREAM = """
(() => {
  const chat = window.__chat = {
    manual: false, calls: 0, bodies: [], controller: null, ended: false, aborted: false,
    encoder: new TextEncoder(),
    event(obj) {
      try { chat.controller.enqueue(chat.encoder.encode(JSON.stringify(obj) + "\\n")); return true; }
      catch (_) { return false; }  // flux déjà annulé par la page (« Arrêter ») : la suite n'arrive plus
    },
    end() {
      chat.ended = true;
      try { chat.controller.close(); } catch (_) {}
    },
  };
  const tts = window.__tts = { calls: [] };
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    const headers = (init && init.headers) || {};
    if (url.pathname === '/tts') {
      const call = { aborted: false };
      tts.calls.push(call);
      const signal = init && init.signal;
      if (signal) signal.addEventListener('abort', () => { call.aborted = true; });
    }
    if (chat.manual && url.pathname === '/chat' && !headers['X-Teranga-Mode']) {
      chat.calls++;
      chat.bodies.push(init && init.body ? String(init.body) : '');
      chat.ended = false;
      chat.aborted = false;
      const body = new ReadableStream({
        start(controller) {
          chat.controller = controller;
          const signal = init && init.signal;
          if (signal) signal.addEventListener('abort', () => {
            chat.aborted = true;
            try { controller.error(new DOMException('Aborted', 'AbortError')); } catch (_) {}
          });
        },
      });
      return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': 'application/x-ndjson' } }));
    }
    return nativeFetch(input, init);
  };
})();
"""

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
        page.add_init_script(FAKE_CHAT_STREAM)
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

    def wait_held(self, name, timeout=8000):
        """Attend que la page ait réellement envoyé la requête avant de la libérer.

        Sur une machine chargée, la requête part plus tard : un release() trop tôt ne trouve rien à
        libérer, et la requête arrivée ensuite reste en attente pour toujours.
        """
        attente = 0
        while not self.held[name]:
            assert attente < timeout, f"la page n'a jamais envoyé /{name} en {timeout} ms"
            self.page.wait_for_timeout(50)
            attente += 50

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

    def stream_chat(self):
        """À appeler avant open() : /chat répond par un flux que le test alimente (chat_event, chat_end)."""
        self.page.add_init_script("window.__chat.manual = true")

    def wait_chat_stream(self, calls=1, timeout=8000):
        """Attend que la page ait ouvert le flux de /chat (comme wait_held pour une requête retenue)."""
        self.page.wait_for_function("n => window.__chat.calls >= n", arg=calls, timeout=timeout)

    def chat_event(self, **event):
        """Livre un événement NDJSON au flux ouvert ; le flux reste ouvert (la suite n'est pas arrivée)."""
        self.wait_chat_stream()
        self.page.evaluate("e => window.__chat.event(e)", event)

    def chat_end(self):
        self.wait_chat_stream()
        self.page.evaluate("() => window.__chat.end()")

    def wait_tts_calls(self, count, timeout=8000):
        """Attend que la page ait envoyé au moins `count` demandes de voix (sans pause à durée fixe)."""
        attente = 0
        while len(self.tts_calls) < count:
            assert attente < timeout, f"/tts : {len(self.tts_calls)} appel(s) en {timeout} ms, {count} attendu(s)"
            self.page.wait_for_timeout(50)
            attente += 50

    def tts_calls_aborted(self):
        """Pour chaque appel /tts parti de la page : vrai si la page l'a annulé."""
        return self.page.evaluate("() => window.__tts.calls.map(call => call.aborted)")

    def wait_tts_aborted(self, count, timeout=8000):
        """Attend que la page ait annulé `count` appels /tts (annulation immédiate : « Arrêter » coupe les appels en vol)."""
        self.page.wait_for_function(
            "n => window.__tts.calls.filter(call => call.aborted).length >= n", arg=count, timeout=timeout
        )

    def chat_stream_aborted(self):
        return self.page.evaluate("() => window.__chat.aborted")

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
