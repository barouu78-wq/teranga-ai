import hashlib
import hmac
import json
import os
import re
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, make_response, render_template_string, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["JSON_SORT_KEYS"] = False
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
TRUST_PROXY = os.getenv("TRUST_PROXY", "1") == "1"
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
}

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY est introuvable. Vérifie ton fichier .env."
    )

client = OpenAI(api_key=API_KEY, timeout=20.0, max_retries=0)

MAX_MESSAGE_LENGTH = 2000
MAX_TTS_LENGTH = 2200
MAX_HISTORY_ITEMS = 6
MAX_HISTORY_CHARS = 7000
RATE_LIMIT = 12
RATE_WINDOW = 60
TTS_RATE_LIMIT = 6
CSRF_COOKIE = "teranga_csrf"
CSRF_HEADER = "X-CSRF-Token"

request_log = defaultdict(deque)
tts_request_log = defaultdict(deque)

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_LANG = frozenset({"fr", "en", "wo"})

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
- Sois concis par défaut. Maximum 8 phrases sauf si l'utilisateur demande plus.
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


def sanitize_text(text, max_len):
    text = CONTROL_CHARS.sub("", str(text or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()[:max_len]


def clean_answer(text):
    text = sanitize_text(text, 8000)
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
            content = sanitize_text(item.get("content", ""), 1800)
            if role not in {"user", "assistant"} or not content:
                continue
            if index == len(recent) - 1 and role == "user" and content == message:
                continue
            label = "Utilisateur" if role == "user" else "Teranga AI"
            lines.append(f"{label}: {content}")
    lines.append(f"Utilisateur: {message}")
    return "\n".join(lines)[-MAX_HISTORY_CHARS:]


def client_ip():
    if TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return (request.remote_addr or "unknown")[:64]


def allowed_request(ip, log, limit, window):
    now = time.time()
    while log and now - log[0] > window:
        log.popleft()
    if len(log) >= limit:
        return False
    log.append(now)
    return True


def sign_token(value):
    digest = hmac.new(
        app.config["SECRET_KEY"].encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{value}.{digest}"


def valid_token(token):
    if not token or "." not in token:
        return False
    value, _, provided = token.partition(".")
    expected = hmac.new(
        app.config["SECRET_KEY"].encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(provided, expected)


def issue_csrf():
    return sign_token(secrets.token_urlsafe(24))


def origin_allowed():
    if not ALLOWED_ORIGINS:
        return True
    origin = request.headers.get("Origin") or ""
    referer = request.headers.get("Referer") or ""
    if origin:
        return origin in ALLOWED_ORIGINS
    return any(referer.startswith(allowed) for allowed in ALLOWED_ORIGINS)


def require_json_post(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.method != "POST":
            return jsonify({"error": "Méthode non autorisée."}), 405
        if request.mimetype != "application/json":
            return jsonify({"error": "Type de contenu invalide."}), 415
        if not origin_allowed():
            return jsonify({"error": "Origine non autorisée."}), 403
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")
        if not cookie_token or not header_token:
            return jsonify({"error": "Jeton de sécurité manquant."}), 403
        if not hmac.compare_digest(cookie_token, header_token) or not valid_token(cookie_token):
            return jsonify({"error": "Jeton de sécurité invalide."}), 403
        return fn(*args, **kwargs)
    return wrapper


@app.after_request
def add_security_headers(response):
    nonce = getattr(request, "_csp_nonce", "")
    script_src = "'self'"
    if nonce:
        script_src += f" 'nonce-{nonce}'"
    else:
        script_src += " 'unsafe-inline'"

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(), microphone=(self), payment=(), usb=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; script-src {script_src}; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; media-src 'self' blob:; "
        "font-src 'self' data:; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; "
        "upgrade-insecure-requests"
    )
    if request.path == "/health":
        response.headers["Cache-Control"] = "no-store"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    response.headers.pop("Server", None)
    return response


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "teranga-ai", "model": MODEL})


def parse_chat_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Requête invalide."}), 400)

    message = sanitize_text(data.get("message", ""), MAX_MESSAGE_LENGTH)
    history = data.get("history", [])
    language = str(data.get("language", "fr")).lower()[:8]
    if language not in SAFE_LANG:
        language = "fr"
    if not isinstance(history, list):
        history = []
    history = history[-MAX_HISTORY_ITEMS:]
    if not message:
        return None, (jsonify({"error": "Écris un message avant d'envoyer."}), 400)

    language_instruction = {
        "fr": "L'utilisateur a choisi le français. Réponds en français naturel.",
        "en": "The user selected English. Reply in natural English.",
        "wo": "L'utilisateur a choisi le wolof. Réponds en wolof lorsque tu peux le faire correctement.",
    }[language]
    return {
        "message": message,
        "history": history,
        "instructions": SYSTEM_PROMPT + "\n\n" + language_instruction,
        "input_text": build_conversation(history, message),
        "use_web": should_use_web(message),
    }, None


@app.post("/chat")
@require_json_post
def chat():
    ip = client_ip()
    if not allowed_request(ip, request_log[ip], RATE_LIMIT, RATE_WINDOW):
        return jsonify({
            "error": "Trop de demandes. Attends quelques secondes puis réessaie."
        }), 429

    payload, error = parse_chat_payload()
    if error:
        return error

    kwargs = {
        "model": MODEL,
        "instructions": payload["instructions"],
        "input": payload["input_text"],
        "max_output_tokens": 380,
        "stream": True,
    }
    if payload["use_web"]:
        kwargs["tools"] = [{"type": "web_search"}]

    def generate():
        try:
            stream = client.responses.create(**kwargs)
            for event in stream:
                etype = getattr(event, "type", "")
                if etype == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        yield json.dumps({"d": delta}, ensure_ascii=False) + "\n"
                elif etype == "response.failed":
                    yield json.dumps({
                        "error": "Désolé, le service est temporairement indisponible."
                    }, ensure_ascii=False) + "\n"
                    return
            yield json.dumps({"done": True}) + "\n"
        except Exception:
            app.logger.exception("Erreur stream /chat")
            try:
                fallback_kwargs = dict(kwargs)
                fallback_kwargs.pop("stream", None)
                response = client.responses.create(**fallback_kwargs)
                reply = clean_answer(response.output_text or "")
                if reply:
                    yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
                    yield json.dumps({"done": True}) + "\n"
                    return
            except Exception:
                app.logger.exception("Erreur fallback /chat")
            yield json.dumps({
                "error": (
                    "Désolé, le service est temporairement indisponible. "
                    "Réessaie dans quelques secondes."
                )
            }, ensure_ascii=False) + "\n"

    return Response(
        generate(),
        mimetype="application/x-ndjson",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-store",
        },
    )


@app.post("/tts")
@require_json_post
def tts():
    ip = client_ip()
    if not allowed_request(ip, tts_request_log[ip], TTS_RATE_LIMIT, 60):
        return jsonify({
            "error": "Trop de demandes vocales. Attends quelques secondes puis réessaie."
        }), 429

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Requête invalide."}), 400

    text = sanitize_text(data.get("text", ""), MAX_TTS_LENGTH)
    language = str(data.get("language", "fr")).lower()[:8]
    if language not in SAFE_LANG:
        language = "fr"
    if not text:
        return jsonify({"error": "Texte manquant."}), 400

    language_name = {"fr": "French", "en": "English", "wo": "Wolof"}[language]
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="marin",
            input=text,
            instructions=(
                f"Speak naturally, clearly and warmly in {language_name}. "
                "Keep a comfortable pace and pronounce names carefully."
            ),
            response_format="wav",
        )
        return Response(
            speech.content,
            mimetype="audio/wav",
            headers={"Cache-Control": "no-store"},
        )
    except Exception:
        app.logger.exception("Erreur dans /tts")
        return jsonify({"error": "La génération vocale a échoué. Réessaie."}), 500


HTML = r"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#073528">
<meta name="description" content="Teranga AI — assistant intelligent dédié au Sénégal.">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>Teranga AI · Sénégal</title>
<style>
:root{
  --g:#0b7d4e;--gd:#06291e;--gm:#0e9a5f;--gold:#f3c15a;--ink:#10241a;
  --mute:#66786e;--line:rgba(8,40,26,.10);--card:#fff;--soft:#e7f4ec;
  --bg:#f3f7f4;--r:22px;
}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;background:
  radial-gradient(800px 280px at 100% -8%,rgba(243,193,90,.16),transparent 50%),
  radial-gradient(640px 260px at 0 0,rgba(11,125,78,.12),transparent 46%),var(--bg)}
body:before{content:"";position:fixed;inset:0 0 auto;height:3px;z-index:50;background:linear-gradient(90deg,#0b7d4e 0 34%,#f3c15a 34% 66%,#ce1126 66% 100%)}
button,textarea{font:inherit}button{touch-action:manipulation}
header{position:sticky;top:0;z-index:30;background:rgba(243,247,244,.86);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.nav{max-width:980px;margin:auto;padding:10px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px}
.brand{display:flex;align-items:center;gap:10px}
.logo{width:38px;height:38px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(160deg,var(--gm),var(--gd));color:#fff;font-size:18px;box-shadow:0 8px 18px rgba(6,41,30,.22)}
.brand b{display:block;font-size:15px;letter-spacing:-.03em}
.brand small{color:var(--mute);font-size:11px}
.nav-actions{display:flex;gap:6px;align-items:center}
.lang{display:flex;background:#fff;border:1px solid var(--line);border-radius:999px;padding:3px}
.lang button{border:0;background:0;color:var(--g);border-radius:999px;padding:6px 9px;font-weight:750;cursor:pointer}
.lang button.active{background:var(--gd);color:#fff}
.icon-btn{width:36px;height:36px;border-radius:999px;border:1px solid var(--line);background:#fff;cursor:pointer;color:var(--mute)}
main{max-width:980px;margin:auto;padding:16px 16px 36px}
.hero{color:#fff;border-radius:26px;padding:22px 22px 18px;background:linear-gradient(145deg,#073528 0%,#0b7d4e 62%,#d89a20 150%);box-shadow:0 18px 40px rgba(6,41,30,.16)}
.hero h1{margin:8px 0 6px;font-size:clamp(28px,6vw,46px);line-height:.95;letter-spacing:-.048em}
.hero p{margin:0;max-width:52ch;opacity:.94;font-size:15px;line-height:1.45}
.chips{display:flex;gap:8px;overflow:auto;padding:12px 0 4px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chips button{flex:none;border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 13px;cursor:pointer;font-weight:650;font-size:13px;box-shadow:0 4px 12px rgba(8,40,26,.05)}
.chat{margin-top:8px;background:#fff;border:1px solid var(--line);border-radius:26px;overflow:hidden;box-shadow:0 16px 40px rgba(8,40,26,.07);display:flex;flex-direction:column;min-height:min(68vh,620px)}
.chat-head{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;font-weight:750}
.live{color:var(--g);font-size:12px;font-weight:700}
#messages{flex:1;overflow:auto;padding:16px;min-height:240px}
.msg{display:flex;margin:10px 0;animation:rise .18s ease}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.msg.user{justify-content:flex-end}
.bubble{max-width:min(86%,640px);padding:11px 14px;border-radius:18px;line-height:1.5;white-space:pre-wrap}
.assistant .bubble{background:var(--soft);border-bottom-left-radius:6px}
.user .bubble{background:var(--gd);color:#fff;border-bottom-right-radius:6px}
.speak-button{margin:5px 0 0;border:0;background:0;color:var(--g);cursor:pointer;font-size:12px;font-weight:750}
.typing{display:flex;gap:5px;padding:12px 14px;width:fit-content}
.typing i{width:7px;height:7px;border-radius:50%;background:#7aa389;animation:blink 1s infinite}
.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
@keyframes blink{50%{opacity:.25;transform:translateY(-2px)}}
.composer{padding:10px;border-top:1px solid var(--line);background:#f7fbf8;display:grid;grid-template-columns:1fr auto auto;gap:7px;align-items:end}
textarea{width:100%;resize:none;min-height:48px;max-height:120px;border:1px solid var(--line);border-radius:16px;padding:12px 13px;outline:0}
textarea:focus{border-color:var(--g);box-shadow:0 0 0 3px rgba(11,125,78,.12)}
.voice-button,#send{height:48px;border:0;border-radius:15px;cursor:pointer;font-weight:800}
.voice-button{width:48px;background:#fff4df;color:#a15d00;border:1px solid #efd3a0}
.voice-button.listening{background:#c93636;color:#fff;border-color:#c93636}
#send{padding:0 16px;background:var(--gd);color:#fff}
#send:disabled{opacity:.55}
.hint{grid-column:1/-1;font-size:11px;color:var(--mute);display:flex;justify-content:space-between;gap:8px}
.toggle{border:0;background:0;color:var(--g);cursor:pointer;font-weight:750;font-size:11px}
.places{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}
.place{background:#fff;border:1px solid var(--line);border-radius:18px;padding:14px}
.place b{display:block;margin-bottom:4px}.place span{color:var(--mute);font-size:13px;line-height:1.4}
footer{text-align:center;padding:22px 12px 28px;color:var(--mute);font-size:12px}
@media(max-width:720px){.places{grid-template-columns:1fr}.composer{grid-template-columns:1fr auto}#send{grid-column:1/2}.voice-button{grid-column:2/3}.hero{padding:18px}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<header>
  <div class="nav">
    <div class="brand">
      <div class="logo" aria-hidden="true">🌴</div>
      <div><b>Teranga AI</b><small>Assistant Sénégal</small></div>
    </div>
    <div class="nav-actions">
      <div class="lang" aria-label="Langue">
        <button type="button" data-lang="fr" class="active">FR</button>
        <button type="button" data-lang="en">EN</button>
        <button type="button" data-lang="wo">WO</button>
      </div>
      <button id="resetBtn" class="icon-btn" type="button" title="Nouvelle conversation">↺</button>
    </div>
  </div>
</header>
<main>
  <section class="hero">
    <h1>Ton assistant,<br>version Teranga.</h1>
    <p id="heroText">Tourisme, transport, prix, culture et démarches — réponses rapides, adaptées au Sénégal.</p>
  </section>
  <div class="chips" id="chips">
    <button type="button" data-question="Quel temps fait-il à Dakar aujourd'hui ?">🌤️ Météo Dakar</button>
    <button type="button" data-question="Combien coûte un taxi de l'aéroport AIBD à Dakar ?">🚕 Taxi AIBD</button>
    <button type="button" data-question="Quels sont les endroits à visiter au Sénégal ?">📍 À visiter</button>
    <button type="button" data-question="Quels plats sénégalais dois-je goûter ?">🍲 Cuisine</button>
  </div>
  <section class="chat">
    <div class="chat-head">
      <span id="chatTitle">Discussion</span>
      <span class="live">● En ligne</span>
    </div>
    <div id="messages"></div>
    <div class="composer">
      <textarea id="input" maxlength="2000" placeholder="Ex. Prix d’un taxi AIBD → Dakar ?" aria-label="Message"></textarea>
      <button id="mic" class="voice-button" type="button" title="Parler">🎤</button>
      <button id="send" type="button">Envoyer</button>
      <div class="hint">
        <span id="hintText">Réponses en direct. La voix se lance seulement si tu l’actives.</span>
        <button id="voiceToggle" class="toggle" type="button">Voix auto : off</button>
      </div>
    </div>
  </section>
  <div class="places">
    <div class="place"><b>🏙️ Dakar</b><span>Marchés, restos, culture et rythme de la capitale.</span></div>
    <div class="place"><b>🏝️ Gorée</b><span>Histoire, patrimoine et vue sur l’Atlantique.</span></div>
    <div class="place"><b>🌊 Petite Côte</b><span>Saly, plages et week-ends au bord de mer.</span></div>
  </div>
</main>
<footer>Teranga AI — assistant dédié au Sénégal · voix générée par IA</footer>
<script nonce="__CSP_NONCE__">
const input=document.getElementById('input');
const send=document.getElementById('send');
const mic=document.getElementById('mic');
const messages=document.getElementById('messages');
const resetBtn=document.getElementById('resetBtn');
const voiceToggle=document.getElementById('voiceToggle');
const csrfToken=(document.cookie.split('; ').find(r=>r.startsWith('teranga_csrf='))||'').slice(13);
let history=[], currentLanguage='fr', recognition=null, isListening=false, currentAudio=null, autoVoice=false, inflight=null;
const T={
fr:{hero:'Tourisme, transport, prix, culture et démarches — réponses rapides, adaptées au Sénégal.',chat:'Discussion',ph:'Ex. Prix d’un taxi AIBD → Dakar ?',send:'Envoyer',welcome:'Bonjour 👋 Je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',listen:'🎤',listening:'🔴',reset:'Nouvelle conversation',thinking:'…',timeout:'Ça prend trop de temps. Réessaie.',voiceOn:'Voix auto : on',voiceOff:'Voix auto : off',hint:'Réponses en direct. La voix se lance seulement si tu l’actives.'},
en:{hero:'Tourism, transport, prices, culture and practical help — fast answers for Senegal.',chat:'Chat',ph:'Ex. Taxi fare AIBD → Dakar?',send:'Send',welcome:'Hello 👋 I am Teranga AI. What would you like to know about Senegal?',listen:'🎤',listening:'🔴',reset:'New conversation',thinking:'…',timeout:'This is taking too long. Try again.',voiceOn:'Auto voice: on',voiceOff:'Auto voice: off',hint:'Live answers. Voice plays only if you turn it on.'},
wo:{hero:'Tukki, transport, njëg, aada ak dund — tontu yu gaaw ci Senegaal.',chat:'Waxtaan',ph:'Misaal: Ñaata la taxi AIBD ba Dakar?',send:'Yónnee',welcome:'Salaam 👋 Maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',listen:'🎤',listening:'🔴',reset:'Waxtaan bu bees',thinking:'…',timeout:'Dafa yàgg lool. Jéemaatal.',voiceOn:'Baat auto: on',voiceOff:'Baat auto: off',hint:'Tontu ci kaw. Baat dafay dox su ko taalaatée.'}
};
const voiceLanguages={fr:'fr-FR',en:'en-US',wo:'wo-SN'};
function addBubble(role,text=''){
  const row=document.createElement('div');
  row.className='msg '+role;
  const bubble=document.createElement('div');
  bubble.className='bubble';
  bubble.textContent=text;
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop=messages.scrollHeight;
  return {row,bubble};
}
function addSpeak(row,text){
  const b=document.createElement('button');
  b.type='button';b.className='speak-button';b.textContent='🔊 Écouter';
  b.onclick=()=>playTTS(text,b);
  row.appendChild(b);
}
async function playTTS(text,button){
  if(!text)return;
  if(currentAudio){currentAudio.pause();currentAudio=null;}
  if(button){button.disabled=true;button.textContent='⏳';}
  try{
    const res=await fetch('/tts',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':decodeURIComponent(csrfToken)},body:JSON.stringify({text,language:currentLanguage})});
    if(!res.ok)throw new Error();
    const url=URL.createObjectURL(await res.blob());
    const audio=new Audio(url);currentAudio=audio;
    audio.onended=()=>{URL.revokeObjectURL(url);if(currentAudio===audio)currentAudio=null;if(button){button.disabled=false;button.textContent='🔊 Écouter';}};
    await audio.play();
  }catch(e){if(button){button.disabled=false;button.textContent='🔊 Écouter';}}
}
function setupVoice(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){mic.disabled=true;return;}
  recognition=new SR();recognition.continuous=false;recognition.interimResults=false;recognition.lang=voiceLanguages[currentLanguage];
  recognition.onstart=()=>{isListening=true;mic.classList.add('listening');mic.textContent=T[currentLanguage].listening;};
  recognition.onresult=e=>{input.value=e.results[0][0].transcript;sendMessage();};
  recognition.onerror=recognition.onend=()=>{isListening=false;mic.classList.remove('listening');mic.textContent=T[currentLanguage].listen;};
}
function setLanguage(lang){
  currentLanguage=lang;
  document.querySelectorAll('.lang button').forEach(b=>b.classList.toggle('active',b.dataset.lang===lang));
  const t=T[lang];
  document.getElementById('heroText').textContent=t.hero;
  document.getElementById('chatTitle').textContent=t.chat;
  input.placeholder=t.ph;send.textContent=t.send;resetBtn.title=t.reset;
  document.getElementById('hintText').textContent=t.hint;
  voiceToggle.textContent=autoVoice?t.voiceOn:t.voiceOff;
  if(mic&&!isListening)mic.textContent=t.listen;
  if(recognition)recognition.lang=voiceLanguages[lang];
}
function resetChat(){
  if(send.disabled)return;
  if(inflight)inflight.abort();
  history=[];messages.innerHTML='';
  addBubble('assistant',T[currentLanguage].welcome);
  input.focus();
}
async function sendMessage(preset){
  const text=(preset||input.value).trim();
  if(!text||send.disabled)return;
  addBubble('user',text);
  history.push({role:'user',content:text});
  input.value='';input.style.height='48px';
  send.disabled=true;send.textContent=T[currentLanguage].thinking;
  const wait=addBubble('assistant','');
  const dots=document.createElement('div');dots.className='typing';dots.innerHTML='<i></i><i></i><i></i>';
  wait.bubble.replaceWith(dots);
  const controller=new AbortController();inflight=controller;
  const timer=setTimeout(()=>controller.abort(),45000);
  let reply='';
  try{
    const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':decodeURIComponent(csrfToken)},body:JSON.stringify({message:text,history:history.slice(-6),language:currentLanguage}),signal:controller.signal});
    if(!res.ok){
      const data=await res.json().catch(()=>({}));
      throw new Error(data.error||'Erreur');
    }
    const reader=res.body.getReader();
    const dec=new TextDecoder();
    let buf='';
    let bubble=null;
    while(true){
      const {value,done}=await reader.read();
      if(done)break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\n');buf=lines.pop();
      for(const line of lines){
        if(!line.trim())continue;
        let ev;try{ev=JSON.parse(line);}catch{continue;}
        if(ev.error)throw new Error(ev.error);
        if(ev.d){
          if(!bubble){dots.replaceWith(wait.bubble);bubble=wait.bubble;}
          reply+=ev.d;
          bubble.textContent=reply;
          messages.scrollTop=messages.scrollHeight;
        }
      }
    }
    if(!bubble){dots.replaceWith(wait.bubble);wait.bubble.textContent=reply||'Aucune réponse.';}
    reply=reply.trim()||wait.bubble.textContent;
    addSpeak(wait.row,reply);
    history.push({role:'assistant',content:reply});
    history=history.slice(-6);
    if(autoVoice)playTTS(reply);
  }catch(err){
    const msg=err.name==='AbortError'?T[currentLanguage].timeout:(err.message||'Service indisponible.');
    if(dots.parentNode)dots.replaceWith(wait.bubble);
    wait.bubble.textContent=msg;
  }finally{
    clearTimeout(timer);inflight=null;send.disabled=false;send.textContent=T[currentLanguage].send;input.focus();
  }
}
document.querySelectorAll('.lang button').forEach(b=>b.onclick=()=>setLanguage(b.dataset.lang));
document.querySelectorAll('#chips button').forEach(b=>b.onclick=()=>sendMessage(b.dataset.question));
send.onclick=()=>sendMessage();
mic.onclick=()=>{if(!recognition)return;if(isListening)recognition.stop();else{recognition.lang=voiceLanguages[currentLanguage];try{recognition.start();}catch(e){}}};
resetBtn.onclick=resetChat;
voiceToggle.onclick=()=>{autoVoice=!autoVoice;voiceToggle.textContent=autoVoice?T[currentLanguage].voiceOn:T[currentLanguage].voiceOff;};
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}});
input.addEventListener('input',()=>{input.style.height='48px';input.style.height=Math.min(input.scrollHeight,120)+'px';});
setLanguage('fr');setupVoice();addBubble('assistant',T.fr.welcome);
</script>
</body>
</html>
"""


@app.get("/")
def home():
    nonce = secrets.token_urlsafe(16)
    request._csp_nonce = nonce
    response = make_response(render_template_string(HTML.replace("__CSP_NONCE__", nonce)))
    response.set_cookie(
        CSRF_COOKIE,
        issue_csrf(),
        httponly=False,
        secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https",
        samesite="Lax",
        max_age=60 * 60 * 12,
    )
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
 