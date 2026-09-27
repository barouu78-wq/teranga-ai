"""Senegal-first knowledge and retrieval policy for Teranga AI.

This module does not pretend to be a static encyclopedia. It gives the response
engine a structured map of Senegal topics and source priorities so it can decide
when fresh web evidence is required.
"""
from __future__ import annotations

SOURCE_PRIORITY = (
    "gov.sn",
    "ansd.sn",
    "tourisme.gouv.sn",
    "diplomatie.gouv.sn",
    "sante.gouv.sn",
    "education.gouv.sn",
    "interieur.gouv.sn",
    "transports.gouv.sn",
    "unesco.org",
    "who.int",
    "worldbank.org",
)

SENEGAL_DOMAINS = {
    "agriculture": ("agriculture", "élevage", "pêche", "horticulture"),
    "territory": ("régions", "départements", "communes", "villes", "géographie"),
    "travel": ("voyage", "tourisme", "itinéraire", "visiter", "plage", "hôtel"),
    "transport": ("transport", "TER", "BRT", "bus", "taxi", "aéroport", "AIBD"),
    "culture": ("culture", "histoire", "patrimoine", "musique", "tradition", "art"),
    "food": ("cuisine", "restaurant", "plat", "thieboudienne", "yassa", "mafé"),
    "economy": ("économie", "emploi", "prix", "entreprise", "commerce", "PIB"),
    "society": ("population", "éducation", "santé", "emploi", "démographie"),
    "environment": ("environnement", "parc", "faune", "forêt", "climat"),
    "diaspora": ("diaspora", "Sénégal-France", "retour", "transfert"),
    "administration": ("démarche", "document", "visa", "administration", "consulat"),
}

DYNAMIC_DOMAINS = {
    "weather", "transport", "restaurant", "travel", "administration",
    "prices", "events", "news", "flights",
}

def classify_domain(text: str) -> str:
    value = str(text or "").lower()
    for domain, terms in SENEGAL_DOMAINS.items():
        if any(term.lower() in value for term in terms):
            return domain
    return "general"

def needs_fresh_web(domain: str, text: str) -> bool:
    value = str(text or "").lower()
    return domain in DYNAMIC_DOMAINS or any(
        marker in value for marker in ("aujourd", "maintenant", "actuel", "latest",
                                       "cette semaine", "prix", "ouvert", "horaires")
    )

def source_domains(domain: str) -> tuple[str, ...]:
    if domain in {"society", "economy", "agriculture", "territory"}:
        return SOURCE_PRIORITY
    if domain in {"travel", "culture", "environment"}:
        return ("tourisme.gouv.sn", "ansd.sn", "unesco.org", "gov.sn")
    if domain == "administration":
        return ("diplomatie.gouv.sn", "interieur.gouv.sn", "gov.sn")
    return SOURCE_PRIORITY

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

MAX_MESSAGE_LENGTH = 2000
MAX_TTS_LENGTH = 1800
MAX_HISTORY_ITEM_LENGTH = 1400
MAX_IMAGE_BYTES = 8 * 1024 * 1024
OUTBOUND_TIMEOUT = 5
MAX_HISTORY_ITEMS = 12
MAX_HISTORY_CHARS = 10000
RATE_LIMIT = 16
RATE_WINDOW = 60
TTS_RATE_LIMIT = 15
CHAT_HOURLY_LIMIT = 120
TTS_HOURLY_LIMIT = 45
STT_RATE_LIMIT = 15
STT_HOURLY_LIMIT = 45
IMAGE_RATE_LIMIT = 24
IMAGE_RATE_WINDOW = 60
FX_RATE_LIMIT = 6
FX_RATE_WINDOW = 60
IDENTITY_COOKIE = "teranga_client"
IDENTITY_TTL = 60 * 60 * 24 * 30
WEB_RATE_LIMIT = 10
WEB_RATE_WINDOW = 60
ABUSE_SCORE_WINDOW = 600
ABUSE_BLOCK_SECONDS = 600
ABUSE_SCORE_THRESHOLD = 8
ABUSE_LOG_SAMPLE = 40
RATE_LOCK = threading.Lock()
CSRF_COOKIE = "teranga_csrf"
CSRF_HEADER = "X-CSRF-Token"

request_log = defaultdict(deque)
tts_request_log = defaultdict(deque)
chat_hourly_log = defaultdict(deque)
tts_hourly_log = defaultdict(deque)
stt_request_log = defaultdict(deque)
stt_hourly_log = defaultdict(deque)
realtime_request_log = defaultdict(deque)
realtime_hourly_log = defaultdict(deque)
image_request_log = defaultdict(deque)
fx_request_log = defaultdict(deque)
web_request_log = defaultdict(deque)
abuse_events = defaultdict(deque)
abuse_blocks = {}
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ZERO_WIDTH_CHARS = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
SAFE_LANG = frozenset({"fr", "en", "wo", "ff"})

# Uniquement les sujets vraiment changeants — évite la recherche web sur chaque question.
WEB_HINTS = (
    "photo", "photos", "image", "images", "visuel", "visuels", "montre moi", "montre-moi",
    "a quoi ressemble", "à quoi ressemble", "a quoi ça ressemble", "à quoi ça ressemble",
    "aujourd'hui", "aujourd’hui", "maintenant", "actuel", "actuelle",
    "actuels", "actuelles", "récent", "récente", "récentes",
    "horaire", "horaires", "ouvert", "ouverte",
    "disponible", "disponibilité", "réservation",
    "événement", "evenement", "météo", "meteo", "climat", "température", "temperature", "pluie", "pluies", "orage", "vent", "humidité", "humidite",
    "actualité", "actualités", "news", "today", "now",
    "current", "latest", "recent", "schedule", "hours",
    "open", "available", "availability", "booking", "weather", "event",
    "visa", "ferry", "cfa", "change", "taux",
    "sim", "orange money", "week-end", "weekend", "ce soir", "demain",
    "manger", "restaurant", "resto", "où manger", "ou manger",
    "eat", "dining", "food court",
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

def format_senegal_knowledge(data):
    profile = data.get("country_profile", {})
    regions = data.get("regions", [])
    lines = [
        "BASE DE CONNAISSANCES NATIONALE DU SÉNÉGAL (référence interne, multisources) :",
        "Ne pas réduire cette base à l'UNESCO : elle couvre territoire, vie quotidienne, météo/climat, santé, mobilité, formalités, économie, culture, histoire, gastronomie, environnement et tourisme.",
    ]
    modules = data.get("knowledge_modules", {})
    if modules:
        lines.append("MODULES NATIONAUX COMPLÉMENTAIRES :")
        for name, module in modules.items():
            description = module.get("description") or ""
            if description:
                lines.append(f"- {name}: {description}")
            for key in ("anchors", "languages", "cultural_areas", "traditions", "important_context", "stable_knowledge", "live_topics", "modes", "key_nodes", "sectors", "regional_examples", "ecosystems", "topics", "food_topics", "daily_topics", "categories", "major_areas"):
                values = module.get(key)
                if values:
                    lines.append(f"  {key}: {', '.join(map(str, values))}")
            rule = module.get("rule")
            if rule:
                lines.append(f"  règle: {rule}")
            source = module.get("live_source")
            if source:
                lines.append(f"  source temps réel: {source}")
    if profile:
        lines.append("REPÈRES NATIONAUX :")
        lines.append(
            f"- Capitale : {profile.get('capital')}; superficie : {profile.get('area_km2')} km²; "
            f"langue officielle : {profile.get('official_language')}; monnaie : {profile.get('currency', {}).get('name')} ({profile.get('currency', {}).get('code')}); "
            f"fuseau : {profile.get('time_zone')}; indépendance : {profile.get('independence_date')}."
        )
        geography = profile.get("geography", {})
        if geography:
            lines.append(
                f"- Géographie : façade {geography.get('coastline')}; pays voisins : {', '.join(geography.get('neighboring_countries', []))}; "
                f"grands fleuves : {', '.join(geography.get('major_rivers', []))}; zones : {', '.join(geography.get('major_geographic_areas', []))}."
            )
        climate = profile.get("climate", {})
        if climate:
            lines.append(f"- Climat : {climate.get('description')}")
        emergencies = profile.get("emergency_numbers", [])
        if emergencies:
            lines.append("URGENCES : " + "; ".join(f"{x.get('service')} {x.get('number')}" for x in emergencies) + ".")
    for region in regions:
        places = ", ".join(region.get("places", [])[:12])
        highlights = ", ".join(region.get("highlights", [])[:10])
        departments = ", ".join(region.get("departments", [])[:8])
        lines.append(
            f"- {region.get('name')}: départements = {departments}; localités = {places}; "
            f"points d'intérêt = {highlights}."
        )
    places = data.get("places", [])
    if places:
        lines.append("Lieux détaillés :")
        for place in places[:60]:
            what = "; ".join(str(place.get("what_to_see", "")).split(";")[:5])
            lines.append(f"- {place.get('name')}: {place.get('summary', '')} À voir : {what}.")
    domains = data.get("knowledge_scope", {}).get("domains", {})
    if domains:
        lines.append("DOMAINES À COUVRIR :")
        for key, description in domains.items():
            lines.append(f"- {key}: {description}")
    sources = data.get("source_registry", [])
    if sources:
        lines.append("SOURCES DE RÉFÉRENCE :")
        for source in sources:
            lines.append(f"- {source.get('name')}: {source.get('role')}.")
    reference_date = data.get("current_reference_date")
    if reference_date:
        lines.append(f"DATE DE RÉFÉRENCE DE LA BASE : {reference_date}. Cette date ne remplace jamais une vérification web pour une information actuelle.")
    dynamic_topics = data.get("dynamic_topics", [])
    if dynamic_topics:
        lines.append("SUJETS À VÉRIFIER EN TEMPS RÉEL : " + ", ".join(dynamic_topics) + ".")
    unesco = ", ".join(data.get("unesco_world_heritage", []))
    if unesco:
        lines.append(f"Patrimoine mondial UNESCO (une partie du patrimoine, pas toute la connaissance nationale) : {unesco}.")
    return "\n".join(lines)

