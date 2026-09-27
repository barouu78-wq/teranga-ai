import hashlib
import hmac
import io
import json
import os
import re
import secrets
import threading
import time
import unicodedata
from collections import defaultdict, deque
from functools import wraps
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, stream_with_context
from openai import OpenAI
from werkzeug.middleware.proxy_fix import ProxyFix
from services.seo import SEO_PAGES, render_seo_page
from services.international_seo import register_localized_routes, localized_sitemap_urls
from services.explorer import render_explorer_page
from services.maps import lookup_map, should_fetch_map
from services.trip_planner import register_trip_planner
from services.images import (
    fetch_city_image as _fetch_city_image,
    fetch_commons_image as _fetch_commons_image,
    fetch_commons_images as _fetch_commons_images,
    fetch_google_images as _fetch_google_images,
)

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
_stable = os.getenv("SECRET_KEY") or os.getenv("OPENAI_API_KEY") or "teranga-ai"
app.config["SECRET_KEY"] = hashlib.sha256(_stable.encode("utf-8")).hexdigest()
app.config["JSON_SORT_KEYS"] = False
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
TRUST_PROXY = os.getenv("TRUST_PROXY", "1") == "1"
SITE_URL = os.getenv("SITE_URL", "https://teranga-ai-1.onrender.com").rstrip("/")
register_localized_routes(app, SITE_URL)

INDEXNOW_KEY = "8078ffb659c643b58bddddca48be0627"


@app.route(f"/{INDEXNOW_KEY}.txt")
def indexnow_key():
    return Response(INDEXNOW_KEY, mimetype="text/plain")


ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", SITE_URL).split(",")
    if origin.strip()
}
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "").strip()
BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_PATH = BASE_DIR / "data" / "senegal_knowledge.json"

def load_senegal_knowledge():
    try:
        with KNOWLEDGE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

SENEGAL_KNOWLEDGE = load_senegal_knowledge()
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

client = OpenAI(api_key=API_KEY, timeout=30.0, max_retries=0)
register_trip_planner(app, client, SITE_URL)
