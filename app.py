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
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

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
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
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
    "visa", "ferry", "gorée", "goree", "cfa", "change", "taux",
    "sim", "orange money", "week-end", "weekend", "ce soir", "demain",
    "manger", "restaurant", "resto", "où manger", "ou manger",
    "eat", "dining", "food court", "dibi", "thiéboudienne", "thieb",
    "spécialité", "specialite", "spécialités", "mafé", "maafe", "yassa",
    "thiéré", "thiere", "fonio", "konkoé", "ndambé", "saloum",
    "ouvert ce soir", "meilleur resto", "où se trouve", "ou se trouve",
    "prix", "tarif", "tarifs", "coût", "cout", "combien coûte", "combien coute",
    "price", "prices", "fare", "fares", "cost", "how much",
    "itinéraire", "itineraire", "trajet", "transport", "bus", "brt", "ter",
    "taxi", "péage", "peage", "car rapide", "dem dikk", "tata",
    "billet", "billets", "ticket", "tickets", "vol", "flight", "airline",
    "aéroport", "airport", "formalités", "formalites", "document", "documents",
    "ambassade", "consulat", "immigration", "vaccin", "vaccination",
    "banque", "bank", "guichet", "atm", "distributeur", "mobile money",
    "wave", "free money", "expresso money", "yas", "free", "orange",
    "concert", "festival", "match", "football", "salon", "foire",
    "programme", "program", "calendrier", "calendar", "fermé", "ferme", "closed",
    "urgent", "alerte", "grève", "greve", "perturbation", "incident",
)

SYSTEM_PROMPT = """
Tu es Teranga AI, un assistant numérique moderne spécialisé dans le Sénégal.

Réponds dans la langue de l'utilisateur : français, anglais, wolof ou pulaar (fuuta tooro).
Sois chaleureux, direct et très court. 2 ou 3 phrases courtes, sauf si on te demande plus.
Jamais plus de 70 mots. Une idée par phrase. Pas de liste de quartiers.
Finis toujours tes phrases. Ne coupe pas au milieu d'un quartier ou d'un plat.
N'utilise jamais de markdown : pas d'astérisques, pas de gras, pas de titres #, pas de listes à puces.
N'invente jamais un téléphone, un horaire exact ou un prix figé.
Si tu n'es pas sûr, dis-le clairement plutôt que d'inventer.
Pour un plat ou un lieu : région ou quartier + spécialité + un repère. Pas de liste vague.
Si une info peut avoir changé, dis-le. Reste factuel et neutre en politique.
Ne conseille pas pour qui voter.
Si tu utilises le web, ne colle pas de listes d'URLs dans le texte : les sources s'affichent à part.

Géographie utile :
Le Sénégal a 14 régions : Dakar, Thiès, Diourbel, Fatick, Kaolack, Kaffrine, Tambacounda, Kédougou, Kolda, Sédhiou, Ziguinchor, Saint-Louis, Louga, Matam.
Grandes villes : Dakar, Pikine, Guédiawaye, Rufisque, Thiès, Mbour, Touba, Kaolack, Saint-Louis, Ziguinchor, Kolda, Tambacounda, Richard-Toll, Louga.
Cap-Vert : Dakar et sa petite côte. Nord : Saint-Louis, Louga, Matam (fuuta). Centre : Thiès, Diourbel, Touba, Kaolack. Sud : Casamance (Ziguinchor, Sédhiou, Kolda), séparée par la Gambie. Est : Tambacounda, Kédougou.
Quartiers de Dakar pour s'orienter : Plateau, Médina, Gueule Tapée, Fann, Point E, Mermoz, Sacré-Cœur, Almadies, Ngor, Ouakam, Yoff, Parcelles Assainies, Liberté, Grand Dakar, Sicap, Pikine, Guédiawaye, Rufisque, Diamniadio. Aéroport : AIBD à Diass, pas à Dakar-ville.
Nature et visites : île de Gorée, île de Niodior / Saloum, Lac Rose, Petite Côte (Saly, Somone, Nianing), Saint-Louis et Parc Djoudj, Casamance et Cap Skirring, Niokolo-Koba, pays Bassari à Kédougou.

Où manger : donne toujours la région ou le quartier et un repère (plage, marché, artère), pas seulement le plat.
Si on te demande un resto précis, situe-le par quartier. Si tu n'es pas sûr du nom, décris la zone et dis de vérifier sur place.

Spécialités régionales (plats + où les chercher) :
Dakar et Cap-Vert : ceebu jën / thiéboudienne (plat national, poisson et riz au rouge), yassa poulet ou poisson, mafé à l'arachide, soupe kandja / supukanja, pastels et fataya. Médina, Kermel et Plateau pour la cuisine de maison ; Soumbédioune, Ouakam, Ngor et Yoff pour le poisson grillé et les dibiteries ; Almadies pour les restos de plage.
Petite Côte (Thiès, Mbour, Saly, Somone, Joal) : poisson braisé, thiof, crevettes, calmars, yassa de mer. Autour des plages et des campements.
Sine-Saloum (Fatick, Foundiougne, Ndangane, islands) : huîtres du Saloum, arches, yett (cymbium), poisson séché-salé, riz au poisson. Aux campements et villages de lagune.
Kaolack et bassin arachidier : mafé, riz à l'huile, couscous de mil, arachide partout. Marchés de Kaolack.
Diourbel et Touba : café Touba, ndambé (haricots), plats simples de mil et d'arachide autour des gares routières et du marché.
Saint-Louis, Louga et Fuuta (Matam, Podor, Richard-Toll) : thiéré / couscous de mil, lakh et laax (mil et lait caillé), fowru, poisson du fleuve, viande braisée. Sur l'île de Saint-Louis et dans les concessions du Fuuta.
Casamance (Ziguinchor, Sédhiou, Kolda, Cap Skirring) : konkoé, sauces à l'huile de palme, fruits de mer, brochets et thiof grillés à la côte, mangues et anacarde, riz local. Cap Skirring et villages autour de Ziguinchor.
Est (Tambacounda, Kédougou, pays Bassari) : fonio, mil, sauces aux feuilles, viande de brousse ou mouton selon la saison, miel. Cuisine de campement et de village, plus rare en resto touristique.
Boissons : bissap, ginger, ditakh, bouye (pain de singe), café Touba. Desserts / goûter : thiakry, ngalakh à la saison de l'arachide.
Quand on te demande les spécialités d'une région, cite 3 ou 4 plats typiques et dis où on les mange (maison, marché, plage, campement), sans inventer une enseigne.

Culture et lieux à connaître, en 1 phrase utile :
Gorée : ancien comptoir et Maison des Esclaves. Touba : ville mouride et grande mosquée. Saint-Louis : ancienne capitale, île classée. Lac Rose / Retba : lac salé rose selon la saison. Monument de la Renaissance : Mamelles, Ouakam. Niokolo-Koba et Djoudj : parcs nationaux. Petite Côte : Saly, Somone, Joal-Fadiouth (cimetière aux coquillages). Casamance : Ziguinchor, Cap Skirring, forêts et fleuve.
Si on te demande un lieu ou un plat connu, ajoute un détail concret (quartier, fleuve, marché, saison) et reste court.
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


PHOTO_TOPICS = (
    ("monument de la renaissance", "Monument de la Renaissance africaine"),
    ("renaissance africaine", "Monument de la Renaissance africaine"),
    ("maison des esclaves", "Maison des Esclaves"),
    ("cap skirring", "Cap Skirring"),
    ("île de gorée", "Île de Gorée"),
    ("ile de goree", "Île de Gorée"),
    ("saint-louis", "Saint-Louis (Sénégal)"),
    ("saint louis", "Saint-Louis (Sénégal)"),
    ("niokolo-koba", "Parc national du Niokolo-Koba"),
    ("niokolo koba", "Parc national du Niokolo-Koba"),
    ("djoudj", "Parc national des oiseaux du Djoudj"),
    ("joal-fadiouth", "Joal-Fadiouth"),
    ("fadiouth", "Joal-Fadiouth"),
    ("joal", "Joal-Fadiouth"),
    ("thiéboudienne", "Thiéboudienne"),
    ("thieboudienne", "Thiéboudienne"),
    ("ceebu jen", "Thiéboudienne"),
    ("ceebu jën", "Thiéboudienne"),
    ("café touba", "Café Touba"),
    ("cafe touba", "Café Touba"),
    ("lac rose", "Lac Retba"),
    ("lac retba", "Lac Retba"),
    ("richard-toll", "Richard-Toll"),
    ("richard toll", "Richard-Toll"),
    ("grande mosquée de touba", "Grande Mosquée de Touba"),
    ("mosquée de touba", "Grande Mosquée de Touba"),
    ("casamance", "Casamance"),
    ("somone", "La Somone"),
    ("yassa", "Yassa"),
    ("bissap", "Bissap"),
    ("mafé", "Mafé"),
    ("maafe", "Mafé"),
    ("diamniadio", "Diamniadio"),
    ("guédiawaye", "Guédiawaye"),
    ("guediawaye", "Guédiawaye"),
    ("tambacounda", "Tambacounda"),
    ("ziguinchor", "Ziguinchor"),
    ("kedougou", "Kédougou"),
    ("kédougou", "Kédougou"),
    ("kaffrine", "Kaffrine"),
    ("sédhiou", "Sédhiou"),
    ("sedhiou", "Sédhiou"),
    ("rufisque", "Rufisque"),
    ("kaolack", "Kaolack"),
    ("diourbel", "Diourbel"),
    ("gorée", "Île de Gorée"),
    ("goree", "Île de Gorée"),
    ("mbour", "M'Bour"),
    ("m'bour", "M'Bour"),
    ("touba", "Touba (Sénégal)"),
    ("thiès", "Thiès"),
    ("thies", "Thiès"),
    ("kolda", "Kolda"),
    ("matam", "Matam"),
    ("louga", "Louga"),
    ("fatick", "Fatick"),
    ("podor", "Podor"),
    ("saly", "Saly Portudal"),
    ("pikine", "Pikine"),
    ("dakar", "Dakar"),
    ("ndar", "Saint-Louis (Sénégal)"),
)


def topic_wikipedia_titles(message, limit=2):
    lowered = message.lower()
    found, seen = [], set()
    for key, title in PHOTO_TOPICS:
        if key in lowered and title not in seen:
            seen.add(title)
            found.append(title)
            if len(found) >= limit:
                break
    return found


def wiki_summary(lang, title):
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + quote(title)
    req = Request(url, headers={"User-Agent": "TerangaAI/1.0 (https://teranga-ai-1.onrender.com)"})
    with urlopen(req, timeout=2) as resp:
        return json.loads(resp.read().decode("utf-8"))


def usable_wiki_image(src):
    src = str(src or "").split("?", 1)[0]
    if not src.startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/")):
        return ""
    lowered = src.lower()
    if "flag_of" in lowered or "coat_of_arms" in lowered or lowered.endswith(".svg.png"):
        return ""
    return src


_IMAGE_CACHE = {}


def fetch_city_image(title):
    if not title:
        return None
    if title in _IMAGE_CACHE:
        return _IMAGE_CACHE[title]
    english = title.replace(" (Sénégal)", "").replace(" (Senegal)", "")
    found = None
    for lang, page in (("fr", title), ("en", english)):
        try:
            data = wiki_summary(lang, page)
        except Exception:
            continue
        src = usable_wiki_image((data.get("thumbnail") or {}).get("source") or "")
        if not src:
            src = usable_wiki_image((data.get("originalimage") or {}).get("source") or "")
        if not src:
            continue
        found = {
            "url": src,
            "alt": sanitize_text(data.get("title") or title, 80),
            "credit": "Wikimédia",
        }
        break
    _IMAGE_CACHE[title] = found
    return found


def fetch_topic_images(message):
    photos = []
    for title in topic_wikipedia_titles(message, 2):
        photo = fetch_city_image(title)
        if photo:
            photos.append(photo)
    return photos or None


MAP_PLACES = (
    ("aibd", "Aéroport Blaise Diagne Diass Sénégal", "Aéroport AIBD"),
    ("aéroport", "Aéroport Blaise Diagne Diass Sénégal", "Aéroport AIBD"),
    ("maison des esclaves", "Maison des Esclaves Gorée Sénégal", "Maison des Esclaves"),
    ("île de gorée", "Île de Gorée Sénégal", "Île de Gorée"),
    ("ile de goree", "Île de Gorée Sénégal", "Île de Gorée"),
    ("gorée", "Île de Gorée Sénégal", "Île de Gorée"),
    ("goree", "Île de Gorée Sénégal", "Île de Gorée"),
    ("lac rose", "Lac Retba Sénégal", "Lac Rose"),
    ("lac retba", "Lac Retba Sénégal", "Lac Rose"),
    ("cap skirring", "Cap Skirring Sénégal", "Cap Skirring"),
    ("saint-louis", "Saint-Louis Sénégal", "Saint-Louis"),
    ("saint louis", "Saint-Louis Sénégal", "Saint-Louis"),
    ("monument de la renaissance", "Monument de la Renaissance africaine Dakar", "Monument de la Renaissance"),
    ("joal", "Joal-Fadiouth Sénégal", "Joal-Fadiouth"),
    ("fadiouth", "Joal-Fadiouth Sénégal", "Joal-Fadiouth"),
    ("touba", "Grande Mosquée de Touba Sénégal", "Touba"),
    ("ziguinchor", "Ziguinchor Sénégal", "Ziguinchor"),
    ("saly", "Saly Portudal Sénégal", "Saly"),
    ("thiès", "Thiès Sénégal", "Thiès"),
    ("thies", "Thiès Sénégal", "Thiès"),
    ("kaolack", "Kaolack Sénégal", "Kaolack"),
    ("mbour", "M'Bour Sénégal", "M'Bour"),
    ("somone", "Somone Sénégal", "Somone"),
    ("popenguine", "Popenguine Sénégal", "Popenguine"),
    ("toubab dialaw", "Toubab Dialaw Sénégal", "Toubab Dialaw"),
    ("fatick", "Fatick Sénégal", "Fatick"),
    ("louga", "Louga Sénégal", "Louga"),
    ("matam", "Matam Sénégal", "Matam"),
    ("tambacounda", "Tambacounda Sénégal", "Tambacounda"),
    ("kédougou", "Kédougou Sénégal", "Kédougou"),
    ("kedougou", "Kédougou Sénégal", "Kédougou"),
    ("kolda", "Kolda Sénégal", "Kolda"),
    ("sédhiou", "Sédhiou Sénégal", "Sédhiou"),
    ("sedhiou", "Sédhiou Sénégal", "Sédhiou"),
    ("diamniadio", "Diamniadio Sénégal", "Diamniadio"),
    ("pointe sarène", "Pointe Sarène Sénégal", "Pointe Sarène"),
    ("pointe sarene", "Pointe Sarène Sénégal", "Pointe Sarène"),
    ("dakar", "Dakar Sénégal", "Dakar"),
)


def lookup_map(message):
    lowered = message.lower()
    for key, query, label in MAP_PLACES:
        if key in lowered:
            q = quote(query)
            return {
                "label": label,
                "url": "https://www.google.com/maps/search/?api=1&query=" + q,
                "embed": "https://maps.google.com/maps?q=" + q + "&hl=fr&z=14&output=embed",
            }
    return None


def should_use_web(message):
    lowered = message.lower()
    if any(term in lowered for term in WEB_HINTS):
        return True
    # Questions that explicitly ask for a current/verified fact should use web search.
    current_markers = (
        "vérifie", "verifie", "confirme", "à jour", "a jour",
        "exactement", "en ce moment", "pour aujourd'hui", "pour demain",
        "latest", "current", "right now", "as of", "verify", "check",
    )
    return any(term in lowered for term in current_markers)


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
    # ProxyFix valide déjà le proxy de confiance et normalise remote_addr.
    # Ne pas relire X-Forwarded-For directement : il peut être falsifié par un client.
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
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://upload.wikimedia.org https://thumb.wikimedia.org https://commons.wikimedia.org; "
        "connect-src 'self'; media-src 'self' blob:; object-src 'none'; "
        "frame-src https://www.google.com https://maps.google.com; "
        "child-src https://www.google.com https://maps.google.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    cached = {
        "/icon.svg", "/og.svg", "/og.png", "/icon-192.png", "/icon-512.png",
        "/robots.txt", "/sitemap.xml", "/manifest.webmanifest",
    }
    if request.path in cached:
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        response.headers["Cache-Control"] = "no-store"
    if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers.pop("Server", None)
    return response


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "teranga-ai",
        "model": MODEL,
        "model_configured": bool(MODEL),
        "web_search": True,
        "redis_rate_limit": redis_client is not None,
        "site_url": SITE_URL,
    })


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
        "max_output_tokens": 280 if payload["use_web"] else 220,
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
    image = fetch_topic_images(payload.get("message", ""))
    return text, extract_sources(response), image, lookup_map(payload.get("message", ""))


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
            reply, sources, image, maps = complete_reply(payload)
            if not reply:
                reply = "Je n'ai pas réussi à répondre. Réessaie."
            return jsonify({"reply": reply, "sources": sources, "image": image, "map": maps})
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
                reply, sources, image, maps = complete_reply(payload)
                if reply:
                    yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
            else:
                image = fetch_topic_images(payload.get("message", ""))
                maps = lookup_map(payload.get("message", ""))
            if sources:
                yield json.dumps({"s": sources}, ensure_ascii=False) + "\n"
            if image:
                yield json.dumps({"img": image}, ensure_ascii=False) + "\n"
            if maps:
                yield json.dumps({"map": maps}, ensure_ascii=False) + "\n"
            yield json.dumps({"done": True}) + "\n"
        except Exception as exc:
            app.logger.exception("Erreur stream /chat")
            # Après le début du stream, ne jamais générer une seconde réponse complète.
            if not yielded:
                try:
                    reply, sources, image, maps = complete_reply(payload)
                    if reply:
                        yield json.dumps({"d": reply}, ensure_ascii=False) + "\n"
                        if sources:
                            yield json.dumps({"s": sources}, ensure_ascii=False) + "\n"
                        if image:
                            yield json.dumps({"img": image}, ensure_ascii=False) + "\n"
                        if maps:
                            yield json.dumps({"map": maps}, ensure_ascii=False) + "\n"
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


HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b0907" id="themeColor">
<meta name="description" content="Teranga AI, l’assistant du Sénégal. Météo Dakar, taxi AIBD, ferry Gorée, visa, cuisine, SIM et Orange Money — en français, anglais et wolof.">
<meta name="keywords" content="Teranga AI, assistant Sénégal, météo Dakar, taxi AIBD, Gorée, visa Sénégal, wolof, Orange Money">
<meta name="robots" content="index,follow">
<link rel="canonical" href="__SITE_URL__/">
<meta property="og:site_name" content="Teranga AI">
<meta property="og:title" content="Teranga AI — l’assistant du Sénégal">
<meta property="og:description" content="Pose une question sur le Sénégal. Réponses claires en français, anglais et wolof.">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_SN">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:url" content="__SITE_URL__/">
<meta property="og:image" content="__SITE_URL__/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Teranga AI — l’assistant du Sénégal">
<meta name="twitter:description" content="Météo, trajets, visa, cuisine — en français, anglais et wolof.">
<meta name="twitter:image" content="__SITE_URL__/og.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Teranga">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icon-192.png">
<title>Teranga AI — assistant Sénégal en français, anglais et wolof</title>
<link rel="icon" href="/icon.svg">
<script type="application/ld+json" nonce="__CSP_NONCE__">{"@context":"https://schema.org","@type":"WebApplication","name":"Teranga AI","url":"__SITE_URL__/","applicationCategory":"TravelApplication","operatingSystem":"Web","inLanguage":["fr","en","wo"],"description":"Assistant numérique pour le Sénégal : météo, transport, visa, cuisine, SIM.","offers":{"@type":"Offer","price":"0","priceCurrency":"XOF"}}</script>
<style>
:root{
  --sand:#0b0907;--ink:#f6efe3;--mute:#b8a48c;--line:rgba(226,179,74,.16);
  --card:rgba(22,18,14,.92);--soft:#171310;--brand:#e2b34a;--brand-2:#c9962e;
  --gold:#e8c36a;--terracotta:#e07a4a;--user:#2a2114;--shadow:0 24px 60px rgba(0,0,0,.45);
  --glow:rgba(232,195,106,.18);
}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
html{color-scheme:dark}
body{
  color:var(--ink);
  font:15px/1.5 "Segoe UI",ui-sans-serif,system-ui,-apple-system,sans-serif;
  background:
    radial-gradient(900px 420px at 110% -10%,var(--glow),transparent 55%),
    radial-gradient(700px 380px at -10% 110%,rgba(15,106,67,.16),transparent 50%),
    var(--sand);
  overflow:hidden;
  text-rendering:optimizeSpeed;
}
body[data-theme="dark"]{
  --sand:#0b0907;--ink:#f6efe3;--mute:#b8a48c;--line:rgba(226,179,74,.16);
  --card:rgba(22,18,14,.92);--soft:#171310;--brand:#e2b34a;--brand-2:#c9962e;
  --gold:#e8c36a;--terracotta:#e07a4a;--user:#2a2114;--shadow:0 24px 60px rgba(0,0,0,.45);
  --glow:rgba(232,195,106,.18);
}
body[data-theme="light"]{
  --sand:#f6efe3;--ink:#1a120c;--mute:#7a6d5f;--line:rgba(26,18,12,.10);
  --card:rgba(255,251,244,.82);--soft:#efe4d2;--brand:#0f6a43;--brand-2:#0a3d28;
  --gold:#d9a441;--terracotta:#c45c2a;--user:#1c3328;--shadow:0 24px 60px rgba(26,18,12,.12);
  --glow:rgba(217,164,65,.28);
}
.sky{
  pointer-events:none;position:fixed;inset:0;overflow:hidden;z-index:0;contain:strict;
}
.sun{
  position:absolute;right:-40px;top:-50px;width:220px;height:220px;border-radius:50%;
  background:radial-gradient(circle at 40% 40%,#ffe7a3,#e2b34a 45%,transparent 70%);
  opacity:.45;
}
.baobab{
  position:absolute;left:-20px;bottom:-30px;width:280px;height:280px;opacity:.07;
  background:
    radial-gradient(circle at 50% 28%,var(--ink) 18px,transparent 19px),
    linear-gradient(var(--ink),var(--ink)) 50% 40%/8px 58% no-repeat;
}
.app{position:relative;z-index:1;min-height:100%;height:var(--vvh,100%);display:flex;flex-direction:column;max-width:820px;margin:auto;contain:layout}
header{
  position:sticky;top:0;z-index:20;
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:14px 18px calc(12px + env(safe-area-inset-top));
  background:color-mix(in srgb,var(--sand) 88%,transparent);
  border-bottom:1px solid var(--line);
  contain:layout style;
}
.brand{display:flex;gap:10px;align-items:center;min-width:0;flex:0 1 auto}
.mark{
  width:42px;height:42px;border-radius:14px;display:grid;place-items:center;
  background:
    radial-gradient(circle at 70% 28%,#f6d889 0 7px,transparent 8px),
    linear-gradient(165deg,#1a5c3b,#072318);
  box-shadow:0 8px 20px rgba(10,61,40,.28);
}
.mark svg{width:24px;height:24px}
.brand strong{display:block;font-size:15px;letter-spacing:-.04em;white-space:nowrap}
.brand em{font-style:normal;color:var(--gold)}
.brand span{display:flex;align-items:center;gap:6px;color:var(--mute);font-size:11px}
.dot{width:7px;height:7px;border-radius:50%;background:#3dbe7e;box-shadow:0 0 0 4px rgba(61,190,126,.15)}
.tools{display:flex;gap:6px;align-items:center}
.seg{display:flex;padding:3px;border:1px solid var(--line);border-radius:999px;background:var(--card)}
.seg button,.icon{
  border:0;background:transparent;color:var(--mute);border-radius:999px;
  padding:6px 8px;font-weight:750;cursor:pointer
}
.seg button.on{background:var(--gold);color:#1a1208}
.icon{width:36px;height:36px;border:1px solid var(--line);background:var(--card);display:grid;place-items:center}
.icon svg{width:16px;height:16px}
#stage{flex:1;min-height:0;overflow:auto;padding:8px 16px 12px;contain:layout paint;overflow-anchor:none;-webkit-overflow-scrolling:touch;display:flex;flex-direction:column}
#messages{margin-top:auto;padding-top:8px}
.hero{
  margin:18px 0 8px;padding:22px 20px 18px;border-radius:28px;
  background:var(--card);
  border:1px solid var(--line);box-shadow:var(--shadow);
  contain:content;
}
.hero.is-hidden{display:none}
.hero h1{margin:0 0 8px;font-size:28px;letter-spacing:-.05em;line-height:1.1;color:var(--gold)}
.hero p{margin:0 0 16px;color:var(--mute);max-width:42ch}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.card{
  text-align:center;border:1px solid var(--line);background:color-mix(in srgb,var(--sand) 70%,transparent);
  border-radius:18px;padding:12px 8px 10px;cursor:pointer;color:inherit
}
.card .ico{width:26px;height:26px;margin:0 auto 8px;color:var(--gold);display:grid;place-items:center}
.card .ico svg{width:24px;height:24px}
.card b{display:block;font-size:12px;font-weight:750}
.card span{display:none}
.card:hover{border-color:var(--gold)}
.tabbar{
  display:grid;grid-template-columns:repeat(4,1fr);gap:2px;
  padding:6px 6px calc(8px + env(safe-area-inset-bottom));
  border-top:1px solid var(--line);
  background:color-mix(in srgb,var(--sand) 94%,transparent);
}
.tabbar button{
  border:0;background:transparent;color:var(--mute);font-size:10px;font-weight:750;
  padding:6px 2px;cursor:pointer
}
.tabbar button.on{color:var(--gold)}
.tabbar svg{display:block;margin:0 auto 3px;width:18px;height:18px}
.msg{margin:0 0 14px;display:flex;gap:8px;align-items:flex-end;contain:content;content-visibility:auto;contain-intrinsic-size:auto 72px}
.msg.is-new{animation:in .18s ease}
.msg.user{justify-content:flex-end}
.avatar{
  flex:none;width:28px;height:28px;border-radius:10px;display:grid;place-items:center;
  background:linear-gradient(160deg,#1a5c3b,#072318);color:#f6e7c2;font-size:13px
}
.user .avatar{display:none}
.col{max-width:min(86%,580px)}
.bubble{
  padding:12px 14px;border-radius:20px;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere
}
.bubble.live{contain:content}
.assistant .bubble{background:var(--soft);border-bottom-left-radius:7px}
.user .bubble{background:linear-gradient(180deg,#3a2c14,#22180c);color:#f8edd4;border:1px solid rgba(232,195,106,.25);border-bottom-right-radius:7px}
.acts{display:flex;gap:4px;margin-top:6px;opacity:.0;transition:.15s}
.assistant:hover .acts,.assistant:focus-within .acts{opacity:1}
.acts button{
  border:0;background:transparent;color:var(--mute);font-weight:700;font-size:11px;
  padding:4px 7px;border-radius:999px;cursor:pointer
}
.acts button:hover{background:var(--card);color:var(--brand)}
.sources{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;align-items:center}
.sources b{font-size:10px;color:var(--mute);font-weight:750;letter-spacing:.04em;text-transform:uppercase}
.sources a{
  max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:11px;color:var(--brand-2);text-decoration:none;
  border:1px solid var(--line);background:var(--card);border-radius:999px;padding:4px 9px
}
.sources a:hover{border-color:var(--gold)}
.city-pic{margin:8px 0 2px;border-radius:16px;overflow:hidden;border:1px solid var(--line);background:var(--card);max-width:280px}
.city-pic img{display:block;width:100%;height:158px;object-fit:cover}
.city-pic small{display:block;padding:6px 10px;color:var(--mute);font-size:11px}
.city-map{margin:8px 0 2px;border-radius:16px;overflow:hidden;border:1px solid var(--line);background:var(--card);max-width:280px}
.city-map iframe{display:block;width:100%;height:170px;border:0}
.city-map a{display:block;padding:8px 10px;color:var(--brand-2);font-size:12px;font-weight:750;text-decoration:none}
.typing{display:flex;gap:5px;padding:14px 16px;width:fit-content;background:var(--soft);border-radius:18px}
.typing i{width:6px;height:6px;border-radius:50%;background:var(--mute);animation:b 1s infinite}
.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
.cursor{display:inline-block;width:7px;height:1em;background:var(--gold);margin-left:2px;vertical-align:-2px;animation:b .8s infinite}
@keyframes b{50%{opacity:.25;transform:translateY(-2px)}}
@keyframes in{from{opacity:0;transform:translateY(8px)}}
.dock{
  padding:10px 14px calc(14px + env(safe-area-inset-bottom));
  background:color-mix(in srgb,var(--sand) 92%,transparent);
  contain:layout style;
}
.composer{
  border:1px solid var(--line);background:var(--card);border-radius:24px;
  padding:8px 8px 8px 14px;box-shadow:var(--shadow)
}
body.has-chat .chips,body.has-chat #hero{display:none}
.chips{display:flex;gap:8px;overflow:auto;padding:0 2px 10px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chips button{
  flex:none;border:1px solid var(--line);background:var(--card);color:var(--ink);
  border-radius:999px;padding:7px 12px;font-size:12px;cursor:pointer
}
.row{display:grid;grid-template-columns:1fr auto auto;gap:7px;align-items:end}
textarea{
  width:100%;min-height:46px;max-height:130px;resize:none;border:0;
  padding:10px 4px 8px 0;background:transparent;color:var(--ink);outline:0;font:inherit
}
#mic,#send{height:44px;border:0;border-radius:16px;cursor:pointer;font-weight:800}
#mic{width:44px;background:color-mix(in srgb,var(--gold) 28%,var(--card));color:#7a4a00}
#mic.listen{background:#c93636;color:#fff}
#send{padding:0 16px;background:linear-gradient(180deg,#e8c36a,#c9962e);color:#1a1208}
#send:disabled{opacity:.5}
.meta{display:flex;justify-content:space-between;gap:8px;margin-top:8px;color:var(--mute);font-size:11px;padding:0 6px}
.meta button{border:0;background:0;color:var(--brand);font-weight:750;cursor:pointer}
.spread{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.spread a,.spread button{
  border:1px solid var(--line);background:var(--sand);color:var(--ink);
  border-radius:999px;padding:8px 12px;font-size:13px;font-weight:750;cursor:pointer;text-decoration:none
}
.spread .wa{background:#128C7E;border-color:#128C7E;color:#fff}
.spread .install{background:linear-gradient(180deg,#e8c36a,#c9962e);border-color:#c9962e;color:#1a1208}
.spread .install[hidden]{display:none}
.seo{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
.foot{
  display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;
  padding:6px 6px 0;color:var(--mute);font-size:11px
}
.foot button,.foot a{border:0;background:0;color:var(--brand);font-weight:750;cursor:pointer;text-decoration:none}
#count{font-variant-numeric:tabular-nums}
@media(max-width:680px){
  header{padding:10px 12px calc(8px + env(safe-area-inset-top));gap:6px}
  .brand span#sub,.brand .dot{display:none}
  .brand span{display:none}
  .mark{width:34px;height:34px;border-radius:12px}
  .seg button{padding:5px 6px;font-size:11px}
  .icon{width:32px;height:32px}
  .hero{margin:10px 0;padding:16px 14px}
  .hero h1{font-size:22px}
  .cards{grid-template-columns:repeat(3,1fr)}
  .row{grid-template-columns:1fr auto auto}
  #send,#mic{grid-column:auto;width:auto}
  #send{min-width:92px}
  .acts{opacity:1}
  .dock{padding:8px 10px calc(10px + env(safe-area-inset-bottom))}
  .meta{flex-wrap:wrap}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

</style>

</head>
<body data-theme="dark">
<div class="sky" aria-hidden="true"><div class="sun"></div><div class="baobab"></div></div>
<div class="app">
<header>
  <div class="brand">
    <div class="mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none"><path d="M12 21V9M5 13c3-.8 4.2-4 7-4s4 3.2 7 4" stroke="#f6e7c2" stroke-width="1.8" stroke-linecap="round"/><circle cx="17" cy="6" r="2.2" fill="#e2b34a"/></svg>
    </div>
    <div>
      <strong>Teranga <em>AI</em></strong>
      <span><i class="dot"></i> <span id="sub">Assistant Sénégal</span></span>
    </div>
  </div>
  <div class="tools">
    <div class="seg" id="langs">
      <button type="button" data-lang="fr" class="on">FR</button>
      <button type="button" data-lang="en">EN</button>
      <button type="button" data-lang="wo">WO</button>
      <button type="button" data-lang="ff">PU</button>
    </div>
    <button class="icon" id="themeBtn" type="button" title="Thème" aria-label="Thème">
      <svg viewBox="0 0 24 24" fill="none"><path d="M12 3v2M12 19v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3 12h2M19 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4M8 12a4 4 0 1 0 8 0 4 4 0 0 0-8 0Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
    </button>
    <button class="icon" id="shareAppBtn" type="button" title="Partager" aria-label="Partager">
      <svg viewBox="0 0 24 24" fill="none"><path d="M15 8a3 3 0 1 0-2.8-4H12a3 3 0 0 0 .2 4L8.5 12M15 16l-4.7-4M8.5 12A3 3 0 1 0 6 17.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
    <button class="icon" id="resetBtn" type="button" title="Nouveau" aria-label="Nouveau chat">
      <svg viewBox="0 0 24 24" fill="none"><path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
  </div>
</header>
<div id="stage">
  <div id="hero" class="hero">
    <h1 id="heroTitle">L’hospitalité, en quelques questions.</h1>
    <p id="heroText">Météo, trajets, plats, plages, marchés — Teranga t’oriente sans inventer les détails qui bougent.</p>
    <div class="cards" id="cards"></div>
    <div class="spread">
      <a class="wa" id="waShare" target="_blank" rel="noopener noreferrer" href="#">WhatsApp</a>
      <button type="button" class="install" id="installBtn" hidden>Installer l’app</button>
      <button type="button" id="copyLink">Copier le lien</button>
    </div>
  </div>
  <section class="seo">
    <h2>Assistant Sénégal</h2>
    <p>Teranga AI aide habitants, diaspora et voyageurs : géographie des 14 régions, où manger à Dakar par quartier, météo, taxi AIBD, ferry Gorée, visa. L’interface parle français, anglais, wolof et pulaar.</p>
  </section>
  <div id="messages"></div>
</div>
<div class="dock">
  <div class="chips" id="chips"></div>
  <div class="composer">
    <div class="row">
      <textarea id="input" maxlength="2000" placeholder="Pose ta question…" rows="1"></textarea>
      <button id="mic" type="button" title="Parler" aria-label="Parler">🎤</button>
      <button id="send" type="button">Envoyer</button>
    </div>
  </div>
  <div class="meta">
    <span id="hint">Réponse en direct</span>
    <span id="count">0 / 2000</span>
    <button id="voiceToggle" type="button">Voix auto off</button>
  </div>
</div>
<nav class="tabbar" id="tabbar" aria-label="Navigation">
  <button type="button" data-tab="home" class="on"><svg viewBox="0 0 24 24" fill="none"><path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" stroke="currentColor" stroke-width="1.7"/></svg>Accueil</button>
  <button type="button" data-tab="discover"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/><path d="m14.5 9.5-2 6-2-2-2-2 6-2Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>Découvrir</button>
  <button type="button" data-tab="chat"><svg viewBox="0 0 24 24" fill="none"><path d="M5 18.5 6.2 15A8 8 0 1 1 9 19.6L5 18.5Z" stroke="currentColor" stroke-width="1.7"/></svg>Converser</button>
  <button type="button" data-tab="profile"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="3.2" stroke="currentColor" stroke-width="1.7"/><path d="M5.5 19c1.3-3 3.6-4.5 6.5-4.5s5.2 1.5 6.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>Profil</button>
</nav>
</div>
<script nonce="__CSP_NONCE__">
const $ = id => document.getElementById(id);
const messages=$('messages'), input=$('input'), send=$('send'), mic=$('mic'), stage=$('stage'), hero=$('hero');
const reduceMotion=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
const T={
fr:{
  sub:'Assistant Sénégal',ph:'Pose ta question…',send:'Envoyer',
  welcome:'Salut, je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',
  timeout:'Délai dépassé. Réessaie.',err:'Service indisponible.',
  vOn:'Voix auto on',vOff:'Voix auto off',listen:'Écouter',copy:'Copier',copied:'Copié',
  share:'Partager',stop:'Arrêter',retry:'Réessayer',resetAsk:'Effacer la conversation ?',
  sources:'Sources',copyLink:'Copier le lien',linkCopied:'Lien copié',
  shareText:'Teranga AI — l’assistant du Sénégal (français, anglais, wolof). Météo, taxi, visa, cuisine :',
  install:'Installer l’app',navHome:'Accueil',navDiscover:'Découvrir',navChat:'Converser',navProfile:'Profil',
  heroTitle:'L’hospitalité, en quelques questions.',
  heroText:'Météo, trajets, plats, plages, marchés — Teranga t’oriente sans inventer les détails qui bougent.',
  hint:'Réponse en direct · Entrée pour envoyer',
  hintTouch:'Réponse en direct',
  cards:[
    {q:"Quel temps fait-il à Dakar aujourd'hui ?",t:'Météo Dakar',d:'Ciel, chaleur et vent du jour'},
    {q:"Parle-moi de l'île de Gorée et de la Maison des Esclaves.",t:'Gorée',d:'Histoire et photo'},
    {q:"Raconte brièvement l'histoire de Dakar et montre la ville.",t:'Histoire Dakar',d:'Ville, origine, photo'},
    {q:"Quelles sont les spécialités culinaires de chaque région du Sénégal ?",t:'Spécialités',d:'Plats du Nord, Centre, Casamance'},
    {q:"Où manger à Dakar selon le quartier : Plateau, Médina, Almadies, Ngor, Ouakam ?",t:'Où manger',d:'Quartier, plage ou marché'},
    {q:"Présente la géographie du Sénégal : régions, grandes villes et Casamance.",t:'Régions',d:'14 régions et grandes villes'}
  ]
},
en:{
  sub:'Senegal assistant',ph:'Ask a question…',send:'Send',
  welcome:'Hi, I am Teranga AI. What do you want to know about Senegal?',
  timeout:'Timed out. Try again.',err:'Service unavailable.',
  vOn:'Auto voice on',vOff:'Auto voice off',listen:'Listen',copy:'Copy',copied:'Copied',
  share:'Share',stop:'Stop',retry:'Retry',resetAsk:'Clear the conversation?',
  sources:'Sources',copyLink:'Copy link',linkCopied:'Link copied',
  shareText:'Teranga AI — Senegal assistant (French, English, Wolof). Weather, taxi, visa, food:',
  install:'Install app',navHome:'Home',navDiscover:'Discover',navChat:'Chat',navProfile:'Profile',
  heroTitle:'Hospitality, in a few questions.',
  heroText:'Weather, rides, food, beaches, markets — Teranga guides you without inventing shifting details.',
  hint:'Live answers · Enter to send',
  hintTouch:'Live answers',
  cards:[
    {q:'What is the weather like in Dakar today?',t:'Dakar weather',d:'Sky, heat and wind today'},
    {q:'Tell me about Goree Island and the House of Slaves.',t:'Goree',d:'History and photo'},
    {q:'Briefly tell the history of Dakar and show the city.',t:'Dakar history',d:'City, origin, photo'},
    {q:'What are the regional food specialties across Senegal?',t:'Specialties',d:'Dishes from North, Center, Casamance'},
    {q:'Where should I eat in Dakar by area: Plateau, Medina, Almadies, Ngor, Ouakam?',t:'Where to eat',d:'Neighborhood, beach or market'},
    {q:'Explain the geography of Senegal: regions, main cities and Casamance.',t:'Regions',d:'14 regions and main cities'}
  ]
},
wo:{
  sub:'Assistant Senegaal',ph:'Laajal…',send:'Yónnee',
  welcome:'Salaam, maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',
  timeout:'Dafa yàgg. Jéemaatal.',err:'Service bañ na.',
  vOn:'Baat auto on',vOff:'Baat auto off',listen:'Dégg',copy:'Koppi',copied:'Koppi na',
  share:'Séddoo',stop:'Taxal',retry:'Jéemaatal',resetAsk:'Dindi waxtaan wi?',
  sources:'Téere',copyLink:'Koppi lien',linkCopied:'Lien koppi na',
  shareText:'Teranga AI — assistant Senegaal (français, anglais, wolof). Tàkk-tàkk, taksi, visa, ñam :',
  install:'Yebal app bi',navHome:'Accueil',navDiscover:'Xam',navChat:'Waxtaan',navProfile:'Profil',
  heroTitle:'Teranga, ci laaj yu néew.',
  heroText:'Taw, taksi, ñam, teex ak marché — Teranga dina la wonal te du sos lu mëna soppi.',
  hint:'Tontu ci kaw · Enter ngir yónnee',
  hintTouch:'Tontu ci kaw',
  cards:[
    {q:"Lan mooy tàkk-tàkk Dakaar tey?",t:'Tàkk-tàkk',d:'Asamaan, tàngaay ak ngelaw'},
    {q:"Nettali Gorée ak Maison des Esclaves.",t:'Gorée',d:'Tàriix ak nataal'},
    {q:"Nettali sama ndakaru Dakaar, wone dëkk bi.",t:'Tàriix Dakaar',d:'Dëkk, tàriix, nataal'},
    {q:'Ban ñam aju ci réegion yu Senegaal?',t:'Ñam réegion',d:'Nord, centre, Kasamans'},
    {q:'Fan laa wara lekk ci Dakaar: Plateau, Medina, Almadies, Ngor, Ouakam?',t:'Lekk',d:'Quartier, teex walla marché'},
    {q:'Wan nga ma géographie Senegaal: régions, dëkk yu mag ak Kasamans.',t:'Réegion',d:'14 régions ak dëkk yu mag'}
  ]
},
ff:{
  sub:'Ballal Senegaal',ph:'Naamndu…',send:'Neldu',
  welcome:'Jam tan, miin woni Teranga AI. Hol ko njiɗɗaa anndude e Senegaal?',
  timeout:'Sahaa booyii. Fuɗɗit.',err:'Sarwiis jaɓaani.',
  vOn:'Sawtu auto on',vOff:'Sawtu auto off',listen:'Heɗo',copy:'Natal',copied:'Natalaa',
  share:'Lollin',stop:'Dartin',retry:'Fuɗɗit',resetAsk:'Momtu yeewtere nde?',
  sources:'Iwdiiji',copyLink:'Natal jokkol',linkCopied:'Jokkol nataa',
  shareText:'Teranga AI — ballal Senegaal (farayse, english, wolof, pulaar).',
  install:'Aaf app',navHome:'Jaɓɓorgo',navDiscover:'Yiytu',navChat:'Yeewtere',navProfile:'Profil',
  heroTitle:'Teranga, e naamne seeɗa.',
  heroText:'Kaanawol, taksi, ñaamdu, geec, luumooji — Teranga holata, wonaa fefindoo.',
  hint:'Jaabawol e sahaa. Sawtu nde ɓadiima pulaar.',
  hintTouch:'Jaabawol e sahaa. Sawtu ɓadiima.',
  cards:[
    {q:'Hol kaanawol Dakaar hannde?',t:'Kaanawol',d:'Dakaar hannde'},
    {q:'Haal Gorée e Maison des Esclaves.',t:'Gorée',d:'Aada e natal'},
    {q:'Hol ñaamdu Dakaar e diiwe: Plateau, Medina, Almadies, Ngor, Ouakam?',t:'Ñaamdu',d:'Diiwal, geec walla luumo'},
    {q:'Hol geografi Senegaal: diiwe, gure mawɗe e Kasamans?',t:'Diiwe',d:'Diiwe 14 e gure'},
    {q:'Haal Aada Dakaar e hollu wuro ngo.',t:'Aada Dakaar',d:'Wuro, aada, natal'},
    {q:'Hol ñaamdu diiwe Senegaal kala?',t:'Ñaamdu diiwe',d:'Fuuta, hakkunde, Kasamans'}
  ]
}
};
const voiceMap={fr:'fr-FR',en:'en-US',wo:'wo-SN',ff:'fr-FR'};
let lang=localStorage.getItem('teranga-lang')||'fr';
if(!T[lang])lang='fr';
let history=[], rec=null, listening=false, audio=null, autoVoice=localStorage.getItem('teranga-voice')==='1', inflight=null;
let persistTimer=0, scrollRaf=0, stickToBottom=true, lastLang='';
function cleanReply(text){
  return String(text||'')
    .replace(/```[\s\S]*?```/g,m=>m.replace(/```/g,''))
    .replace(/`([^`]+)`/g,'$1')
    .replace(/\*\*([^*]+)\*\*/g,'$1')
    .replace(/__([^_]+)__/g,'$1')
    .replace(/(^|\s)\*([^*\n]+)\*(?=\s|$|[.,;!?])/g,'$1$2')
    .replace(/\*\*/g,'')
    .replace(/__/g,'')
    .replace(/^#{1,6}\s+/gm,'')
    .replace(/^\s*[-*•]\s+/gm,'')
    .replace(/\n{3,}/g,'\n\n')
    .trim();
}
function cookie(name){
  const m=document.cookie.match(new RegExp('(?:^|; )'+name+'=([^;]*)'));
  return m?decodeURIComponent(m[1]):'';
}
function headers(extra){
  return Object.assign({'Content-Type':'application/json','X-CSRF-Token':cookie('teranga_csrf')}, extra||{});
}
function isTouch(){return window.matchMedia('(pointer:coarse)').matches;}
function setChatMode(on){
  document.body.classList.toggle('has-chat',on);
  document.querySelectorAll('#tabbar button').forEach(b=>b.classList.toggle('on',b.dataset.tab===(on?'chat':'home')));
  hero.classList.toggle('is-hidden',on);
}
function hideHero(){setChatMode(true);}
function showHero(){setChatMode(false);}
function applyThemeColor(){
  const dark=document.body.dataset.theme==='dark'||(!document.body.dataset.theme&&matchMedia('(prefers-color-scheme:dark)').matches);
  $('themeColor').content=dark?'#0b0907':'#f6efe3';
}
function sharePayload(){
  const url=location.origin+'/';
  return {title:'Teranga AI',text:T[lang].shareText+' '+url,url};
}
function bindShare(){
  const p=sharePayload();
  const wa=$('waShare');
  if(wa)wa.href='https://wa.me/?text='+encodeURIComponent(p.text);
  const copy=$('copyLink');
  if(copy)copy.textContent=T[lang].copyLink;
  const inst=$('installBtn');
  if(inst)inst.textContent=T[lang].install;
}
async function shareApp(){
  const p=sharePayload();
  try{
    if(navigator.share){await navigator.share(p);return;}
  }catch(e){if(e&&e.name==='AbortError')return;}
  window.open('https://wa.me/?text='+encodeURIComponent(p.text),'_blank','noopener');
}
function nearBottom(){
  return stage.scrollHeight - stage.scrollTop - stage.clientHeight < 80;
}
function scrollStage(force){
  if(!force && !stickToBottom)return;
  if(scrollRaf)return;
  scrollRaf=requestAnimationFrame(()=>{
    scrollRaf=0;
    stage.scrollTop=stage.scrollHeight;
  });
}
function addMsg(role,text,opts){
  const row=document.createElement('div');
  row.className='msg '+role+((opts&&opts.animate&&!reduceMotion)?' is-new':'');
  if(role==='assistant'){
    const av=document.createElement('div');av.className='avatar';av.textContent='🌴';row.appendChild(av);
  }
  const col=document.createElement('div');col.className='col';
  const b=document.createElement('div');b.className='bubble';
  b.appendChild(document.createTextNode(text||''));
  col.appendChild(b);row.appendChild(col);
  messages.appendChild(row);
  scrollStage(true);
  return {row,b,col};
}
function addActs(col,text){
  const acts=document.createElement('div');acts.className='acts';
  const listen=document.createElement('button');listen.type='button';listen.textContent=T[lang].listen;
  listen.onclick=()=>speak(text,listen);
  const copy=document.createElement('button');copy.type='button';copy.textContent=T[lang].copy;
  copy.onclick=async()=>{
    try{await navigator.clipboard.writeText(text);copy.textContent=T[lang].copied;setTimeout(()=>copy.textContent=T[lang].copy,1200);}catch(e){}
  };
  const share=document.createElement('button');share.type='button';share.textContent=T[lang].share;
  share.onclick=async()=>{
    try{
      if(navigator.share)await navigator.share({title:'Teranga AI',text});
      else {await navigator.clipboard.writeText(text);share.textContent=T[lang].copied;setTimeout(()=>share.textContent=T[lang].share,1200);}
    }catch(e){}
  };
  acts.append(listen,copy,share);col.appendChild(acts);
}
function addCityImage(col,image){
  const list=Array.isArray(image)?image:(image&&image.url?[image]:[]);
  list.slice(0,2).forEach(item=>{
    if(!item||!item.url)return;
    const box=document.createElement('figure');box.className='city-pic';
    const img=document.createElement('img');
    img.src=item.url;img.alt=item.alt||'';img.loading='lazy';
    const cap=document.createElement('small');
    cap.textContent=item.alt+(item.credit?' · '+item.credit:'');
    box.append(img,cap);col.appendChild(box);
  });
}
function addMap(col,map){
  if(!map||!map.url)return;
  const box=document.createElement('div');box.className='city-map';
  if(map.embed){
    const frame=document.createElement('iframe');
    frame.src=map.embed;frame.loading='lazy';frame.referrerPolicy='no-referrer-when-downgrade';
    frame.title=map.label||'Carte';frame.allowFullscreen=true;
    box.appendChild(frame);
  }
  const a=document.createElement('a');
  a.href=map.url;a.target='_blank';a.rel='noopener noreferrer';
  a.textContent='Ouvrir dans Google Maps'+(map.label?' · '+map.label:'');
  box.appendChild(a);col.appendChild(box);
}
function addSources(col,sources){
  if(!sources||!sources.length)return;
  const box=document.createElement('div');box.className='sources';
  const label=document.createElement('b');label.textContent=T[lang].sources;box.appendChild(label);
  sources.slice(0,5).forEach(src=>{
    if(!src||!src.url)return;
    const a=document.createElement('a');
    a.href=src.url;a.target='_blank';a.rel='noopener noreferrer';
    a.textContent=src.title||src.url.replace(/^https?:\/\/(www\.)?/,'');
    box.appendChild(a);
  });
  if(box.childElementCount>1)col.appendChild(box);
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
    audio.onended=()=>{URL.revokeObjectURL(url);if(btn){btn.disabled=false;btn.textContent=T[lang].listen;}};
    await audio.play();
  }catch(e){if(btn){btn.disabled=false;btn.textContent=T[lang].listen;}}
}
const CARD_ICONS=[
  '<svg viewBox="0 0 24 24" fill="none"><path d="M6 15a6 6 0 1 1 10.4-4.2A4.5 4.5 0 1 1 17 19H7.5A3.5 3.5 0 0 1 6 15Z" stroke="currentColor" stroke-width="1.7"/><path d="M8 11.5 10 9l2 2 3-3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none"><path d="M4 18h16M6 18V9l6-4 6 4v9" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M10 18v-5h4v5" stroke="currentColor" stroke-width="1.7"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none"><path d="M5 19V8l7-4 7 4v11" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M9 19v-6h6v6" stroke="currentColor" stroke-width="1.7"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none"><path d="M4 10h16l-1.2 8.2A2 2 0 0 1 16.8 20H7.2a2 2 0 0 1-2-1.8L4 10Z" stroke="currentColor" stroke-width="1.7"/><path d="M8 10V7a4 4 0 0 1 8 0v3" stroke="currentColor" stroke-width="1.7"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none"><path d="M12 21s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10Z" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="11" r="2.2" stroke="currentColor" stroke-width="1.7"/></svg>',
  '<svg viewBox="0 0 24 24" fill="none"><path d="M4 6.5 10 4l4 3 6-2v13l-6 2-4-3-6 2V6.5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M10 4v13M14 7v13" stroke="currentColor" stroke-width="1.7"/></svg>'
];
function renderCards(){
  if(lastLang===lang)return;
  lastLang=lang;
  const t=T[lang];
  const cardFrag=document.createDocumentFragment();
  const chipFrag=document.createDocumentFragment();
  t.cards.forEach((c,i)=>{
    const card=document.createElement('button');
    card.className='card';card.type='button';card.dataset.q=c.q;
    const ico=document.createElement('div');ico.className='ico';ico.innerHTML=CARD_ICONS[i%CARD_ICONS.length];
    const b=document.createElement('b');b.textContent=c.t;
    card.append(ico,b);cardFrag.appendChild(card);
    const chip=document.createElement('button');
    chip.type='button';chip.dataset.q=c.q;chip.textContent=c.t;
    chipFrag.appendChild(chip);
  });
  $('cards').replaceChildren(cardFrag);
  $('chips').replaceChildren(chipFrag);
}
function setLang(next){
  lang=next;localStorage.setItem('teranga-lang',next);
  document.querySelectorAll('#langs button').forEach(b=>b.classList.toggle('on',b.dataset.lang===next));
  const t=T[lang];
  $('sub').textContent=t.sub;input.placeholder=t.ph;send.textContent=t.send;
  $('voiceToggle').textContent=autoVoice?t.vOn:t.vOff;
  $('heroTitle').textContent=t.heroTitle;$('heroText').textContent=t.heroText;
  $('hint').textContent=isTouch()?t.hintTouch:t.hint;
  const tabs=document.querySelectorAll('#tabbar button');
  if(tabs[0])tabs[0].lastChild.nodeValue=t.navHome;
  if(tabs[1])tabs[1].lastChild.nodeValue=t.navDiscover;
  if(tabs[2])tabs[2].lastChild.nodeValue=t.navChat;
  if(tabs[3])tabs[3].lastChild.nodeValue=t.navProfile;
  document.documentElement.lang=next==='wo'?'wo':next;
  renderCards();
  bindShare();
  if(rec)rec.lang=voiceMap[lang];
}
function themeInit(){
  const saved=localStorage.getItem('teranga-theme');
  document.body.dataset.theme=saved||'dark';
  applyThemeColor();
}
$('tabbar').addEventListener('click',e=>{
  const btn=e.target.closest('button[data-tab]');
  if(!btn)return;
  const tab=btn.dataset.tab;
  document.querySelectorAll('#tabbar button').forEach(b=>b.classList.toggle('on',b===btn));
  if(tab==='home'){showHero();stage.scrollTop=0;}
  if(tab==='discover'){showHero();$('chips').scrollIntoView({block:'nearest'});}
  if(tab==='chat'){input.focus();}
  if(tab==='profile'){$('themeBtn').click();}
});
function reset(){
  if(history.length&&!confirm(T[lang].resetAsk))return;
  if(inflight)inflight.abort();
  history=[];messages.replaceChildren();showHero();
  sessionStorage.removeItem('teranga-history');
}
function setupMic(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){mic.disabled=true;mic.title='Micro non disponible';return;}
  rec=new SR();rec.continuous=false;rec.interimResults=false;rec.lang=voiceMap[lang];
  rec.onstart=()=>{listening=true;mic.classList.add('listen');};
  rec.onresult=e=>{input.value=e.results[0][0].transcript;ask();};
  rec.onend=rec.onerror=()=>{listening=false;mic.classList.remove('listen');};
}
function persist(){
  clearTimeout(persistTimer);
  persistTimer=setTimeout(()=>{
    try{sessionStorage.setItem('teranga-history',JSON.stringify({lang,history}));}catch(e){}
  },250);
}
function restore(){
  try{
    const raw=sessionStorage.getItem('teranga-history');
    if(!raw)return;
    const data=JSON.parse(raw);
    if(data.lang&&T[data.lang])lang=data.lang;
    if(Array.isArray(data.history)&&data.history.length){
      history=data.history.slice(-12);
      hideHero();
      const frag=document.createDocumentFragment();
      history.forEach(item=>{
        if(item.role!=='user'&&item.role!=='assistant')return;
        const row=document.createElement('div');
        row.className='msg '+item.role;
        if(item.role==='assistant'){
          const av=document.createElement('div');av.className='avatar';av.textContent='🌴';row.appendChild(av);
        }
        const col=document.createElement('div');col.className='col';
        const b=document.createElement('div');b.className='bubble';
        b.textContent=cleanReply(item.content||'');
        col.appendChild(b);
        if(item.role==='assistant'){
          addActs(col,item.content||'');
          addCityImage(col,item.image);
          addMap(col,item.map);
          addSources(col,item.sources);
        }
        row.appendChild(col);
        frag.appendChild(row);
      });
      messages.appendChild(frag);
      stage.scrollTop=stage.scrollHeight;
    }
  }catch(e){}
}
async function ask(preset){
  const text=(preset||input.value).trim();
  if(!text||send.disabled)return;
  hideHero();
  addMsg('user',text,{animate:true});
  history.push({role:'user',content:text});
  persist();
  input.value='';input.style.height='';$('count').textContent='0 / 2000';
  send.disabled=false;send.textContent=T[lang].stop;
  send.dataset.mode='stop';
  const wait=addMsg('assistant','',{animate:true});
  const node=wait.b.firstChild;
  const cursor=document.createElement('span');cursor.className='cursor';
  const dots=document.createElement('div');dots.className='typing';
  dots.append(document.createElement('i'),document.createElement('i'),document.createElement('i'));
  wait.b.replaceWith(dots);
  const ctrl=new AbortController();inflight=ctrl;
  const kill=setTimeout(()=>ctrl.abort(),75000);
  const body=JSON.stringify({message:text,history:history.slice(-12),language:lang});
  let reply='', sources=[], image=null, map=null;
  try{
    const res=await fetch('/chat',{method:'POST',headers:headers(),body,signal:ctrl.signal});
    if(!res.ok){
      const data=await res.json().catch(()=>({}));
      throw new Error(data.error||T[lang].err);
    }
    let live='', pending='', shown=false, paint=0;
    const flush=()=>{
      paint=0;
      if(!pending)return;
      live+=pending;pending='';
      if(!shown){
        dots.replaceWith(wait.b);
        wait.b.classList.add('live');
        if(!reduceMotion)wait.b.appendChild(cursor);
        shown=true;
      }
      node.nodeValue=cleanReply(live);
      scrollStage();
    };
    const queue=chunk=>{
      pending+=chunk;
      if(!paint)paint=requestAnimationFrame(flush);
    };
    const reader=res.body.getReader();
    const dec=new TextDecoder();
    let buf='';
    while(true){
      const {value,done}=await reader.read();
      if(done)break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split('\n');buf=parts.pop();
      for(let i=0;i<parts.length;i++){
        const line=parts[i];
        if(!line)continue;
        let ev;try{ev=JSON.parse(line);}catch{continue;}
        if(ev.error)throw new Error(ev.error);
        if(ev.d)queue(ev.d);
        if(ev.s)sources=ev.s;
        if(ev.img)image=ev.img;
        if(ev.map)map=ev.map;
      }
    }
    if(buf.trim()){
      try{
        const ev=JSON.parse(buf);
        if(ev.error)throw new Error(ev.error);
        if(ev.d)queue(ev.d);
        if(ev.s)sources=ev.s;
        if(ev.img)image=ev.img;
        if(ev.map)map=ev.map;
      }catch(e){if(e.message&&!String(e).includes('JSON'))throw e;}
    }
    if(paint){cancelAnimationFrame(paint);flush();}
    reply=live.trim();
    if(!reply){
      const res2=await fetch('/chat',{method:'POST',headers:headers({'X-Teranga-Mode':'json'}),body,signal:ctrl.signal});
      const data=await res2.json().catch(()=>({}));
      if(!res2.ok)throw new Error(data.error||T[lang].err);
      reply=(data.reply||'').trim();
      if(data.sources)sources=data.sources;
      if(data.image)image=data.image;
      if(data.map)map=data.map;
      pending=reply;flush();
    }
    reply=cleanReply(reply);
    if(!shown){dots.replaceWith(wait.b);node.nodeValue=reply||T[lang].err;}
    else {node.nodeValue=reply;if(cursor.parentNode)cursor.remove();}
    wait.b.classList.remove('live');
    addActs(wait.col,reply);
    addCityImage(wait.col,image);
    addMap(wait.col,map);
    addSources(wait.col,sources);
    history.push({role:'assistant',content:reply,sources,image,map});
    history=history.slice(-12);
    persist();
    if(autoVoice&&reply)speak(reply);
  }catch(err){
    const aborted=err.name==='AbortError';
    const msg=aborted?T[lang].timeout:(err.message||T[lang].err);
    if(dots.parentNode)dots.replaceWith(wait.b);
    node.nodeValue=msg;
    if(!aborted){
      const retry=document.createElement('button');
      retry.className='speak';retry.type='button';retry.textContent=T[lang].retry;
      retry.onclick=()=>ask(text);
      wait.col.appendChild(retry);
    }
  }finally{
    clearTimeout(kill);inflight=null;send.dataset.mode='';send.disabled=false;send.textContent=T[lang].send;input.focus();
  }
}
$('langs').onclick=e=>{const b=e.target.closest('button');if(b)setLang(b.dataset.lang);};
$('chips').onclick=e=>{const b=e.target.closest('button');if(b)ask(b.dataset.q);};
$('cards').onclick=e=>{const b=e.target.closest('button');if(b)ask(b.dataset.q);};
send.onclick=()=>{
  if(send.dataset.mode==='stop'&&inflight){inflight.abort();return;}
  ask();
};
mic.onclick=()=>{if(!rec)return;listening?rec.stop():rec.start();};
$('resetBtn').onclick=reset;
$('shareAppBtn').onclick=shareApp;
$('copyLink').onclick=async()=>{
  try{
    await navigator.clipboard.writeText(location.origin+'/');
    $('copyLink').textContent=T[lang].linkCopied;
    setTimeout(()=>$('copyLink').textContent=T[lang].copyLink,1200);
  }catch(e){shareApp();}
};
$('themeBtn').onclick=()=>{
  const next=document.body.dataset.theme==='dark'?'light':'dark';
  document.body.dataset.theme=next;localStorage.setItem('teranga-theme',next);
  applyThemeColor();
};
$('voiceToggle').onclick=()=>{
  autoVoice=!autoVoice;localStorage.setItem('teranga-voice',autoVoice?'1':'0');
  $('voiceToggle').textContent=autoVoice?T[lang].vOn:T[lang].vOff;
};
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask();}});
let countRaf=0;
input.addEventListener('input',()=>{
  input.style.height='auto';
  const h=Math.min(input.scrollHeight,130);
  input.style.height=h+'px';
  if(!countRaf)countRaf=requestAnimationFrame(()=>{
    countRaf=0;$('count').textContent=input.value.length+' / 2000';
  });
});
stage.addEventListener('scroll',()=>{stickToBottom=nearBottom();},{passive:true});
if(window.visualViewport){
  const place=()=>{
    document.body.style.setProperty('--vvh',visualViewport.height+'px');
    if(document.body.classList.contains('has-chat'))scrollStage(true);
  };
  visualViewport.addEventListener('resize',place);place();
}
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js').catch(()=>{});
}
let deferredInstall=null;
window.addEventListener('beforeinstallprompt',e=>{
  e.preventDefault();deferredInstall=e;
  const btn=$('installBtn');if(btn)btn.hidden=false;
});
$('installBtn').onclick=async()=>{
  if(!deferredInstall)return;
  deferredInstall.prompt();
  await deferredInstall.userChoice.catch(()=>{});
  deferredInstall=null;$('installBtn').hidden=true;
};
themeInit();restore();setLang(lang);setupMic();

</script>
</body>
</html>
"""


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
    try:
        return Response(build_icon_png(192), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        return icon_svg()


@app.get("/icon-512.png")
def icon_512():
    try:
        return Response(build_icon_png(512), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        return icon_svg()


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
            "theme_color": "#0b0907",
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
    response = Response(
        HTML.replace("__CSP_NONCE__", nonce).replace("__SITE_URL__", SITE_URL),
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
