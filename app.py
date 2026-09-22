import hashlib
import hmac
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

client = OpenAI(api_key=API_KEY, timeout=25.0, max_retries=1)

MAX_MESSAGE_LENGTH = 2000
MAX_TTS_LENGTH = 3500
MAX_HISTORY_ITEMS = 8
MAX_HISTORY_CHARS = 10000
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
            content = sanitize_text(item.get("content", ""), 2500)
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
    raw = secrets.token_urlsafe(24)
    return sign_token(raw)


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
    return jsonify({
        "status": "ok",
        "service": "teranga-ai",
        "model": MODEL
    })


@app.post("/chat")
@require_json_post
def chat():
    ip = client_ip()
    if not allowed_request(ip, request_log[ip], RATE_LIMIT, RATE_WINDOW):
        return jsonify({
            "error": "Trop de demandes. Attends quelques secondes puis réessaie."
        }), 429

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Requête invalide."}), 400

    message = sanitize_text(data.get("message", ""), MAX_MESSAGE_LENGTH)
    history = data.get("history", [])
    language = str(data.get("language", "fr")).lower()[:8]
    if language not in SAFE_LANG:
        language = "fr"

    if not isinstance(history, list):
        history = []
    if len(history) > MAX_HISTORY_ITEMS * 2:
        history = history[-MAX_HISTORY_ITEMS:]

    if not message:
        return jsonify({"error": "Écris un message avant d'envoyer."}), 400

    language_instruction = {
        "fr": "L'utilisateur a choisi le français. Réponds en français naturel.",
        "en": "The user selected English. Reply in natural English.",
        "wo": "L'utilisateur a choisi le wolof. Réponds en wolof lorsque tu peux le faire correctement.",
    }[language]

    final_instructions = SYSTEM_PROMPT + "\n\n" + language_instruction
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
        return jsonify({"reply": reply})
    except Exception:
        app.logger.exception("Erreur dans /chat")
        return jsonify({
            "error": (
                "Désolé, le service est temporairement indisponible. "
                "Réessaie dans quelques secondes."
            )
        }), 500


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
<meta name="theme-color" content="#064c30">
<meta name="description" content="Teranga AI — assistant intelligent dédié au Sénégal.">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>Teranga AI · Sénégal</title>
<style>
:root{
  --green:#0a7a4c;
  --green-deep:#053823;
  --green-mid:#0b8f59;
  --gold:#f4b942;
  --gold-2:#e8941a;
  --red:#ce1126;
  --cream:#f4f7f4;
  --ink:#102018;
  --muted:#5d7166;
  --line:rgba(16,48,32,.10);
  --card:rgba(255,255,255,.82);
  --soft:#e8f4ed;
  --shadow:0 24px 60px rgba(5,40,24,.14);
  --radius:28px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;
  color:var(--ink);
  font-family:ui-sans-serif,Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:
    radial-gradient(900px 420px at 100% -10%, rgba(244,185,66,.18), transparent 50%),
    radial-gradient(700px 380px at -10% 15%, rgba(10,122,76,.14), transparent 46%),
    linear-gradient(180deg,#f7faf7 0%, var(--cream) 100%);
  min-height:100vh;
}
body:before{
  content:"";
  position:fixed;inset:0 auto auto 0;width:100%;height:4px;z-index:40;
  background:linear-gradient(90deg,#0a7a4c 0 33%,#f4b942 33% 66%,#ce1126 66% 100%);
}
button,textarea{font:inherit}
header{
  position:sticky;top:0;z-index:20;
  background:rgba(247,250,247,.78);
  backdrop-filter:blur(18px) saturate(1.2);
  border-bottom:1px solid var(--line);
}
.nav{
  max-width:1080px;margin:auto;padding:14px 20px;
  display:flex;align-items:center;justify-content:space-between;gap:14px;
}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.logo{
  width:46px;height:46px;border-radius:16px;display:grid;place-items:center;
  background:
    linear-gradient(160deg,var(--green-mid),var(--green-deep) 70%),
    linear-gradient(45deg,transparent 60%, var(--gold));
  color:#fff;font-size:22px;flex:none;
  box-shadow:0 10px 24px rgba(10,122,76,.28);
}
.brand-title{font-weight:800;font-size:17px;letter-spacing:-.03em}
.brand-sub{font-size:12px;color:var(--muted);margin-top:2px}
.status-dot{
  display:inline-block;width:7px;height:7px;border-radius:50%;
  background:#1db954;margin-right:6px;box-shadow:0 0 0 3px rgba(29,185,84,.18);
}
.nav-actions{display:flex;align-items:center;gap:8px}
.lang{display:flex;gap:4px;background:rgba(255,255,255,.7);padding:4px;border-radius:999px;border:1px solid var(--line)}
.lang button{
  border:0;background:transparent;color:var(--green);
  border-radius:999px;padding:7px 11px;font-weight:750;cursor:pointer;
}
.lang button.active{background:var(--green-deep);color:#fff}
.reset-btn{
  border:1px solid var(--line);background:#fff;color:var(--muted);
  border-radius:999px;width:38px;height:38px;cursor:pointer;
}
.reset-btn:hover{color:var(--green-deep);border-color:#c9ddd2}
main{max-width:1080px;margin:auto;padding:24px 20px 72px}
.hero{
  position:relative;overflow:hidden;color:#fff;
  border-radius:32px;padding:40px 34px 34px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.08), transparent 40%),
    linear-gradient(145deg,#064c30 0%, #0a7a4c 58%, #d99216 140%);
  box-shadow:var(--shadow);
}
.hero h1{
  margin:14px 0 10px;font-size:clamp(34px,6vw,58px);
  line-height:.96;letter-spacing:-.05em;max-width:14ch;
}
.hero p{max-width:640px;margin:0;font-size:17px;line-height:1.55;opacity:.94}
.hero-badge{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);
  padding:7px 12px;border-radius:999px;font-size:12px;font-weight:750;
}
.hero-pills{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}
.hero-pills span{
  padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.16);font-size:12px;
}
.section{margin-top:28px}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:12px}
.section h2{font-size:22px;margin:0;letter-spacing:-.03em}
.section-note{font-size:12px;color:var(--muted)}
.quick{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.quick button{
  border:1px solid var(--line);background:var(--card);
  border-radius:20px;padding:16px;text-align:left;cursor:pointer;
  backdrop-filter:blur(10px);
  transition:transform .18s ease, box-shadow .18s ease;
}
.quick button:hover{transform:translateY(-3px);box-shadow:0 16px 30px rgba(8,40,24,.08)}
.quick .q-icon{font-size:22px;display:block;margin-bottom:8px}
.quick strong{display:block;font-size:14px}
.quick small{display:block;color:var(--muted);margin-top:4px}
.chat{
  margin-top:28px;background:rgba(255,255,255,.88);
  border:1px solid var(--line);border-radius:30px;box-shadow:var(--shadow);overflow:hidden;
}
.chat-head{
  padding:16px 20px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
}
.chat-title{font-weight:800}
.chat-status{font-size:12px;color:var(--green);font-weight:700}
#messages{min-height:280px;max-height:560px;overflow:auto;padding:20px}
.empty-state{text-align:center;padding:36px 16px;color:var(--muted)}
.empty-icon{
  width:62px;height:62px;margin:0 auto 12px;border-radius:22px;
  display:grid;place-items:center;background:var(--soft);font-size:26px;
}
.msg{display:flex;margin:12px 0;gap:9px;align-items:flex-end}
.msg.user{justify-content:flex-end}
.bubble{
  max-width:min(84%,680px);padding:13px 16px;border-radius:20px;
  line-height:1.55;white-space:pre-wrap;
}
.assistant .bubble{background:var(--soft);border-bottom-left-radius:8px}
.user .bubble{background:var(--green-deep);color:#fff;border-bottom-right-radius:8px}
.speak-button{
  display:block;margin:6px 0 0 4px;border:0;background:transparent;
  color:var(--green);cursor:pointer;font-size:13px;font-weight:750;
}
.composer{
  padding:12px;border-top:1px solid var(--line);background:#f8fbf9;
  display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:end;
}
textarea{
  width:100%;resize:none;min-height:54px;max-height:150px;
  border:1px solid var(--line);border-radius:18px;padding:14px 15px;
  background:#fff;color:var(--ink);outline:none;
}
textarea:focus{border-color:var(--green);box-shadow:0 0 0 4px rgba(10,122,76,.10)}
.voice-button,#send{height:54px;border:0;border-radius:17px;cursor:pointer;font-weight:800}
.voice-button{width:54px;background:#fff6e8;color:#b56a00;border:1px solid #f3d7a8;font-size:20px}
.voice-button.listening{background:#c93636;color:#fff;border-color:#c93636}
#send{padding:0 20px;background:var(--green-deep);color:#fff}
#send:disabled{opacity:.55;cursor:not-allowed}
.composer-hint{grid-column:1/-1;font-size:11px;color:var(--muted)}
.wake-hint{display:none;font-size:12px;color:var(--muted);padding:4px 8px}
.destinations{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.destination{
  border:1px solid var(--line);background:var(--card);border-radius:22px;padding:18px;
}
.destination strong{display:block;margin-bottom:6px}
.destination span{color:var(--muted);font-size:14px;line-height:1.45}
footer{text-align:center;padding:28px 18px 42px;color:var(--muted);font-size:12px}
@media(max-width:800px){
  .quick{grid-template-columns:repeat(2,1fr)}
  .destinations{grid-template-columns:1fr}
}
@media(max-width:560px){
  .nav{padding:10px 12px}
  main{padding:16px 12px 60px}
  .hero{padding:26px 20px;border-radius:24px}
  .composer{grid-template-columns:1fr auto}
  #send{grid-column:1/2}
  .voice-button{grid-column:2/3}
}
@media (prefers-reduced-motion: reduce){
  *{animation:none!important;transition:none!important}
}
</style>
</head>
<body>
<header>
  <div class="nav">
    <div class="brand">
      <div class="logo" aria-hidden="true">🌴</div>
      <div>
        <div class="brand-title">Teranga AI</div>
        <div class="brand-sub"><span class="status-dot"></span>Assistant Sénégal</div>
      </div>
    </div>
    <div class="nav-actions">
      <div class="lang" role="tablist" aria-label="Langue">
        <button type="button" data-lang="fr" class="active">FR</button>
        <button type="button" data-lang="en">EN</button>
        <button type="button" data-lang="wo">WO</button>
      </div>
      <button id="resetBtn" class="reset-btn" type="button" title="Nouvelle conversation">↺</button>
    </div>
  </div>
</header>
<main>
  <section class="hero">
    <span class="hero-badge"> pensé pour le Sénégal</span>
    <h1>Ton assistant,<br>version Teranga.</h1>
    <p id="heroText">Ton assistant intelligent pour le Sénégal : tourisme, transport, prix, culture, démarches et vie quotidienne.</p>
    <div class="hero-pills">
      <span>Rapide</span><span>Vocal</span><span>FR · EN · WO</span>
    </div>
  </section>
  <section class="section">
    <div class="section-head">
      <h2 id="quickTitle">Questions rapides</h2>
      <span class="section-note">Appuie pour demander</span>
    </div>
    <div class="quick">
      <button type="button" data-question="Quel temps fait-il à Dakar aujourd'hui ?">
        <span class="q-icon">🌤️</span><strong>Météo</strong><small>Dakar aujourd'hui</small>
      </button>
      <button type="button" data-question="Combien coûte un taxi de l'aéroport AIBD à Dakar ?">
        <span class="q-icon">🚕</span><strong>Taxi AIBD</strong><small>AIBD → Dakar</small>
      </button>
      <button type="button" data-question="Quels sont les endroits à visiter au Sénégal ?">
        <span class="q-icon">📍</span><strong>À visiter</strong><small>Destinations</small>
      </button>
      <button type="button" data-question="Quels plats sénégalais dois-je goûter ?">
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
      <textarea id="input" maxlength="2000" placeholder="Ex. Quel est le prix d'un taxi AIBD → Dakar ?" aria-label="Message"></textarea>
      <button id="mic" class="voice-button" type="button" title="Parler">🎤</button>
      <button id="send" type="button">Envoyer</button>
      <div class="composer-hint">La réponse peut être lue automatiquement à voix haute.</div>
    </div>
  </section>
  <section class="section">
    <div class="section-head">
      <h2>Quelques idées</h2>
      <span class="section-note">Découvrir le Sénégal</span>
    </div>
    <div class="destinations">
      <div class="destination"><strong>🏙️ Dakar</strong><span>Culture, marchés, restaurants et vie urbaine.</span></div>
      <div class="destination"><strong>🏝️ Île de Gorée</strong><span>Histoire, patrimoine et découverte culturelle.</span></div>
      <div class="destination"><strong>🌊 Saly & Petite Côte</strong><span>Plages, détente et activités touristiques.</span></div>
    </div>
  </section>
</main>
<footer>
  Teranga AI — Un assistant numérique dédié au Sénégal<br>
  <small>La voix entendue est générée par une IA.</small>
</footer>
<script nonce="__CSP_NONCE__">
const input = document.getElementById('input');
const send = document.getElementById('send');
const mic = document.getElementById('mic');
const messages = document.getElementById('messages');
const resetBtn = document.getElementById('resetBtn');
const emptyState = document.getElementById('emptyState');
const csrfToken = document.cookie.split('; ').find(row => row.startsWith('teranga_csrf='))?.split('=')[1] || '';

let history = [];
let currentLanguage = 'fr';
let recognition = null;
let isListening = false;
let currentAudio = null;

const translations = {
  fr: {
    hero: 'Ton assistant intelligent pour le Sénégal : tourisme, transport, prix, culture, démarches et vie quotidienne.',
    quick: 'Questions rapides',
    chat: 'Pose ta question à Teranga AI',
    placeholder: "Ex. Quel est le prix d'un taxi AIBD → Dakar ?",
    send: 'Envoyer',
    welcome: 'Bonjour 👋 Je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',
    listen: '🎤',
    listening: '🔴',
    reset: 'Nouvelle conversation',
    wake: 'Le serveur se réveille, ça peut prendre jusqu’à 30 secondes...',
    thinking: 'Réflexion…',
    timeout: 'Ça prend trop de temps. Réessaie dans un instant.'
  },
  en: {
    hero: 'Your intelligent assistant for Senegal: tourism, transport, prices, culture, practical procedures and daily life.',
    quick: 'Quick questions',
    chat: 'Ask Teranga AI',
    placeholder: 'Example: How much is a taxi from AIBD to Dakar?',
    send: 'Send',
    welcome: 'Hello 👋 I am Teranga AI. What would you like to know about Senegal?',
    listen: '🎤',
    listening: '🔴',
    reset: 'New conversation',
    wake: 'The server is waking up, this can take up to 30 seconds...',
    thinking: 'Thinking…',
    timeout: 'This is taking too long. Please try again in a moment.'
  },
  wo: {
    hero: 'Sa xam-xam bu bees ci Senegaal: tukki, transport, njëg, aada ak dund gu bees.',
    quick: 'Laaj yu gaaw',
    chat: 'Laajal Teranga AI',
    placeholder: 'Misaal: Ñaata la taxi AIBD ba Dakar?',
    send: 'Yónnee',
    welcome: 'Salaam 👋 Maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',
    listen: '🎤',
    listening: '🔴',
    reset: 'Waxtaan bu bees',
    wake: 'Server bi mu ngi yeew, mën na yàgg ba 30 second...',
    thinking: 'Xalaat…',
    timeout: 'Dafa yàgg lool. Jéemaatal.'
  }
};

const voiceLanguages = { fr: 'fr-FR', en: 'en-US', wo: 'wo-SN' };

function addMessage(role, text) {
  if (emptyState) emptyState.remove();
  const row = document.createElement('div');
  row.className = 'msg ' + role;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  row.appendChild(bubble);
  if (role === 'assistant') {
    const speakButton = document.createElement('button');
    speakButton.type = 'button';
    speakButton.className = 'speak-button';
    speakButton.textContent = '🔊 Écouter';
    speakButton.addEventListener('click', () => playTTS(text, speakButton));
    row.appendChild(speakButton);
  }
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

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
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': decodeURIComponent(csrfToken)
      },
      body: JSON.stringify({ text, language: currentLanguage })
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
  }
}

function setupVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    mic.disabled = true;
    mic.title = 'La reconnaissance vocale n’est pas disponible sur ce navigateur.';
    return;
  }
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = voiceLanguages[currentLanguage];
  recognition.onstart = () => {
    isListening = true;
    mic.classList.add('listening');
    mic.textContent = translations[currentLanguage].listening;
  };
  recognition.onresult = (event) => {
    input.value = event.results[0][0].transcript;
    mic.classList.remove('listening');
    mic.textContent = translations[currentLanguage].listen;
    isListening = false;
    sendMessage(null, true);
  };
  recognition.onerror = recognition.onend = () => {
    isListening = false;
    mic.classList.remove('listening');
    mic.textContent = translations[currentLanguage].listen;
  };
}

function startVoice() {
  if (!recognition) return;
  if (isListening) {
    recognition.stop();
    return;
  }
  recognition.lang = voiceLanguages[currentLanguage] || 'fr-FR';
  try { recognition.start(); } catch (error) { isListening = false; }
}

function resetChat() {
  if (send.disabled) return;
  history = [];
  messages.innerHTML = '';
  addMessage('assistant', translations[currentLanguage].welcome);
  input.focus();
}

function setLanguage(lang) {
  currentLanguage = lang;
  document.querySelectorAll('.lang button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  const t = translations[lang];
  document.getElementById('heroText').textContent = t.hero;
  document.getElementById('quickTitle').textContent = t.quick;
  document.getElementById('chatTitle').textContent = t.chat;
  document.getElementById('input').placeholder = t.placeholder;
  document.getElementById('send').textContent = t.send;
  if (mic && !isListening) mic.textContent = t.listen;
  resetBtn.title = t.reset;
  if (recognition) recognition.lang = voiceLanguages[lang] || 'fr-FR';
}

async function sendMessage(textFromButton = null) {
  const text = (textFromButton || input.value).trim();
  if (!text || send.disabled) return;
  addMessage('user', text);
  history.push({ role: 'user', content: text });
  input.value = '';
  send.disabled = true;
  send.textContent = translations[currentLanguage].thinking;
  const wakeHint = document.createElement('div');
  wakeHint.className = 'wake-hint';
  wakeHint.textContent = translations[currentLanguage].wake;
  messages.appendChild(wakeHint);
  const controller = new AbortController();
  const abortTimer = setTimeout(() => controller.abort(), 60000);
  const wakeTimer = setTimeout(() => { wakeHint.style.display = 'block'; }, 8000);
  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': decodeURIComponent(csrfToken)
      },
      body: JSON.stringify({
        message: text,
        history: history.slice(-8),
        language: currentLanguage
      }),
      signal: controller.signal
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Erreur');
    const reply = data.reply || 'Aucune réponse.';
    addMessage('assistant', reply);
    setTimeout(() => playTTS(reply), 0);
    history.push({ role: 'assistant', content: reply });
    history = history.slice(-8);
  } catch (error) {
    const message = error.name === 'AbortError'
      ? translations[currentLanguage].timeout
      : (error.message || 'Service temporairement indisponible.');
    addMessage('assistant', message);
  } finally {
    clearTimeout(abortTimer);
    clearTimeout(wakeTimer);
    wakeHint.remove();
    send.disabled = false;
    send.textContent = translations[currentLanguage].send;
    input.focus();
  }
}

document.querySelectorAll('.lang button').forEach(btn => {
  btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
});
document.querySelectorAll('.quick button').forEach(btn => {
  btn.addEventListener('click', () => sendMessage(btn.dataset.question));
});
send.addEventListener('click', () => sendMessage());
mic.addEventListener('click', () => startVoice());
resetBtn.addEventListener('click', () => resetChat());
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});
setLanguage('fr');
setupVoice();
addMessage('assistant', translations.fr.welcome);
</script>
</body>
</html>
"""


@app.get("/")
def home():
    nonce = secrets.token_urlsafe(16)
    request._csp_nonce = nonce
    html = HTML.replace("__CSP_NONCE__", nonce)
    response = make_response(render_template_string(html))
    token = issue_csrf()
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,
        secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https",
        samesite="Lax",
        max_age=60 * 60 * 12,
    )
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
