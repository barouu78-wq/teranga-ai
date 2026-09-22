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
from flask import Flask, Response, jsonify, request, stream_with_context
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
    raise RuntimeError("OPENAI_API_KEY est introuvable. Vérifie ton fichier .env.")

client = OpenAI(api_key=API_KEY, timeout=35.0, max_retries=1)

MAX_MESSAGE_LENGTH = 2000
MAX_TTS_LENGTH = 1800
MAX_HISTORY_ITEMS = 6
MAX_HISTORY_CHARS = 6000
RATE_LIMIT = 12
RATE_WINDOW = 60
TTS_RATE_LIMIT = 6
CSRF_COOKIE = "teranga_csrf"
CSRF_HEADER = "X-CSRF-Token"

request_log = defaultdict(deque)
tts_request_log = defaultdict(deque)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_LANG = frozenset({"fr", "en", "wo"})

# Uniquement les sujets vraiment changeants — évite la recherche web sur chaque question.
WEB_HINTS = (
    "aujourd'hui", "aujourd’hui", "maintenant", "actuel", "actuelle",
    "actuels", "actuelles", "récent", "récente", "récentes",
    "horaire", "horaires", "ouvert", "ouverte",
    "disponible", "disponibilité", "réservation",
    "événement", "evenement", "météo", "meteo",
    "actualité", "actualités", "news", "today", "now",
    "current", "latest", "recent", "schedule", "hours",
    "open", "available", "availability", "booking", "weather", "event",
)

SYSTEM_PROMPT = """
Tu es Teranga AI, un assistant numérique moderne spécialisé dans le Sénégal.

Réponds dans la langue de l'utilisateur (français, anglais ou wolof).
Sois chaleureux, direct et concis. 4 à 8 phrases max, sauf demande contraire.
N'invente jamais un prix, une adresse, un téléphone, un horaire ou un nom d'établissement.
Si une info peut avoir changé, dis-le. Reste factuel et neutre en politique.
Ne conseille pas pour qui voter.
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
            content = sanitize_text(item.get("content", ""), 1400)
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
        if request.mimetype != "application/json":
            return jsonify({"error": "Type de contenu invalide."}), 415
        if not origin_allowed():
            return jsonify({"error": "Origine non autorisée."}), 403
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")
        if not cookie_token or not header_token:
            return jsonify({"error": "Jeton de sécurité manquant. Recharge la page."}), 403
        if not hmac.compare_digest(cookie_token, header_token) or not valid_token(cookie_token):
            return jsonify({"error": "Jeton de sécurité invalide. Recharge la page."}), 403
        return fn(*args, **kwargs)
    return wrapper


@app.after_request
def add_security_headers(response):
    nonce = getattr(request, "_csp_nonce", "")
    script_src = f"'self' 'nonce-{nonce}'" if nonce else "'self' 'unsafe-inline'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(), microphone=(self), payment=(), usb=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; script-src {script_src}; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; media-src 'self' blob:; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
        "fr": "Réponds en français naturel.",
        "en": "Reply in natural English.",
        "wo": "Réponds en wolof lorsque tu peux le faire correctement.",
    }[language]
    return {
        "instructions": SYSTEM_PROMPT + "\n" + language_instruction,
        "input_text": build_conversation(history, message),
        "use_web": should_use_web(message),
        "message": message,
    }, None


def model_kwargs(payload, stream):
    kwargs = {
        "model": MODEL,
        "instructions": payload["instructions"],
        "input": payload["input_text"],
        "max_output_tokens": 320,
        "stream": stream,
    }
    if payload["use_web"]:
        kwargs["tools"] = [{"type": "web_search"}]
    return kwargs


def event_delta(event):
    etype = getattr(event, "type", "") or ""
    if etype in {"response.output_text.delta", "response.text.delta"}:
        return getattr(event, "delta", "") or ""
    delta = getattr(event, "delta", None)
    if isinstance(delta, str) and etype.endswith(".delta"):
        return delta
    return ""


def complete_reply(payload):
    response = client.responses.create(**model_kwargs(payload, stream=False))
    return clean_answer(getattr(response, "output_text", "") or "")


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

    want_json = request.headers.get("X-Teranga-Mode", "").lower() == "json"

    if want_json:
        try:
            reply = complete_reply(payload)
            if not reply:
                reply = "Je n'ai pas réussi à répondre. Réessaie."
            return jsonify({"reply": reply})
        except Exception:
            app.logger.exception("Erreur JSON /chat")
            return jsonify({
                "error": "Désolé, le service est temporairement indisponible."
            }), 500

    def generate():
        yielded = False
        try:
            stream = client.responses.create(**model_kwargs(payload, stream=True))
            for event in stream:
                etype = getattr(event, "type", "") or ""
                if etype == "response.failed":
                    break
                delta = event_delta(event)
                if delta:
                    yielded = True
                    yield json.dumps({"d": delta}, ensure_ascii=False) + "\n"
                elif etype == "response.completed":
                    text = ""
                    resp = getattr(event, "response", None)
                    if resp is not None:
                        text = getattr(resp, "output_text", "") or ""
                    if text and not yielded:
                        yielded = True
                        yield json.dumps({"d": clean_answer(text)}, ensure_ascii=False) + "\n"
            if not yielded:
                reply = complete_reply(payload)
                if reply:
                    yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
            yield json.dumps({"done": True}) + "\n"
        except Exception:
            app.logger.exception("Erreur stream /chat")
            try:
                reply = complete_reply(payload)
                if reply:
                    yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
                    yield json.dumps({"done": True}) + "\n"
                    return
            except Exception:
                app.logger.exception("Erreur fallback /chat")
            yield json.dumps({
                "error": "Désolé, le service est temporairement indisponible. Réessaie."
            }, ensure_ascii=False) + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )


@app.post("/tts")
@require_json_post
def tts():
    ip = client_ip()
    if not allowed_request(ip, tts_request_log[ip], TTS_RATE_LIMIT, 60):
        return jsonify({"error": "Trop de demandes vocales. Réessaie dans un instant."}), 429
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
            instructions=f"Speak naturally and clearly in {language_name}.",
            response_format="mp3",
        )
        return Response(speech.content, mimetype="audio/mpeg", headers={"Cache-Control": "no-store"})
    except Exception:
        app.logger.exception("Erreur /tts")
        return jsonify({"error": "La génération vocale a échoué."}), 500


HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b1510">
<meta name="description" content="Teranga AI — assistant pour le Sénégal.">
<title>Teranga AI</title>
<style>
:root{
  --bg:#f4f1ea;--ink:#14211b;--mute:#6b746e;--line:rgba(20,33,27,.10);
  --card:#fffcf7;--soft:#e7efe8;--brand:#0c6b45;--brand-2:#083d29;
  --gold:#e2b34a;--user:#123528;--shadow:0 20px 50px rgba(20,33,27,.08);
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0c1210;--ink:#e8eee9;--mute:#9aa59e;--line:rgba(255,255,255,.08);
    --card:#151c19;--soft:#1c2621;--brand:#3dbe7e;--brand-2:#1a3d2d;
    --user:#1b3d2e;--shadow:0 20px 50px rgba(0,0,0,.28);
  }
}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{
  color:var(--ink);
  font:15px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;
  background:
    radial-gradient(900px 400px at 100% -20%,rgba(226,179,74,.18),transparent 50%),
    var(--bg);
}
body[data-theme="dark"]{
  --bg:#0c1210;--ink:#e8eee9;--mute:#9aa59e;--line:rgba(255,255,255,.08);
  --card:#151c19;--soft:#1c2621;--brand:#3dbe7e;--brand-2:#1a3d2d;
  --user:#1b3d2e;--shadow:0 20px 50px rgba(0,0,0,.28);
}
body[data-theme="light"]{
  --bg:#f4f1ea;--ink:#14211b;--mute:#6b746e;--line:rgba(20,33,27,.10);
  --card:#fffcf7;--soft:#e7efe8;--brand:#0c6b45;--brand-2:#083d29;
  --user:#123528;--shadow:0 20px 50px rgba(20,33,27,.08);
}
.app{min-height:100%;display:flex;flex-direction:column;max-width:760px;margin:auto}
header{
  position:sticky;top:0;z-index:20;
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:12px 16px calc(12px + env(safe-area-inset-top));
  background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:blur(16px);
  border-bottom:1px solid var(--line);
}
.brand{display:flex;gap:10px;align-items:center}
.mark{width:36px;height:36px;border-radius:12px;display:grid;place-items:center;
  background:linear-gradient(160deg,#147a4f,#07291d);color:#fff;font-size:17px}
.brand strong{display:block;font-size:14px;letter-spacing:-.03em}
.brand span{display:block;color:var(--mute);font-size:11px}
.tools{display:flex;gap:6px;align-items:center}
.seg{display:flex;padding:3px;border:1px solid var(--line);border-radius:999px;background:var(--card)}
.seg button,.icon{
  border:0;background:transparent;color:var(--mute);border-radius:999px;
  padding:6px 9px;font-weight:700;cursor:pointer
}
.seg button.on{background:var(--brand-2);color:#fff}
.icon{width:34px;height:34px;border:1px solid var(--line);background:var(--card)}
#messages{flex:1;overflow:auto;padding:18px 16px 8px}
.msg{margin:0 0 12px;display:flex;animation:in .16s ease}
.msg.user{justify-content:flex-end}
.bubble{
  max-width:min(88%,560px);padding:11px 13px;border-radius:18px;
  white-space:pre-wrap;word-break:break-word
}
.assistant .bubble{background:var(--soft);border-bottom-left-radius:6px}
.user .bubble{background:var(--user);color:#fff;border-bottom-right-radius:6px}
.speak{margin:6px 0 0;border:0;background:0;color:var(--brand);font-weight:750;font-size:12px;cursor:pointer}
.typing{display:flex;gap:5px;padding:13px 14px;width:fit-content;background:var(--soft);border-radius:16px}
.typing i{width:6px;height:6px;border-radius:50%;background:var(--mute);animation:b 1s infinite}
.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
@keyframes b{50%{opacity:.25;transform:translateY(-2px)}}
@keyframes in{from{opacity:0;transform:translateY(6px)}}
.dock{padding:8px 12px calc(12px + env(safe-area-inset-bottom));border-top:1px solid var(--line);background:var(--card)}
.chips{display:flex;gap:8px;overflow:auto;padding:2px 2px 10px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chips button{
  flex:none;border:1px solid var(--line);background:var(--bg);color:var(--ink);
  border-radius:999px;padding:8px 12px;font-size:13px;cursor:pointer
}
.row{display:grid;grid-template-columns:1fr auto auto;gap:7px;align-items:end}
textarea{
  width:100%;min-height:46px;max-height:120px;resize:none;border:1px solid var(--line);
  border-radius:16px;padding:12px;background:var(--bg);color:var(--ink);outline:0
}
textarea:focus{border-color:var(--brand)}
#mic,#send{height:46px;border:0;border-radius:15px;cursor:pointer;font-weight:800}
#mic{width:46px;background:#f3e3c4;color:#8a5a00}
#mic.listen{background:#c93636;color:#fff}
#send{padding:0 15px;background:var(--brand-2);color:#fff}
#send:disabled{opacity:.5}
.meta{display:flex;justify-content:space-between;gap:8px;margin-top:6px;color:var(--mute);font-size:11px}
.meta button{border:0;background:0;color:var(--brand);font-weight:750;cursor:pointer}
@media(max-width:640px){.row{grid-template-columns:1fr auto}#send{grid-column:1}#mic{grid-column:2}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style>
</head>
<body>
<div class="app">
<header>
  <div class="brand">
    <div class="mark">🌴</div>
    <div><strong>Teranga AI</strong><span id="sub">Assistant Sénégal</span></div>
  </div>
  <div class="tools">
    <div class="seg" id="langs">
      <button type="button" data-lang="fr" class="on">FR</button>
      <button type="button" data-lang="en">EN</button>
      <button type="button" data-lang="wo">WO</button>
    </div>
    <button class="icon" id="themeBtn" type="button" title="Thème">◐</button>
    <button class="icon" id="resetBtn" type="button" title="Nouveau">↺</button>
  </div>
</header>
<div id="messages"></div>
<div class="dock">
  <div class="chips" id="chips">
    <button type="button" data-q="Quel temps fait-il à Dakar aujourd'hui ?">Météo Dakar</button>
    <button type="button" data-q="Combien coûte un taxi de l'aéroport AIBD à Dakar ?">Taxi AIBD</button>
    <button type="button" data-q="Quels sont les endroits à visiter au Sénégal ?">À visiter</button>
    <button type="button" data-q="Quels plats sénégalais dois-je goûter ?">Cuisine</button>
  </div>
  <div class="row">
    <textarea id="input" maxlength="2000" placeholder="Pose ta question…"></textarea>
    <button id="mic" type="button">🎤</button>
    <button id="send" type="button">Envoyer</button>
  </div>
  <div class="meta">
    <span id="hint">Réponse en direct · recharge si le jeton expire</span>
    <button id="voiceToggle" type="button">Voix auto off</button>
  </div>
</div>
</div>
<script nonce="__CSP_NONCE__">
const $ = id => document.getElementById(id);
const messages=$('messages'), input=$('input'), send=$('send'), mic=$('mic');
const T={
fr:{sub:'Assistant Sénégal',ph:'Pose ta question…',send:'Envoyer',welcome:'Salut, je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',timeout:'Délai dépassé. Réessaie.',err:'Service indisponible.',vOn:'Voix auto on',vOff:'Voix auto off'},
en:{sub:'Senegal assistant',ph:'Ask a question…',send:'Send',welcome:'Hi, I am Teranga AI. What do you want to know about Senegal?',timeout:'Timed out. Try again.',err:'Service unavailable.',vOn:'Auto voice on',vOff:'Auto voice off'},
wo:{sub:'Assistant Senegaal',ph:'Laajal…',send:'Yónnee',welcome:'Salaam, maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',timeout:'Dafa yàgg. Jéemaatal.',err:'Service bañ na.',vOn:'Baat auto on',vOff:'Baat auto off'}
};
const voiceMap={fr:'fr-FR',en:'en-US',wo:'wo-SN'};
let lang='fr', history=[], rec=null, listening=false, audio=null, autoVoice=false, inflight=null;
function cookie(name){
  const m=document.cookie.match(new RegExp('(?:^|; )'+name+'=([^;]*)'));
  return m?decodeURIComponent(m[1]):'';
}
function headers(extra){
  return Object.assign({'Content-Type':'application/json','X-CSRF-Token':cookie('teranga_csrf')}, extra||{});
}
function addMsg(role,text){
  const row=document.createElement('div');
  row.className='msg '+role;
  const b=document.createElement('div');
  b.className='bubble';
  b.textContent=text;
  row.appendChild(b);
  messages.appendChild(row);
  messages.scrollTop=messages.scrollHeight;
  return {row,b};
}
function addSpeak(row,text){
  const btn=document.createElement('button');
  btn.className='speak';btn.type='button';btn.textContent='Écouter';
  btn.onclick=()=>speak(text,btn);
  row.appendChild(btn);
}
async function speak(text,btn){
  if(!text)return;
  if(audio){audio.pause();audio=null;}
  if(btn){btn.disabled=true;btn.textContent='…';}
  try{
    const res=await fetch('/tts',{method:'POST',headers:headers(),body:JSON.stringify({text,language:lang})});
    if(!res.ok)throw 0;
    const url=URL.createObjectURL(await res.blob());
    audio=new Audio(url);
    audio.onended=()=>{URL.revokeObjectURL(url);if(btn){btn.disabled=false;btn.textContent='Écouter';}};
    await audio.play();
  }catch(e){if(btn){btn.disabled=false;btn.textContent='Écouter';}}
}
function setLang(next){
  lang=next;
  document.querySelectorAll('#langs button').forEach(b=>b.classList.toggle('on',b.dataset.lang===next));
  const t=T[lang];
  $('sub').textContent=t.sub;input.placeholder=t.ph;send.textContent=t.send;
  $('voiceToggle').textContent=autoVoice?t.vOn:t.vOff;
  if(rec)rec.lang=voiceMap[lang];
}
function themeInit(){
  const saved=localStorage.getItem('teranga-theme');
  if(saved)document.body.dataset.theme=saved;
}
function reset(){
  if(send.disabled)return;
  if(inflight)inflight.abort();
  history=[];messages.innerHTML='';
  addMsg('assistant',T[lang].welcome);
}
function setupMic(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){mic.disabled=true;return;}
  rec=new SR();rec.continuous=false;rec.interimResults=false;rec.lang=voiceMap[lang];
  rec.onstart=()=>{listening=true;mic.classList.add('listen');};
  rec.onresult=e=>{input.value=e.results[0][0].transcript;ask();};
  rec.onend=rec.onerror=()=>{listening=false;mic.classList.remove('listen');};
}
async function readStream(res){
  if(!res.body)return '';
  const reader=res.body.getReader();const dec=new TextDecoder();
  let buf='', reply='';
  while(true){
    const {value,done}=await reader.read();
    if(done)break;
    buf+=dec.decode(value,{stream:true});
    const parts=buf.split('\n');buf=parts.pop();
    for(const line of parts){
      if(!line.trim())continue;
      let ev;try{ev=JSON.parse(line);}catch{continue;}
      if(ev.error)throw new Error(ev.error);
      if(ev.d)reply+=ev.d;
    }
  }
  if(buf.trim()){
    try{
      const ev=JSON.parse(buf);
      if(ev.error)throw new Error(ev.error);
      if(ev.d)reply+=ev.d;
    }catch(e){if(e.message&&!String(e.message).includes('JSON'))throw e;}
  }
  return reply;
}
async function ask(preset){
  const text=(preset||input.value).trim();
  if(!text||send.disabled)return;
  addMsg('user',text);
  history.push({role:'user',content:text});
  input.value='';input.style.height='46px';
  send.disabled=true;send.textContent='…';
  const wait=addMsg('assistant','');
  const dots=document.createElement('div');dots.className='typing';dots.innerHTML='<i></i><i></i><i></i>';
  wait.b.replaceWith(dots);
  const ctrl=new AbortController();inflight=ctrl;
  const kill=setTimeout(()=>ctrl.abort(),55000);
  const body=JSON.stringify({message:text,history:history.slice(-6),language:lang});
  let reply='';
  try{
    const res=await fetch('/chat',{method:'POST',headers:headers(),body,signal:ctrl.signal});
    if(!res.ok){
      const data=await res.json().catch(()=>({}));
      throw new Error(data.error||T[lang].err);
    }
    let live='';
    const reader=res.body.getReader();const dec=new TextDecoder();
    let buf='';
    let shown=false;
    const show=()=>{
      if(!shown){dots.replaceWith(wait.b);shown=true;}
      wait.b.textContent=live;
      messages.scrollTop=messages.scrollHeight;
    };
    while(true){
      const {value,done}=await reader.read();
      if(done)break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split('\n');buf=parts.pop();
      for(const line of parts){
        if(!line.trim())continue;
        let ev;try{ev=JSON.parse(line);}catch{continue;}
        if(ev.error)throw new Error(ev.error);
        if(ev.d){live+=ev.d;show();}
      }
    }
    if(buf.trim()){
      try{
        const ev=JSON.parse(buf);
        if(ev.error)throw new Error(ev.error);
        if(ev.d){live+=ev.d;show();}
      }catch(e){if(e.message&&!String(e).includes('JSON'))throw e;}
    }
    reply=live.trim();
    if(!reply){
      const res2=await fetch('/chat',{method:'POST',headers:headers({'X-Teranga-Mode':'json'}),body,signal:ctrl.signal});
      const data=await res2.json().catch(()=>({}));
      if(!res2.ok)throw new Error(data.error||T[lang].err);
      reply=(data.reply||'').trim();
      live=reply;show();
    }
    if(!shown){dots.replaceWith(wait.b);wait.b.textContent=reply||T[lang].err;}
    addSpeak(wait.row,reply);
    history.push({role:'assistant',content:reply});
    history=history.slice(-6);
    if(autoVoice&&reply)speak(reply);
  }catch(err){
    const msg=err.name==='AbortError'?T[lang].timeout:(err.message||T[lang].err);
    if(dots.parentNode)dots.replaceWith(wait.b);
    wait.b.textContent=msg;
  }finally{
    clearTimeout(kill);inflight=null;send.disabled=false;send.textContent=T[lang].send;input.focus();
  }
}
$('langs').onclick=e=>{const b=e.target.closest('button');if(b)setLang(b.dataset.lang);};
$('chips').onclick=e=>{const b=e.target.closest('button');if(b)ask(b.dataset.q);};
send.onclick=()=>ask();
mic.onclick=()=>{if(!rec)return;listening?rec.stop():rec.start();};
$('resetBtn').onclick=reset;
$('themeBtn').onclick=()=>{
  const next=document.body.dataset.theme==='dark'?'light':'dark';
  document.body.dataset.theme=next;localStorage.setItem('teranga-theme',next);
};
$('voiceToggle').onclick=()=>{autoVoice=!autoVoice;$('voiceToggle').textContent=autoVoice?T[lang].vOn:T[lang].vOff;};
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask();}});
input.addEventListener('input',()=>{input.style.height='46px';input.style.height=Math.min(input.scrollHeight,120)+'px';});
themeInit();setLang('fr');setupMic();addMsg('assistant',T.fr.welcome);
</script>
</body>
</html>
"""


@app.get("/")
def home():
    nonce = secrets.token_urlsafe(16)
    request._csp_nonce = nonce
    response = Response(HTML.replace("__CSP_NONCE__", nonce), mimetype="text/html")
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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5002")), debug=False)
