import json
from html import escape
from flask import Response, jsonify, request

ALLOWED_LANGS = {"fr", "en", "wo", "ff"}
MAX_BODY_BYTES = 12000

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
        "region_options": ["Dakar", "Gorée", "Saint-Louis", "Petite Côte", "Sine-Saloum", "Casamance", "Kédougou"],
        "surprise": "✨ Laisser Teranga AI choisir",
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
        "region_options": ["Dakar", "Gorée", "Saint-Louis", "Petite Côte", "Sine-Saloum", "Casamance", "Kédougou"],
        "surprise": "✨ Let Teranga AI choose",
    },
}

def _lang():
    lang = str(request.args.get("lang") or request.form.get("lang") or "fr").lower()[:2]
    return lang if lang in ALLOWED_LANGS else "fr"

def _option_list(values):
    return "".join(f'<label class="chip"><input type="checkbox" name="x" value="{escape(v)}"><span>{escape(v)}</span></label>' for v in values)

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
.result{{white-space:pre-wrap;font-family:inherit;line-height:1.7}}.loading{{color:var(--gold)}}.error{{color:#ffb4a9;margin-top:12px}}
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
<div id="status"></div><div id="result" class="result"></div>
</div><p class="small">Les estimations et informations susceptibles de changer doivent être vérifiées avant le départ.</p>
</main>
<script>
const form=document.getElementById('planner'), steps=[...document.querySelectorAll('.step')], status=document.getElementById('status'), result=document.getElementById('result'); let current=0;
function show(i){{current=i;steps.forEach((s,n)=>s.classList.toggle('active',n===i));window.scrollTo({{top:0,behavior:'smooth'}})}}
document.querySelectorAll('[data-next]').forEach(b=>b.onclick=()=>{{if(form.reportValidity())show(current+1)}});
document.querySelectorAll('[data-prev]').forEach(b=>b.onclick=()=>show(current-1));
form.onsubmit=async e=>{{e.preventDefault(); if(!form.reportValidity())return;
const payload={{lang:'{lang}',arrival:form.arrival.value,departure:form.departure.value,adults:+form.adults.value,children:+form.children.value,
interests:[...document.querySelectorAll('input[name=x]:checked')].map(x=>x.value),budget:[...document.querySelectorAll('section[data-step="4"] input[name=x]:checked')].map(x=>x.value)[0]||'Confort',
pace:[...document.querySelectorAll('section[data-step="4"] input[name=x]:checked')].map(x=>x.value)[1]||'Équilibré',
regions:[...document.querySelectorAll('section[data-step="5"] input[name=x]:checked')].map(x=>x.value),surprise:document.getElementById('surprise').checked}};
status.innerHTML='<p class="loading">Teranga AI prépare ton voyage…</p>'; result.textContent='';
try{{const r=await fetch('/api/trip-planner',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});const data=await r.json();if(!r.ok)throw new Error(data.error||'error');result.textContent=data.itinerary;status.textContent='';}}
catch(err){{status.innerHTML='<p class="error">{error}</p>';}}
}};
</script></body></html>""".format(
        lang=escape(lang), site=escape(site_url), title=escape(t["title"]), intro=escape(t["intro"]),
        kicker=escape(t["kicker"]), dates=escape(t["dates"]), travelers=escape(t["travelers"]),
        interests=escape(t["interests"]), budget=escape(t["budget"]), regions=escape(t["regions"]),
        pace=escape(t["pace"]), start=escape(t["start"]), cont=escape(t["continue"]),
        generate=escape(t["generate"]), result=escape(t["result"]), back=escape(t["back"]),
        error=escape(t["error"]), **{"from": escape(t["from"]), "to": escape(t["to"]), "adults": escape(t["adults"])},
        children=escape(t["children"]), interests_html=_option_list(t["interest_options"]),
        budget_html=_option_list(t["budget_options"]), pace_html=_option_list(t["pace_options"]),
        regions_html=_option_list(t["region_options"]), surprise=escape(t["surprise"])
    )
    return html

def _prompt(data):
    return f"""Build a practical Senegal travel itinerary from these preferences.
Arrival: {data['arrival']}
Departure: {data['departure']}
Travelers: {data['adults']} adults, {data['children']} children
Interests: {', '.join(data['interests']) or 'general discovery'}
Budget level: {data['budget']}
Pace: {data['pace']}
Preferred regions: {', '.join(data['regions']) or 'none'}
Surprise me: {data['surprise']}

Return ONLY a useful itinerary in the user's language. Use a clear day-by-day structure.
Include sensible travel pacing, approximate budget categories without inventing fixed current prices, and practical notes.
Do not claim current opening hours, fares, availability, visa rules or weather unless explicitly verified from live sources.
Do not invent hotels, restaurants, transport operators or reservations. If a recommendation needs current verification, say so.
If dates or preferences are inconsistent, explain the issue briefly.
"""

def register_trip_planner(app, client, site_url):
    @app.get("/trip-planner")
    def trip_planner():
        return Response(_html(site_url, _lang()), mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})

    @app.post("/api/trip-planner")
    def api_trip_planner():
        if request.content_length and request.content_length > MAX_BODY_BYTES:
            return jsonify({"error": "Requête trop volumineuse."}), 413
        origin = request.headers.get("Origin", "").rstrip("/")
        allowed = {site_url.rstrip("/")}
        if origin and origin not in allowed:
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
        try:
            adults = max(1, min(20, int(body.get("adults", 1))))
            children = max(0, min(20, int(body.get("children", 0))))
        except (TypeError, ValueError):
            return jsonify({"error": "Nombre de voyageurs invalide."}), 400
        interests = [str(x)[:80] for x in body.get("interests", []) if isinstance(x, str)][:9]
        regions = [str(x)[:80] for x in body.get("regions", []) if isinstance(x, str)][:7]
        budget = str(body.get("budget", "Confort"))[:40]
        pace = str(body.get("pace", "Équilibré"))[:40]
        data = {"arrival": str(body["arrival"])[:20], "departure": str(body["departure"])[:20],
                "adults": adults, "children": children, "interests": interests, "regions": regions,
                "budget": budget, "pace": pace, "surprise": bool(body.get("surprise"))}
        try:
            response = client.responses.create(model=app.config.get("OPENAI_TRIP_MODEL") or "gpt-5.6-luna",
                input=_prompt(data))
            text = getattr(response, "output_text", "") or ""
            if not text:
                return jsonify({"error": "Réponse vide de l'assistant."}), 502
            return jsonify({"itinerary": text[:14000], "language": lang})
        except Exception:
            app.logger.exception("trip-planner")
            return jsonify({"error": "Impossible de générer le voyage pour le moment."}), 502
