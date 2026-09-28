import json
from html import escape
from flask import Response, jsonify, request
from datetime import date

from services.http_security import origin_allowed
from services.language_quality import language_instruction
from services.senegal_knowledge import SENEGAL_REGIONS

ALLOWED_LANGS = {"fr", "en", "wo", "ff"}
UI_LANGS = {"fr", "en"}
MAX_BODY_BYTES = 12000
MAX_TRIP_DAYS = 90
REGION_COORDS = {
    "Dakar": (14.7167, -17.4677), "Diourbel": (14.6500, -16.2333),
    "Fatick": (14.3333, -16.4167), "Kaffrine": (14.1059, -15.5508),
    "Kaolack": (14.1500, -16.0833), "Kédougou": (12.5600, -12.1800),
    "Kolda": (12.8833, -14.9500), "Louga": (15.6167, -16.2167),
    "Matam": (15.6559, -13.2554), "Saint-Louis": (16.0326, -16.4818),
    "Sédhiou": (12.7081, -15.5569), "Tambacounda": (13.7700, -13.6700),
    "Thiès": (14.7833, -16.9167), "Ziguinchor": (12.5833, -16.2667),
}
BUDGET_BANDS = {"Économique": (35, 65), "Confort": (70, 130), "Premium": (140, 240), "Luxe": (260, 500), "Budget": (35, 65), "Comfort": (70, 130), "Luxury": (260, 500)}

UI = {
    "fr": {
        "title": "Senegal Trip Planner",
        "kicker": "Teranga AI · Voyage au Sénégal",
        "intro": "Construis un itinéraire personnalisé en quelques étapes.",
        "dates": "Dates", "travelers": "Voyageurs", "interests": "Centres d'intérêt",
        "budget": "Budget", "regions": "Régions", "pace": "Rythme",
        "start": "Créer mon voyage", "continue": "Continuer", "generate": "Générer mon itinéraire",
        "result": "Ton voyage est prêt", "back": "Modifier", "error": "Impossible de générer le voyage pour le moment.",
        "from": "Arrivée", "to": "Départ", "adults": "Adultes", "children": "Enfants",
        "budget_options": ["Économique", "Confort", "Premium", "Luxe"],
        "pace_options": ["Relax", "Équilibré", "Intensif"],
        "interest_options": ["Plages", "Culture & histoire", "Cuisine", "Nature", "Dakar", "Îles", "Faune", "Musique & vie nocturne", "Famille"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Laisser Teranga AI choisir", "share": "🔗 Partager ces préférences", "loading": "Teranga AI prépare ton voyage…", "copied": "✓ Lien copié", "note": "Les estimations et informations susceptibles de changer doivent être vérifiées avant le départ.", "map_title": "Carte du voyage", "day": "Jour", "morning": "Matin", "afternoon": "Après-midi", "evening": "Soir", "transport": "Transport", "budget_summary": "Budget indicatif",
    },
    "en": {
        "title": "Senegal Trip Planner", "kicker": "Teranga AI · Travel Senegal",
        "intro": "Build a personalized Senegal itinerary in a few steps.",
        "dates": "Dates", "travelers": "Travelers", "interests": "Interests", "budget": "Budget", "regions": "Regions", "pace": "Pace",
        "start": "Create my trip", "continue": "Continue", "generate": "Generate my itinerary", "result": "Your trip is ready",
        "back": "Edit", "error": "We could not generate the trip right now.", "from": "Arrival", "to": "Departure",
        "adults": "Adults", "children": "Children",
        "budget_options": ["Budget", "Comfort", "Premium", "Luxury"], "pace_options": ["Relaxed", "Balanced", "Intensive"],
        "interest_options": ["Beaches", "Culture & history", "Food", "Nature", "Dakar", "Islands", "Wildlife", "Music & nightlife", "Family"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Let Teranga AI choose", "share": "🔗 Share these preferences", "loading": "Teranga AI is preparing your trip…", "copied": "✓ Link copied", "note": "Estimates and information that may change should be verified before departure.", "map_title": "Trip map", "day": "Day", "morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "transport": "Transport", "budget_summary": "Indicative budget",
    },
}

def _lang():
    lang = str(request.args.get("lang") or request.form.get("lang") or "fr").lower()[:2]
    return lang if lang in UI_LANGS else "fr"

def _allowed_options(lang):
    languages = [lang, "fr", "en"]
    return {
        "interests": {value for language in languages if language in UI for value in UI[language]["interest_options"]},
        "regions": {value for language in languages if language in UI for value in UI[language]["region_options"]},
        "budget": set(BUDGET_BANDS),
        "pace": {"Relax", "Équilibré", "Intensif", "Relaxed", "Balanced", "Intensive"},
    }


def _option_list(values, name="x", input_type="checkbox"):
    return "".join(
        f'<label class="chip"><input type="{escape(input_type)}" name="{escape(name)}" value="{escape(v)}"><span>{escape(v)}</span></label>'
        for v in values
    )

def _html(site_url, lang="fr"):
    t = UI.get(lang, UI["fr"])
    return """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{site}/trip-planner">
<meta property="og:title" content="{title} | Teranga AI">
<meta property="og:description" content="{intro}">
<title>{title} | Teranga AI</title>
<style>
:root{{color-scheme:dark;--bg:#0b0907;--panel:#171310;--line:rgba(226,179,74,.2);--gold:#e2b34a;--text:#f6efe3;--muted:#b8a48c;--green:#0f6a43}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 90% 0,#244b37 0,transparent 28%),var(--bg);color:var(--text);font:16px/1.55 system-ui,sans-serif}}
main{{width:min(920px,calc(100% - 28px));margin:auto;padding:28px 0 70px}}
nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px}}nav a{{color:var(--gold);text-decoration:none;font-weight:800}}.logo{{font-weight:900;font-size:18px}}
.logo em{{font-style:normal;color:var(--gold)}}.kicker{{color:var(--gold);font-size:12px;letter-spacing:.13em;text-transform:uppercase;font-weight:900}}
h1{{font:700 clamp(34px,7vw,58px)/1.02 Georgia,serif;margin:9px 0 14px}}.intro{{color:var(--muted);font-size:18px}}
.card{{margin-top:22px;background:rgba(23,19,16,.96);border:1px solid var(--line);border-radius:28px;padding:24px}}
.step{{display:none}}.step.active{{display:block}}h2{{font-size:24px;margin:0 0 16px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}
label.field{{display:flex;flex-direction:column;gap:7px;color:var(--muted);font-size:14px}}
input[type=date],input[type=number]{{width:100%;background:#0e0b09;border:1px solid var(--line);color:var(--text);border-radius:13px;padding:13px;font:inherit}}
.chips{{display:flex;flex-wrap:wrap;gap:10px}}.chip input{{position:absolute;opacity:0}}.chip span{{display:block;padding:11px 14px;border:1px solid var(--line);border-radius:999px;cursor:pointer;color:var(--muted)}}.chip input:checked+span{{border-color:var(--gold);color:var(--text);background:#2a2113}}
.actions{{display:flex;justify-content:space-between;gap:12px;margin-top:24px}}button{{border:0;border-radius:14px;padding:13px 18px;font:800 15px system-ui;cursor:pointer}}.primary{{background:var(--gold);color:#17100a}}.secondary{{background:#251e18;color:var(--text)}}
.result{{white-space:pre-wrap;font-family:inherit;line-height:1.7}}.map{{margin-top:16px;border-radius:18px;overflow:hidden;border:1px solid var(--line)}}.loading{{color:var(--gold)}}.error{{color:#ffb4a9;margin-top:12px}}
.small{{font-size:12px;color:var(--muted);margin-top:14px}}
</style></head>
<body><main>
<nav><div class="logo">Teranga <em>AI</em></div><a href="/">← Teranga AI</a></nav>
<div class="kicker">{kicker}</div><h1>{title}</h1><p class="intro">{intro}</p>
<div class="card">
<form id="planner">
<section class="step active" data-step="1"><h2>{dates}</h2><div class="grid">
<label class="field">{from}<input name="arrival" type="date" required></label>
<label class="field">{to}<input name="departure" type="date" required></label></div>
<div class="actions"><span></span><button class="primary" type="button" data-next>{cont}</button></div></section>
<section class="step" data-step="2"><h2>{travelers}</h2><div class="grid">
<label class="field">{adults}<input name="adults" type="number" min="1" max="20" value="1" required></label>
<label class="field">{children}<input name="children" type="number" min="0" max="20" value="0"></label></div>
<div class="actions"><button class="secondary" type="button" data-prev>←</button><button class="primary" type="button" data-next>{cont}</button></div></section>
<section class="step" data-step="3"><h2>{interests}</h2><div class="chips">{interests_html}</div>
<div class="actions"><button class="secondary" type="button" data-prev>←</button><button class="primary" type="button" data-next>{cont}</button></div></section>
<section class="step" data-step="4"><h2>{budget}</h2><div class="chips">{budget_html}</div><h2 style="margin-top:22px">{pace}</h2><div class="chips">{pace_html}</div>
<div class="actions"><button class="secondary" type="button" data-prev>←</button><button class="primary" type="button" data-next>{cont}</button></div></section>
<section class="step" data-step="5"><h2>{regions}</h2><div class="chips">{regions_html}</div><label class="chip" style="display:inline-block;margin-top:12px"><input id="surprise" type="checkbox"><span>{surprise}</span></label>
<div class="actions"><button class="secondary" type="button" data-prev>←</button><button class="primary" type="submit">{generate}</button></div></section>
</form>
<div id="status"></div><div id="result" class="result"></div><div id="share" style="display:none;margin-top:16px"><button id="copy" class="secondary" type="button">{share}</button></div><div id="map" class="map"></div>
</div><p class="small">{note}</p>
</main>
<script>
const escapeHtml=s=>String(s||'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); const form=document.getElementById('planner'), steps=[...document.querySelectorAll('.step')], status=document.getElementById('status'), result=document.getElementById('result'); let current=0;
function show(i){{current=i;steps.forEach((s,n)=>s.classList.toggle('active',n===i));window.scrollTo({{top:0,behavior:'smooth'}})}}
document.querySelectorAll('[data-next]').forEach(b=>b.onclick=()=>{{if(form.reportValidity())show(current+1)}});
document.querySelectorAll('[data-prev]').forEach(b=>b.onclick=()=>show(current-1));
function encodeTrip(payload){{const bytes=new TextEncoder().encode(JSON.stringify(payload));let binary='';bytes.forEach(byte=>binary+=String.fromCharCode(byte));return btoa(binary).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'')}}
function decodeTrip(value){{try{{const base64=value.replace(/-/g,'+').replace(/_/g,'/');const padded=base64+'='.repeat((4-base64.length%4)%4);const binary=atob(padded);const bytes=Uint8Array.from(binary,char=>char.charCodeAt(0));return JSON.parse(new TextDecoder().decode(bytes))}}catch(_error){{return null}}}}
function applySharedTrip(){{const encoded=new URLSearchParams(location.hash.slice(1)).get('trip');if(!encoded)return;const payload=decodeTrip(encoded);if(!payload||typeof payload!=='object')return;for(const key of ['arrival','departure','adults','children']){{if(payload[key]!==undefined&&form.elements[key])form.elements[key].value=payload[key]}}for(const key of ['interests','regions']){{if(!Array.isArray(payload[key]))continue;document.querySelectorAll('input[name="'+key+'"]').forEach(input=>{{input.checked=payload[key].includes(input.value)}})}}for(const key of ['budget','pace']){{if(typeof payload[key]!=='string')continue;const input=document.querySelector('input[name="'+key+'"][value="'+CSS.escape(payload[key])+'"]');if(input)input.checked=true}}const surprise=document.getElementById('surprise');if(surprise)surprise.checked=Boolean(payload.surprise)}}
applySharedTrip();
form.onsubmit=async e=>{{e.preventDefault(); if(!form.reportValidity())return;
const payload={{lang:'{lang}',arrival:form.arrival.value,departure:form.departure.value,adults:+form.adults.value,children:+form.children.value,
interests:[...document.querySelectorAll('input[name="interests"]:checked')].map(x=>x.value),budget:document.querySelector('input[name="budget"]:checked')?.value||'Confort',
pace:document.querySelector('input[name="pace"]:checked')?.value||'Équilibré',
regions:[...document.querySelectorAll('input[name="regions"]:checked')].map(x=>x.value),surprise:document.getElementById('surprise').checked}};
status.innerHTML='<p class="loading">{loading}</p>'; result.textContent='';
try{{const r=await fetch('/api/trip-planner',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});const data=await r.json();if(!r.ok)throw new Error(data.error||'error');const p=data.plan||{{summary:data.itinerary,days:[],practical_notes:[]}};result.innerHTML='<h2>'+escapeHtml(p.summary||'')+'</h2>'+((p.days||[]).map(d=>'<article class="card"><h3>{day} '+escapeHtml(d.day||'')+' · '+escapeHtml(d.title||'')+'</h3><p><b>{morning} :</b> '+escapeHtml(d.morning||'')+'</p><p><b>{afternoon} :</b> '+escapeHtml(d.afternoon||'')+'</p><p><b>{evening} :</b> '+escapeHtml(d.evening||'')+'</p><p><b>{transport} :</b> '+escapeHtml(d.transport||'')+'</p></article>').join(''))+'<h3>{budget_summary}</h3><ul>'+((data.budget?.lines)||[]).map(x=>'<li>'+escapeHtml(x)+'</li>').join('')+'</ul>';status.textContent='';document.getElementById('map').innerHTML=data.map_html||'';document.getElementById('share').style.display='block';const encoded=encodeTrip(payload);const shareLang=payload.lang==='en'?'en':'fr';history.replaceState(null,'','/trip-planner?lang='+shareLang+'#trip='+encoded);document.getElementById('copy').onclick=async()=>{{await navigator.clipboard.writeText(location.href);document.getElementById('copy').textContent='{copied}';}};}}
catch(err){{status.innerHTML='<p class="error">{error}</p>';}}
}};
</script></body></html>""".format(
        lang=escape(lang), site=escape(site_url), title=escape(t["title"]), intro=escape(t["intro"]),
        kicker=escape(t["kicker"]), dates=escape(t["dates"]), travelers=escape(t["travelers"]),
        interests=escape(t["interests"]), budget=escape(t["budget"]), regions=escape(t["regions"]),
        pace=escape(t["pace"]), start=escape(t["start"]), cont=escape(t["continue"]),
        generate=escape(t["generate"]), result=escape(t["result"]), back=escape(t["back"]),
        error=escape(t["error"]), day=escape(t["day"]), morning=escape(t["morning"]), afternoon=escape(t["afternoon"]), evening=escape(t["evening"]), transport=escape(t["transport"]), budget_summary=escape(t["budget_summary"]), **{"from": escape(t["from"]), "to": escape(t["to"]), "adults": escape(t["adults"])},
        children=escape(t["children"]), loading=escape(t["loading"]), copied=escape(t["copied"]), note=escape(t["note"]), map_title=escape(t["map_title"]), share=escape(t.get("share", "Share this trip")), interests_html=_option_list(t["interest_options"], "interests"),
        budget_html=_option_list(t["budget_options"], "budget", "radio"), pace_html=_option_list(t["pace_options"], "pace", "radio"),
        regions_html=_option_list(t["region_options"], "regions"), surprise=escape(t["surprise"])
    )
    return html

def _budget(data):
    days = max(1, (data["departure_date"] - data["arrival_date"]).days)
    low, high = BUDGET_BANDS.get(data["budget"], (70, 130))
    people = data["adults"] + data["children"]
    total_low, total_high = low * people * days, high * people * days
    total = [round(total_low), round(total_high)]
    accommodation = [round(total_low * 0.38), round(total_high * 0.38)]
    food = [round(total_low * 0.22), round(total_high * 0.22)]
    transport = [round(total_low * 0.18), round(total_high * 0.18)]
    activities = [round(total_low * 0.17), round(total_high * 0.17)]
    buffer = [total[0] - sum((accommodation[0], food[0], transport[0], activities[0])),
              total[1] - sum((accommodation[1], food[1], transport[1], activities[1]))]
    return {
        "days": days,
        "people": people,
        "accommodation": accommodation,
        "food": food,
        "transport": transport,
        "activities": activities,
        "buffer": buffer,
        "total": total,
    }

def _map_html(regions):
    points = [REGION_COORDS[r] for r in regions if r in REGION_COORDS]
    if not points:
        return ""
    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]
    margin = 0.8
    west = min(longitudes) - margin
    south = min(latitudes) - margin
    east = max(longitudes) + margin
    north = max(latitudes) + margin
    bbox = f"{west:.4f}%2C{south:.4f}%2C{east:.4f}%2C{north:.4f}"
    return f'<iframe title="{map_title}" width="100%" height="320" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik"></iframe>'
def _normalize_plan(plan, fallback_text, expected_days=None):
    fallback = {"summary": fallback_text[:3000], "days": [], "practical_notes": []}
    if not isinstance(plan, dict):
        return fallback
    summary = plan.get("summary")
    days = plan.get("days")
    notes = plan.get("practical_notes")
    if not isinstance(summary, str) or not summary.strip() or not isinstance(days, list) or not isinstance(notes, list):
        return fallback
    if expected_days is not None and len(days) != expected_days:
        return fallback

    normalized_days = []
    for index, item in enumerate(days, start=1):
        if not isinstance(item, dict) or item.get("day") != index:
            return fallback
        fields = ("title", "region", "morning", "afternoon", "evening", "transport")
        values = {field: item.get(field) for field in fields}
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            return fallback
        normalized_days.append({
            "day": index,
            **{field: value.strip()[:500] for field, value in values.items()},
        })

    normalized_notes = [note.strip()[:500] for note in notes if isinstance(note, str) and note.strip()][:20]
    return {
        "summary": summary.strip()[:3000],
        "days": normalized_days,
        "practical_notes": normalized_notes,
    }

def _prompt(data):
    language = data.get("lang", "fr")
    return f"""{language_instruction(language)}

Build a practical Senegal travel itinerary from these preferences.
Arrival: {data['arrival']}
Departure: {data['departure']}
Travelers: {data['adults']} adults, {data['children']} children
Interests: {', '.join(data['interests']) or 'general discovery'}
Budget level: {data['budget']}
Pace: {data['pace']}
Preferred regions: {', '.join(data['regions']) or 'none'}
Surprise me: {data['surprise']}

Return ONLY valid JSON in the user's language. Schema: {{"summary": string, "days": [{{"day": number, "title": string, "region": string, "morning": string, "afternoon": string, "evening": string, "transport": string}}], "practical_notes": [string]}}. Create one object per travel day.
Include sensible travel pacing, approximate budget categories without inventing fixed current prices, and practical notes.
Do not claim current opening hours, fares, availability, visa rules or weather unless explicitly verified from live sources.
Do not invent hotels, restaurants, transport operators or reservations. If a recommendation needs current verification, say so.
If dates or preferences are inconsistent, explain the issue briefly.
"""

def register_trip_planner(app, client, site_url, allowed_origins=None):
    configured_origins = {str(origin).rstrip("/") for origin in (allowed_origins or {site_url}) if str(origin).strip()}

    @app.get("/trip-planner")
    def trip_planner():
        return Response(_html(site_url, _lang()), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.post("/api/trip-planner")
    def api_trip_planner():
        content_length = request.content_length
        if content_length is None and not request.environ.get("wsgi.input_terminated"):
            return jsonify({"error": "Longueur de requête requise."}), 411
        if content_length is not None and content_length > MAX_BODY_BYTES:
            return jsonify({"error": "Requête trop volumineuse."}), 413
        raw_body = request.get_data(cache=True)
        if len(raw_body) > MAX_BODY_BYTES:
            return jsonify({"error": "Requête trop volumineuse."}), 413
        if not origin_allowed(
            request.headers.get("Origin"),
            request.headers.get("Referer"),
            configured_origins,
        ):
            return jsonify({"error": "Origine non autorisée."}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Requête invalide."}), 400
        lang = str(body.get("lang", "fr")).lower()[:2]
        if lang not in ALLOWED_LANGS:
            lang = "fr"
        required = ["arrival", "departure"]
        if any(not str(body.get(k, "")).strip() for k in required):
            return jsonify({"error": "Dates manquantes."}), 400
        adults_value = body.get("adults", 1)
        children_value = body.get("children", 0)
        if (
            isinstance(adults_value, bool)
            or isinstance(children_value, bool)
            or not isinstance(adults_value, int)
            or not isinstance(children_value, int)
        ):
            return jsonify({"error": "Nombre de voyageurs invalide."}), 400
        adults = max(1, min(20, adults_value))
        children = max(0, min(20, children_value))
        options = _allowed_options(lang)
        interests_value = body.get("interests", [])
        regions_value = body.get("regions", [])
        interests = [x[:80] for x in interests_value if isinstance(x, str) and x in options["interests"]][:9] if isinstance(interests_value, list) else []
        regions = [x[:80] for x in regions_value if isinstance(x, str) and x in options["regions"]][:14] if isinstance(regions_value, list) else []
        budget = str(body.get("budget", "Confort"))[:40]
        if budget not in options["budget"]:
            budget = "Confort"
        pace = str(body.get("pace", "Équilibré"))[:40]
        if pace not in options["pace"]:
            pace = "Équilibré"
        arrival_value = body["arrival"]
        departure_value = body["departure"]
        if (
            not isinstance(arrival_value, str)
            or not isinstance(departure_value, str)
            or len(arrival_value) != 10
            or len(departure_value) != 10
        ):
            return jsonify({"error": "Format de date invalide."}), 400
        try:
            arrival_date = date.fromisoformat(arrival_value)
            departure_date = date.fromisoformat(departure_value)
        except ValueError:
            return jsonify({"error": "Format de date invalide."}), 400
        trip_days = (departure_date - arrival_date).days
        if trip_days <= 0:
            return jsonify({"error": "La date de départ doit être après l'arrivée."}), 400
        if trip_days > MAX_TRIP_DAYS:
            return jsonify({"error": f"La durée du voyage ne peut pas dépasser {MAX_TRIP_DAYS} jours."}), 400
        data = {"lang": lang, "arrival": arrival_date.isoformat(), "departure": departure_date.isoformat(),
                "arrival_date": arrival_date, "departure_date": departure_date,
                "adults": adults, "children": children, "interests": interests, "regions": regions,
                "budget": budget, "pace": pace, "surprise": body.get("surprise") is True}
        try:
            response = client.responses.create(model=app.config.get("OPENAI_TRIP_MODEL") or "gpt-5.6-luna",
                input=_prompt(data))
            text = getattr(response, "output_text", "") or ""
            if not text:
                return jsonify({"error": "Réponse vide de l'assistant."}), 502
            budget_info = _budget(data)
            regions = data["regions"] or ["Dakar"]
            try:
                parsed_plan = json.loads(text)
            except json.JSONDecodeError:
                parsed_plan = None
            expected_days = max(1, (departure_date - arrival_date).days)
            plan = _normalize_plan(parsed_plan, text, expected_days)
            if lang == "en":
                budget_lines = [
                    f"Indicative total budget: {budget_info['total'][0]}–{budget_info['total'][1]} USD",
                    f"Accommodation: {budget_info['accommodation'][0]}–{budget_info['accommodation'][1]} USD",
                    f"Meals: {budget_info['food'][0]}–{budget_info['food'][1]} USD",
                    f"Local transport: {budget_info['transport'][0]}–{budget_info['transport'][1]} USD",
                    f"Activities: {budget_info['activities'][0]}–{budget_info['activities'][1]} USD",
                    f"Buffer: {budget_info['buffer'][0]}–{budget_info['buffer'][1]} USD",
                    "Estimate excluding international flights; adjust for season and actual choices.",
                ]
            else:
                budget_lines = [
                    f"Budget total indicatif : {budget_info['total'][0]}–{budget_info['total'][1]} USD",
                    f"Hébergement : {budget_info['accommodation'][0]}–{budget_info['accommodation'][1]} USD",
                    f"Repas : {budget_info['food'][0]}–{budget_info['food'][1]} USD",
                    f"Transport local : {budget_info['transport'][0]}–{budget_info['transport'][1]} USD",
                    f"Activités : {budget_info['activities'][0]}–{budget_info['activities'][1]} USD",
                    f"Marge : {budget_info['buffer'][0]}–{budget_info['buffer'][1]} USD",
                    "Estimation hors vols internationaux, à ajuster selon saison et choix réels.",
                ]
            return jsonify({
                "itinerary": json.dumps(plan, ensure_ascii=False),
                "plan": plan,
                "budget": {"currency": "USD", "lines": budget_lines, "total": budget_info["total"]},
                "language": lang,
                "map_html": _map_html(regions),
            })
        except Exception:
            app.logger.exception("trip-planner")
            return jsonify({"error": "Impossible de générer le voyage pour le moment."}), 502
