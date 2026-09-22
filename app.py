import os
import re
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template_string, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY est introuvable. Vérifie ton fichier .env."
    )

client = OpenAI(api_key=API_KEY, timeout=25.0, max_retries=1)

MAX_MESSAGE_LENGTH = 2000
MAX_TTS_LENGTH = 3500
MAX_HISTORY_ITEMS = 8
MAX_HISTORY_CHARS = 10000
RATE_LIMIT = 12
RATE_WINDOW = 60

request_log = defaultdict(deque)
tts_request_log = defaultdict(deque)

WEB_HINTS = (
    "aujourd'hui", "aujourd’hui", "maintenant", "actuel", "actuelle",
    "actuels", "actuelles", "récent", "récente", "récentes",
    "prix", "tarif", "coût", "combien", "horaire", "horaires",
    "ouvert", "ouverte", "disponible", "disponibilité", "réservation",
    "événement", "evenement", "météo", "meteo", "actualité", "actualités",
    "news", "today", "now", "current", "latest", "recent", "price",
    "cost", "schedule", "hours", "open", "available", "availability",
    "booking", "weather", "event", "how much", "taxi", "transport"
)


SYSTEM_PROMPT = """
Tu es Teranga AI, un assistant numérique moderne spécialisé dans le Sénégal.

MISSION
Aide les habitants du Sénégal, les voyageurs, la diaspora, les visiteurs et
les commerçants avec des informations utiles, claires et fiables sur le Sénégal.

LANGUES
- Réponds dans la langue utilisée par l'utilisateur.
- Français -> français naturel.
- English -> natural English.
- Wolof -> wolof lorsque tu peux le faire correctement.
- Comprends les mélanges français, anglais et wolof.
- Comprends les fautes de frappe, le langage SMS et les formulations courtes.

STYLE
- Sois chaleureux, professionnel et simple.
- Réponds directement.
- Sois concis par défaut.
- Donne les détails utiles quand ils sont nécessaires.
- Utilise des listes courtes quand cela améliore la lisibilité.
- N'invente jamais une information.

SÉNÉGAL
Tu peux aider notamment sur Dakar et les autres régions, tourisme, plages,
destinations, hôtels, restaurants, cuisine sénégalaise, marchés, commerce,
transport, culture, histoire, événements, démarches pratiques, entreprises,
services et vie quotidienne.

FIABILITÉ ET ACTUALITÉ
- Les prix, horaires, disponibilités, événements, transports, coordonnées et
  informations commerciales peuvent changer.
- Pour une information susceptible d'avoir changé récemment, utilise la
  recherche web lorsque c'est pertinent.
- Ne présente jamais une estimation comme un tarif officiel.
- Si une information n'est pas vérifiable ou reste incertaine, dis-le clairement.
- Privilégie les sources officielles ou récentes et fiables.
- Ne fabrique jamais le nom, l'adresse, le téléphone, le prix ou le site
  d'un hôtel, restaurant, entreprise ou service.

PRIX
- Pour un prix actuel, cherche une source récente lorsque nécessaire.
- Indique clairement lorsqu'un prix est indicatif, négociable ou variable.

POLITIQUE ET INFORMATIONS PUBLIQUES
- Pour les sujets politiques, électoraux ou institutionnels actuels, reste
  strictement factuel et neutre.
- Distingue les faits vérifiés, les déclarations et les analyses attribuées.
- Ne conseille pas à l'utilisateur pour qui voter et ne classe pas les candidats
  ou partis.

SÉCURITÉ
Pour les sujets sensibles ou dangereux, donne des conseils prudents et
recommande les sources officielles ou les professionnels appropriés.

OBJECTIF
L'utilisateur doit avoir l'impression de parler à un assistant sérieux,
moderne, utile et réellement adapté au Sénégal.
"""


def clean_answer(text):
    text = (text or "").strip()
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(.*?)\*(?!\*)", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def should_use_web(message):
    lowered = message.lower()
    return any(term in lowered for term in WEB_HINTS)


def build_conversation(history, message):
    lines = []
    if isinstance(history, list):
        recent = history[-MAX_HISTORY_ITEMS:]
        for index, item in enumerate(recent):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).lower()
            content = str(item.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                continue
            if index == len(recent) - 1 and role == "user" and content == message:
                continue
            label = "Utilisateur" if role == "user" else "Teranga AI"
            lines.append(f"{label}: {content[:2500]}")
    lines.append(f"Utilisateur: {message}")
    return "\n".join(lines)[-MAX_HISTORY_CHARS:]


def allowed_request(ip):
    now = time.time()
    log = request_log[ip]

    while log and now - log[0] > RATE_WINDOW:
        log.popleft()

    if len(log) >= RATE_LIMIT:
        return False

    log.append(now)
    return True


def allowed_tts_request(ip):
    now = time.time()
    log = tts_request_log[ip]
    while log and now - log[0] > 60:
        log.popleft()
    if len(log) >= 6:
        return False
    log.append(now)
    return True


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; media-src 'self' blob:; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "teranga-ai",
        "model": MODEL
    })


@app.post("/chat")
def chat():
    ip = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr or "unknown"
    )

    ip = ip.split(",")[0].strip()

    if not allowed_request(ip):
        return jsonify({
            "error": "Trop de demandes. Attends quelques secondes puis réessaie."
        }), 429

    data = request.get_json(silent=True) or {}

    message = str(data.get("message", "")).strip()
    history = data.get("history", [])
    language = str(data.get("language", "fr")).lower()

    if not message:
        return jsonify({
            "error": "Écris un message avant d'envoyer."
        }), 400

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": (
                f"Ton message est trop long. "
                f"Maximum {MAX_MESSAGE_LENGTH} caractères."
            )
        }), 400

    language_instruction = {
        "fr": (
            "L'utilisateur a choisi le français. "
            "Réponds en français naturel."
        ),
        "en": (
            "The user selected English. "
            "Reply in natural English."
        ),
        "wo": (
            "L'utilisateur a choisi le wolof. "
            "Réponds en wolof lorsque tu peux le faire correctement."
        ),
    }.get(
        language,
        "Réponds dans la langue de l'utilisateur."
    )

    final_instructions = (
        SYSTEM_PROMPT
        + "\n\n"
        + language_instruction
    )

    input_text = build_conversation(history, message)

    try:
        response_kwargs = {
            "model": MODEL,
            "instructions": final_instructions,
            "input": input_text,
            "max_output_tokens": 500,
        }
        if should_use_web(message):
            response_kwargs["tools"] = [{"type": "web_search"}]
        response = client.responses.create(**response_kwargs)

        reply = clean_answer(response.output_text or "")

        if not reply:
            reply = (
                "Désolé, je n'ai pas réussi à obtenir une réponse. "
                "Réessaie dans quelques secondes."
            )

        return jsonify({
            "reply": reply
        })

    except Exception:
        app.logger.exception("Erreur dans /chat")

        return jsonify({
            "error": (
                "Désolé, le service est temporairement indisponible. "
                "Réessaie dans quelques secondes."
            )
        }), 500


@app.post("/tts")
def tts():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    ip = ip.split(",")[0].strip()
    if not allowed_tts_request(ip):
        return jsonify({"error": "Trop de demandes vocales. Attends quelques secondes puis réessaie."}), 429
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    language = str(data.get("language", "fr")).lower()
    if not text:
        return jsonify({"error": "Texte manquant."}), 400
    if len(text) > MAX_TTS_LENGTH:
        return jsonify({"error": f"Texte vocal trop long. Maximum {MAX_TTS_LENGTH} caractères."}), 400
    language_name = {"fr": "French", "en": "English", "wo": "Wolof"}.get(language, "the language of the text")
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="marin",
            input=text,
            instructions=(f"Speak naturally, clearly and warmly in {language_name}. "
                          "Keep a comfortable pace and pronounce names carefully."),
            response_format="wav",
        )
        return Response(speech.content, mimetype="audio/wav", headers={"Cache-Control": "no-store"})
    except Exception:
        app.logger.exception("Erreur dans /tts")
        return jsonify({"error": "La génération vocale a échoué. Réessaie."}), 500


HTML = r"""
<!doctype html>

<html lang="fr">

<head>

<meta charset="utf-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<meta name="theme-color"
      content="#0b7a4b">

<title>Teranga AI V2 🇸🇳</title>


<style>
:root{
  --green:#087a4b;
  --green-2:#0c9b61;
  --green-dark:#075b39;
  --orange:#f79324;
  --cream:#f7fbf8;
  --ink:#14231c;
  --muted:#6b7b73;
  --line:#e4ece7;
  --card:#ffffff;
  --soft:#eef8f3;
  --shadow:0 18px 50px rgba(9,58,38,.10);
  --shadow-sm:0 8px 24px rgba(9,58,38,.07);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;
  color:var(--ink);
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  background:
    radial-gradient(circle at 90% 0%,rgba(247,147,36,.10),transparent 28%),
    radial-gradient(circle at 0% 20%,rgba(8,122,75,.09),transparent 30%),
    var(--cream);
}
button,textarea{font:inherit}
header{
  position:sticky;top:0;z-index:20;
  background:rgba(255,255,255,.90);
  backdrop-filter:blur(18px);
  border-bottom:1px solid rgba(228,236,231,.9);
}
.nav{
  max-width:1120px;margin:auto;padding:12px 18px;
  display:flex;align-items:center;justify-content:space-between;gap:14px;
}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.logo{
  width:44px;height:44px;border-radius:15px;display:grid;place-items:center;
  background:linear-gradient(145deg,var(--green),var(--green-2) 60%,var(--orange));
  box-shadow:0 8px 20px rgba(8,122,75,.22);
  font-size:22px;flex:none;
}
.brand-copy{min-width:0}
.brand-title{font-weight:850;font-size:17px;letter-spacing:-.02em}
.brand-sub{font-size:11px;color:var(--muted);margin-top:2px}
.status-dot{
  display:inline-block;width:7px;height:7px;border-radius:50%;
  background:#20a463;margin-right:5px;vertical-align:1px;
}
.lang{display:flex;gap:5px}
.lang button{
  border:1px solid var(--line);background:#fff;color:var(--green);
  border-radius:999px;padding:8px 11px;font-weight:800;cursor:pointer;
}
.lang button.active{background:var(--green);border-color:var(--green);color:#fff}
main{max-width:1120px;margin:auto;padding:22px 18px 70px}
.hero{
  position:relative;overflow:hidden;
  color:#fff;border-radius:30px;padding:34px 30px;
  background:linear-gradient(135deg,#075e3a 0%,#0a8c58 62%,#f79324 150%);
  box-shadow:var(--shadow);
}
.hero:after{
  content:"";position:absolute;width:190px;height:190px;border-radius:50%;
  right:-55px;top:-70px;background:rgba(255,255,255,.10);
}
.hero-top{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;position:relative;z-index:1}
.hero-badge{
  display:inline-flex;align-items:center;gap:7px;
  background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);
  padding:7px 11px;border-radius:999px;font-size:12px;font-weight:800;
}
.hero h1{margin:16px 0 9px;font-size:clamp(31px,6vw,55px);line-height:.98;letter-spacing:-.045em}
.hero p{max-width:700px;margin:0;font-size:17px;line-height:1.55;opacity:.95}
.hero-pills{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.hero-pills span{
  padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.13);
  border:1px solid rgba(255,255,255,.18);font-size:12px;
}
.section{margin-top:25px}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:12px}
.section h2{font-size:21px;margin:0;letter-spacing:-.025em}
.section-note{font-size:12px;color:var(--muted)}
.quick{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.quick button{
  border:1px solid var(--line);background:rgba(255,255,255,.9);
  border-radius:18px;padding:15px;text-align:left;cursor:pointer;
  box-shadow:var(--shadow-sm);transition:transform .16s,box-shadow .16s,border-color .16s;
}
.quick button:hover{transform:translateY(-2px);border-color:#cfe1d8;box-shadow:0 12px 28px rgba(9,58,38,.10)}
.quick .q-icon{font-size:20px;display:block;margin-bottom:8px}
.quick strong{display:block;font-size:14px}
.quick small{display:block;color:var(--muted);margin-top:3px;line-height:1.35}
.chat{
  margin-top:25px;background:rgba(255,255,255,.96);
  border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow);overflow:hidden;
}
.chat-head{
  padding:17px 20px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;gap:10px;
}
.chat-title{font-weight:850}
.chat-status{font-size:12px;color:var(--green);font-weight:700}
#messages{min-height:270px;max-height:570px;overflow:auto;padding:20px}
.empty-state{text-align:center;padding:30px 15px;color:var(--muted)}
.empty-icon{
  width:58px;height:58px;margin:0 auto 12px;border-radius:20px;
  display:grid;place-items:center;background:var(--soft);font-size:25px;
}
.msg{display:flex;margin:12px 0;gap:9px;align-items:flex-end}
.msg.user{justify-content:flex-end}
.avatar{
  width:30px;height:30px;border-radius:11px;display:grid;place-items:center;
  background:var(--soft);color:var(--green);font-size:15px;flex:none;
}
.msg.user .avatar{display:none}
.bubble{
  max-width:min(84%,680px);padding:13px 15px;border-radius:19px;
  line-height:1.52;white-space:pre-wrap;box-shadow:0 4px 14px rgba(20,50,35,.04);
}
.assistant .bubble{background:var(--soft);border-bottom-left-radius:7px}
.user .bubble{background:var(--green);color:#fff;border-bottom-right-radius:7px}
.speak-button{
  display:block;margin:6px 0 0 39px;border:0;background:transparent;
  color:var(--green);cursor:pointer;font-size:13px;font-weight:800;padding:3px 0;
}
.speak-button:disabled{opacity:.6}
.composer{
  padding:12px;border-top:1px solid var(--line);
  background:#fbfdfc;display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:end;
}
.input-wrap{position:relative}
textarea{
  width:100%;resize:none;min-height:52px;max-height:150px;
  border:1px solid var(--line);border-radius:18px;padding:14px 15px;
  background:#fff;color:var(--ink);outline:none;
}
textarea:focus{border-color:var(--green);box-shadow:0 0 0 4px rgba(8,122,75,.08)}
.voice-button,#send{
  height:52px;border:0;border-radius:17px;cursor:pointer;font-weight:850;
}
.voice-button{width:52px;background:#fff1df;color:#b96300;border:1px solid #f5d3aa;font-size:21px}
.voice-button.listening{background:#c93636;color:#fff;border-color:#c93636;animation:pulse 1s infinite}
#send{padding:0 19px;background:var(--green);color:#fff;box-shadow:0 8px 18px rgba(8,122,75,.20)}
#send:disabled{opacity:.55;cursor:not-allowed;box-shadow:none}
.composer-hint{grid-column:1/-1;font-size:11px;color:var(--muted);padding:0 4px}
@keyframes pulse{50%{transform:scale(1.04)}}
.destinations{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.destination{
  border:1px solid var(--line);background:#fff;border-radius:20px;padding:18px;
  box-shadow:var(--shadow-sm);
}
.destination strong{display:block;margin-bottom:6px}
.destination span{color:var(--muted);line-height:1.45;font-size:14px}
footer{text-align:center;padding:28px 18px 42px;color:var(--muted);font-size:12px}
@media(max-width:800px){
  .quick{grid-template-columns:repeat(2,1fr)}
  .destinations{grid-template-columns:1fr}
}
@media(max-width:560px){
  .nav{padding:10px 12px}.logo{width:40px;height:40px}
  .brand-sub{display:none}.lang button{padding:7px 9px}
  main{padding:14px 10px 55px}
  .hero{border-radius:24px;padding:25px 20px}
  .hero h1{font-size:34px}.hero p{font-size:15px}
  .hero-pills span:nth-child(n+3){display:none}
  .quick{grid-template-columns:1fr 1fr;gap:8px}
  .quick button{padding:13px}.quick small{display:none}
  .chat{border-radius:23px}
  #messages{padding:14px;min-height:300px}
  .bubble{max-width:89%}
  .composer{grid-template-columns:1fr auto}
  #send{grid-column:1/2}.voice-button{grid-column:2/3}
  .composer-hint{grid-column:1/-1;grid-row:3}
}
</style>

</head>


<body>
<header>
  <div class="nav">
    <div class="brand">
      <div class="logo">🌴</div>
      <div class="brand-copy">
        <div class="brand-title">Teranga AI V2</div>
        <div class="brand-sub"><span class="status-dot"></span>Assistant Sénégal</div>
      </div>
    </div>
    <div class="lang">
      <button data-lang="fr" class="active">FR</button>
      <button data-lang="en">EN</button>
      <button data-lang="wo">WO</button>
    </div>
  </div>
</header>

<main>
  <section class="hero">
    <div class="hero-top">
      <div>
        <span class="hero-badge">🇸🇳 Pensé pour le Sénégal</span>
        <h1>Ton assistant,<br>version Teranga.</h1>
        <p id="heroText">Ton assistant intelligent pour le Sénégal : tourisme, transport, prix, culture, démarches et vie quotidienne.</p>
        <div class="hero-pills">
          <span>⚡ Rapide</span><span>🎤 Vocal</span><span>🌍 FR · EN · WO</span>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <h2 id="quickTitle">Questions rapides</h2>
      <span class="section-note">Appuie pour demander</span>
    </div>
    <div class="quick">
      <button data-question="Quel temps fait-il à Dakar aujourd'hui ?">
        <span class="q-icon">🌤️</span><strong>Météo</strong><small>Dakar aujourd'hui</small>
      </button>
      <button data-question="Combien coûte un taxi de l'aéroport AIBD à Dakar ?">
        <span class="q-icon">🚕</span><strong>Taxi AIBD</strong><small>AIBD → Dakar</small>
      </button>
      <button data-question="Quels sont les endroits à visiter au Sénégal ?">
        <span class="q-icon">📍</span><strong>À visiter</strong><small>Destinations</small>
      </button>
      <button data-question="Quels plats sénégalais dois-je goûter ?">
        <span class="q-icon">🍲</span><strong>Cuisine</strong><small>Saveurs locales</small>
      </button>
    </div>
  </section>

  <section class="chat">
    <div class="chat-head">
      <span class="chat-title" id="chatTitle">Pose ta question à Teranga AI</span>
      <span class="chat-status">● En ligne</span>
    </div>
    <div id="messages">
      <div class="empty-state" id="emptyState">
        <div class="empty-icon">🌴</div>
        <strong>Bienvenue sur Teranga AI</strong>
        <div>Écris ta question ou utilise le micro.</div>
      </div>
    </div>
    <div class="composer">
      <div class="input-wrap">
        <textarea id="input" maxlength="2000" placeholder="Ex. Quel est le prix d'un taxi AIBD → Dakar ?"></textarea>
      </div>
      <button id="mic" class="voice-button" type="button" title="Parler">🎤</button>
      <button id="send">Envoyer</button>
      <div class="composer-hint">La réponse peut être lue automatiquement à voix haute.</div>
    </div>
  </section>

  <section class="section">
    <div class="section-head"><h2>Quelques idées 🇸🇳</h2><span class="section-note">Découvrir le Sénégal</span></div>
    <div class="destinations">
      <div class="destination"><strong>🏙️ Dakar</strong><span>Culture, marchés, restaurants et vie urbaine.</span></div>
      <div class="destination"><strong>🏝️ Île de Gorée</strong><span>Histoire, patrimoine et découverte culturelle.</span></div>
      <div class="destination"><strong>🌊 Saly & Petite Côte</strong><span>Plages, détente et activités touristiques.</span></div>
    </div>
  </section>
</main>

<footer>
  Teranga AI V2 — Un assistant numérique dédié au Sénégal 🇸🇳<br>
  <small>La voix entendue est générée par une IA.</small>
</footer>

<script>
<script>

const input =
    document.getElementById('input');

const send =
    document.getElementById('send');

const mic =
    document.getElementById('mic');

const messages =
    document.getElementById('messages');

let history = [];

let currentLanguage = 'fr';

let recognition = null;

let isListening = false;


const translations = {

    fr: {
        hero:
            'Ton assistant intelligent pour le Sénégal : tourisme, transport, prix, culture, démarches et vie quotidienne.',
        quick:
            'Questions rapides',
        chat:
            'Pose ta question à Teranga AI',
        placeholder:
            "Ex. Quel est le prix d'un taxi AIBD → Dakar ?",
        send:
            'Envoyer',
        welcome:
            'Bonjour 👋 Je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',
        listen:
            '🎤',
        listening:
            '🔴'
    },

    en: {
        hero:
            'Your intelligent assistant for Senegal: tourism, transport, prices, culture, practical procedures and daily life.',
        quick:
            'Quick questions',
        chat:
            'Ask Teranga AI',
        placeholder:
            'Example: How much is a taxi from AIBD to Dakar?',
        send:
            'Send',
        welcome:
            'Hello 👋 I am Teranga AI. What would you like to know about Senegal?',
        listen:
            '🎤',
        listening:
            '🔴'
    },

    wo: {
        hero:
            'Sa xam-xam bu bees ci Senegaal: tukki, transport, njëg, aada ak dund gu bees.',
        quick:
            'Laaj yu gaaw',
        chat:
            'Laajal Teranga AI',
        placeholder:
            'Misaal: Ñaata la taxi AIBD ba Dakar?',
        send:
            'Yónnee',
        welcome:
            'Salaam 👋 Maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',
        listen:
            '🎤',
        listening:
            '🔴'
    }

};


const voiceLanguages = {
    fr: 'fr-FR',
    en: 'en-US',
    wo: 'wo-SN'
};


function addMessage(role, text) {

    const row =
        document.createElement('div');

    row.className =
        'msg ' + role;

    const bubble =
        document.createElement('div');

    bubble.className =
        'bubble';

    bubble.textContent =
        text;

    row.appendChild(bubble);

    if (role === 'assistant') {

        const speakButton =
            document.createElement('button');

        speakButton.type = 'button';

        speakButton.className =
            'speak-button';

        speakButton.textContent =
            '🔊 Écouter';

        speakButton.addEventListener(
            'click',
            function () {
                playTTS(text, speakButton);
            }
        );

        row.appendChild(speakButton);
    }

    messages.appendChild(row);

    messages.scrollTop =
        messages.scrollHeight;
}


let currentAudio = null;


async function playTTS(text, button = null) {
    if (!text) return;
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    if (button) {
        button.disabled = true;
        button.textContent = '⏳ Lecture…';
    }
    try {
        const response = await fetch('/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text, language: currentLanguage})
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || 'Erreur audio');
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        currentAudio = audio;
        audio.onended = () => {
            URL.revokeObjectURL(url);
            if (currentAudio === audio) currentAudio = null;
            if (button) { button.disabled = false; button.textContent = '🔊 Écouter'; }
        };
        await audio.play();
    } catch (error) {
        if (button) { button.disabled = false; button.textContent = '🔊 Écouter'; }
        console.debug('Lecture vocale indisponible:', error);
    }
}


function setupVoice() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        mic.disabled = true;
        mic.title =
            'La reconnaissance vocale n’est pas disponible sur ce navigateur.';

        return;
    }

    recognition =
        new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.lang =
        voiceLanguages[currentLanguage];

    recognition.onstart =
        function () {

            isListening = true;

            mic.classList.add('listening');

            mic.textContent =
                translations[currentLanguage].listening;
        };


    recognition.onresult =
        function (event) {

            const transcript =
                event.results[0][0].transcript;

            input.value =
                transcript;

            input.dispatchEvent(
                new Event(
                    'input',
                    { bubbles: true }
                )
            );

            mic.classList.remove(
                'listening'
            );

            mic.textContent =
                translations[currentLanguage].listen;

            isListening = false;
            sendMessage(null, true);
        };


    recognition.onerror =
        function () {

            isListening = false;

            mic.classList.remove(
                'listening'
            );

            mic.textContent =
                translations[currentLanguage].listen;
        };


    recognition.onend =
        function () {

            isListening = false;

            mic.classList.remove(
                'listening'
            );

            mic.textContent =
                translations[currentLanguage].listen;
        };
}


function startVoice() {

    if (!recognition) {
        return;
    }

    if (isListening) {
        recognition.stop();
        return;
    }

    recognition.lang =
        voiceLanguages[currentLanguage] || 'fr-FR';

    try {
        recognition.start();
    } catch (error) {
        isListening = false;
    }
}


function setLanguage(lang) {

    currentLanguage = lang;

    document
        .querySelectorAll('.lang button')
        .forEach(btn => {

            btn.classList.toggle(
                'active',
                btn.dataset.lang === lang
            );

        });

    const t =
        translations[lang];

    document
        .getElementById('heroText')
        .textContent = t.hero;

    document
        .getElementById('quickTitle')
        .textContent = t.quick;

    document
        .getElementById('chatTitle')
        .textContent = t.chat;

    document
        .getElementById('input')
        .placeholder = t.placeholder;

    document
        .getElementById('send')
        .textContent = t.send;

    if (mic && !isListening) {
        mic.textContent = t.listen;
    }

    if (recognition) {
        recognition.lang =
            voiceLanguages[lang] || 'fr-FR';
    }
}


async function sendMessage(textFromButton = null, fromVoice = false) {

    const text =
        (textFromButton || input.value).trim();

    if (!text || send.disabled) {
        return;
    }

    addMessage(
        'user',
        text
    );

    history.push({
        role: 'user',
        content: text
    });

    input.value = '';

    send.disabled = true;

    send.textContent =
        currentLanguage === 'en'
            ? 'Thinking…'
            : 'Réflexion…';

    try {

        const response =
            await fetch('/chat', {

                method: 'POST',

                headers: {
                    'Content-Type':
                        'application/json'
                },

                body: JSON.stringify({

                    message: text,

                    history:
                        history.slice(-8),

                    language:
                        currentLanguage

                })

            });


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.error || 'Erreur'
            );
        }


        const reply =
            data.reply ||
            'Aucune réponse.';


        addMessage(
            'assistant',
            reply
        );

        setTimeout(() => playTTS(reply), 0);

        history.push({
            role: 'assistant',
            content: reply
        });


        history =
            history.slice(-8);


    } catch (error) {

        addMessage(
            'assistant',
            error.message ||
            'Service temporairement indisponible.'
        );

    } finally {

        send.disabled = false;

        send.textContent =
            translations[
                currentLanguage
            ].send;

        input.focus();
    }
}


document
    .querySelectorAll('.lang button')
    .forEach(btn => {

        btn.addEventListener(
            'click',
            () => setLanguage(
                btn.dataset.lang
            )
        );

    });


document
    .querySelectorAll('.quick button')
    .forEach(btn => {

        btn.addEventListener(
            'click',
            () => sendMessage(
                btn.dataset.question
            )
        );

    });


send.addEventListener(
    'click',
    () => sendMessage()
);


mic.addEventListener(
    'click',
    () => startVoice()
);


input.addEventListener(
    'keydown',
    event => {

        if (
            event.key === 'Enter' &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }

    }
);


setLanguage('fr');

setupVoice();

addMessage(
    'assistant',
    translations.fr.welcome
);

</script>

</body>

</html>
"""


@app.get("/")
def home():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=False
    ) 