import hashlib
import hmac
import io
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from prompts import SYSTEM_PROMPT, WEB_HINTS

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, stream_with_context
from openai import OpenAI
from werkzeug.middleware.proxy_fix import ProxyFix

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
SITE_URL = os.getenv("SITE_URL", "https://teranga-ai-1.onrender.com").rstrip("/")
BASE_DIR = Path(__file__).resolve().parent
REDIS_URL = os.getenv("REDIS_URL", "").strip()
_OG_PNG = None
redis_client = None
if REDIS_URL:
    try:
        import redis as redis_lib
        redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        redis_client = None
if TRUST_PROXY:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY est introuvable. Vérifie ton fichier .env.")

client = OpenAI(api_key=API_KEY, timeout=50.0, max_retries=1)

MAX_MESSAGE_LENGTH = 2000
MAX_TTS_LENGTH = 1800
MAX_HISTORY_ITEMS = 12
MAX_HISTORY_CHARS = 10000
RATE_LIMIT = 16
RATE_WINDOW = 60
TTS_RATE_LIMIT = 8
RATE_LOCK = threading.Lock()
CSRF_COOKIE = "teranga_csrf"
CSRF_HEADER = "X-CSRF-Token"

request_log = defaultdict(deque)
tts_request_log = defaultdict(deque)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_LANG = frozenset({"fr", "en", "wo", "ff"})

def sanitize_text(text, max_len):
    text = CONTROL_CHARS.sub("", str(text or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()[:max_len]


def clean_answer(text):
    text = sanitize_text(text, 8000)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    text = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```", ""), text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)
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


def allowed_request(ip, log, limit, window, bucket="chat"):
    if redis_client is not None:
        try:
            key = f"teranga:rl:{bucket}:{ip}"
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, int(window))
            return count <= limit
        except Exception:
            app.logger.exception("Redis rate-limit, fallback mémoire")
    now = time.time()
    with RATE_LOCK:
        while log and now - log[0] > window:
            log.popleft()
        if len(log) >= limit:
            return False
        log.append(now)
        return True


def public_error(exc):
    text = f"{type(exc).__name__} {exc}".lower()
    if "timeout" in text or "timed out" in text:
        return "La réponse a pris trop de temps. Réessaie."
    if "429" in text or "rate" in text:
        return "Le service est très demandé. Réessaie dans un moment."
    if "401" in text or "403" in text or "api key" in text:
        return "Le service est temporairement mal configuré. Réessaie plus tard."
    return "Désolé, le service est temporairement indisponible. Réessaie."


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
        "ff": "Réponds en pulaar (fuuta tooro) lorsque tu peux le faire correctement. Si un mot manque, complète clairement en français.",
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
        "max_output_tokens": 700 if payload["use_web"] else 520,
        "stream": stream,
    }
    if payload["use_web"]:
        kwargs["tools"] = [{"type": "web_search"}]
    return kwargs


def _field(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_sources(*objs):
    found = []
    seen = set()

    def add(url, title=""):
        url = sanitize_text(url, 400)
        if not url.startswith(("http://", "https://")):
            return
        key = url.split("#", 1)[0].rstrip("/").lower()
        if key in seen or len(found) >= 5:
            return
        seen.add(key)
        host = urlparse(url).netloc.replace("www.", "").lower()
        if not host or host.endswith("openai.com") or host in {"localhost"}:
            return
        title = sanitize_text(title, 72) or host or "Source"
        found.append({"title": title, "url": url})

    def walk(node, depth=0):
        if node is None or depth > 8 or len(found) >= 5:
            return
        if isinstance(node, (list, tuple)):
            for item in node[:40]:
                walk(item, depth + 1)
            return
        url = _field(node, "url")
        title = _field(node, "title") or _field(node, "name") or ""
        atype = str(_field(node, "type") or "")
        if url and (
            "citation" in atype
            or atype in {"url_citation", "source"}
            or str(url).startswith("http")
        ):
            add(str(url), str(title or ""))
        for key in (
            "annotations", "output", "content", "response", "citation",
            "citations", "sources", "results", "action", "item",
        ):
            child = _field(node, key)
            if child is not None:
                walk(child, depth + 1)
        if depth < 2:
            dump = getattr(node, "model_dump", None)
            if callable(dump):
                try:
                    walk(dump(), depth + 1)
                except Exception:
                    pass

    for obj in objs:
        walk(obj)
    return found


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
    text = clean_answer(getattr(response, "output_text", "") or "")
    return text, extract_sources(response)


@app.post("/chat")
@require_json_post
def chat():
    ip = client_ip()
    if not allowed_request(ip, request_log[ip], RATE_LIMIT, RATE_WINDOW, "chat"):
        return jsonify({
            "error": "Trop de demandes. Attends quelques secondes puis réessaie."
        }), 429, {"Retry-After": "8"}

    payload, error = parse_chat_payload()
    if error:
        return error

    want_json = request.headers.get("X-Teranga-Mode", "").lower() == "json"

    if want_json:
        try:
            reply, sources = complete_reply(payload)
            if not reply:
                reply = "Je n'ai pas réussi à répondre. Réessaie."
            return jsonify({"reply": reply, "sources": sources})
        except Exception as exc:
            app.logger.exception("Erreur JSON /chat")
            return jsonify({"error": public_error(exc)}), 500

    def generate():
        yielded = False
        sources = []
        try:
            stream = client.responses.create(**model_kwargs(payload, stream=True))
            for event in stream:
                etype = getattr(event, "type", "") or ""
                if etype == "response.failed":
                    break
                if (
                    "annotation" in etype
                    or "web_search" in etype
                    or "output_item" in etype
                    or etype.endswith(".completed")
                ):
                    extra = extract_sources(event)
                    if extra:
                        sources = extra
                delta = event_delta(event)
                if delta:
                    yielded = True
                    yield json.dumps({"d": delta}, ensure_ascii=False) + "\n"
                elif etype == "response.completed":
                    text = ""
                    resp = getattr(event, "response", None)
                    if resp is not None:
                        text = getattr(resp, "output_text", "") or ""
                        sources = extract_sources(resp, event) or sources
                    if text and not yielded:
                        yielded = True
                        yield json.dumps({"d": clean_answer(text)}, ensure_ascii=False) + "\n"
            if not yielded:
                reply, sources = complete_reply(payload)
                if reply:
                    yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
            if sources:
                yield json.dumps({"s": sources}, ensure_ascii=False) + "\n"
            yield json.dumps({"done": True}) + "\n"
        except Exception as exc:
            app.logger.exception("Erreur stream /chat")
            try:
                reply, sources = complete_reply(payload)
                if reply:
                    yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
                    if sources:
                        yield json.dumps({"s": sources}, ensure_ascii=False) + "\n"
                    yield json.dumps({"done": True}) + "\n"
                    return
            except Exception as exc2:
                app.logger.exception("Erreur fallback /chat")
                exc = exc2
            yield json.dumps({"error": public_error(exc)}, ensure_ascii=False) + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )


@app.post("/tts")
@require_json_post
def tts():
    ip = client_ip()
    if not allowed_request(ip, tts_request_log[ip], TTS_RATE_LIMIT, 60, "tts"):
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
    language_name = {
        "fr": "French",
        "en": "English",
        "wo": "Wolof",
        "ff": "Pulaar, a Fulah language of northern Senegal",
    }[language]
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


ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect rx="14" width="64" height="64" fill="#1a3d2a"/>
<circle cx="44" cy="18" r="8" fill="#e2b34a"/>
<path d="M32 54V28M18 36c8-2 10-10 14-10s6 8 14 10" stroke="#f3e6c8" stroke-width="3" fill="none" stroke-linecap="round"/>
</svg>"""

OG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#f6efe3"/>
<circle cx="1080" cy="80" r="220" fill="#e2b34a" opacity=".45"/>
<rect x="80" y="160" rx="28" width="96" height="96" fill="#1a3d2a"/>
<text x="80" y="340" font-size="72" font-family="Georgia,serif" fill="#1a120c">Teranga AI</text>
<text x="80" y="410" font-size="32" font-family="Georgia,serif" fill="#7a6d5f">L’assistant du Sénégal · FR · EN · WO</text>
</svg>"""


@app.get("/icon.svg")
def icon_svg():
    return Response(ICON_SVG, mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/og.svg")
def og_svg():
    return Response(OG_SVG, mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


def build_og_png():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1200, 630), "#f6efe3")
    draw = ImageDraw.Draw(img)
    draw.ellipse((920, -140, 1340, 280), fill="#e2b34a")
    draw.rounded_rectangle((80, 150, 196, 266), 28, fill="#1a3d2a")
    draw.ellipse((148, 172, 180, 204), fill="#e2b34a")
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = title_font
    draw.text((80, 300), "Teranga AI", fill="#1a120c", font=title_font)
    draw.text((80, 400), "L'assistant du Senegal  ·  FR  EN  WO", fill="#7a6d5f", font=sub_font)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@app.get("/og.png")
def og_png():
    global _OG_PNG
    if _OG_PNG is None:
        try:
            _OG_PNG = build_og_png()
        except Exception:
            app.logger.exception("og.png")
            return og_svg()
    return Response(_OG_PNG, mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /chat\nDisallow: /tts\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(body, mimetype="text/plain", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/sitemap.xml")
def sitemap():
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{SITE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>"
        "</urlset>"
    )
    return Response(body, mimetype="application/xml", headers={"Cache-Control": "public, max-age=86400"})


def build_icon_png(size):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (size, size), "#1a3d2a")
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 5, fill="#1a3d2a")
    sun = size // 5
    draw.ellipse((size - pad - sun, pad, size - pad, pad + sun), fill="#e2b34a")
    trunk_w = max(4, size // 14)
    draw.rectangle((size // 2 - trunk_w // 2, size // 2, size // 2 + trunk_w // 2, size - pad), fill="#f3e6c8")
    draw.arc((pad, size // 3, size - pad, size - pad // 2), start=200, end=340, fill="#f3e6c8", width=max(3, size // 18))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@app.get("/icon-192.png")
def icon_192():
    return Response(build_icon_png(192), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/icon-512.png")
def icon_512():
    return Response(build_icon_png(512), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/sw.js")
def service_worker():
    body = """
self.addEventListener('install', event => {
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.pathname === '/chat' || url.pathname === '/tts') return;
  if (url.pathname === '/' ) return;
});
"""
    resp = Response(body.strip() + "\n", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.get("/manifest.webmanifest")
def manifest():
    return Response(
        json.dumps({
            "id": "/",
            "name": "Teranga AI",
            "short_name": "Teranga",
            "description": "Assistant du Sénégal en français, anglais et wolof.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait",
            "lang": "fr",
            "background_color": "#f6efe3",
            "theme_color": "#0a3d28",
            "categories": ["travel", "lifestyle", "utilities"],
            "icons": [
                {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
        }),
        mimetype="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/")
def home():
    nonce = secrets.token_urlsafe(16)
    request._csp_nonce = nonce
    page = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    response = Response(
        page.replace("__CSP_NONCE__", nonce).replace("__SITE_URL__", SITE_URL),
        mimetype="text/html",
    )
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
