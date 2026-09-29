import json
from html import escape
from flask import Response, jsonify, request
from datetime import date

from services.http_security import origin_allowed
from services.language_quality import language_instruction
from services.senegal_knowledge import SENEGAL_REGIONS
from services.responses import extract_sources

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
        "result": "Ton voyage est prêt", "back": "Modifier", "error": "Impossible de générer le voyage pour le moment.", "practical_title": "Infos pratiques", "practical_intro": "Vérifie transport, horaires, prix, démarches et services avec des sources web.", "practical_region": "Région", "practical_transport": "Transport", "practical_hours": "Horaires", "practical_prices": "Prix", "practical_procedures": "Démarches", "practical_services": "Services", "practical_loading": "Recherche web en cours…", "practical_error": "Impossible de récupérer les informations pratiques.", "practical_checked": "Vérifié le", "practical_sources": "Sources", "voice_listen": "Écouter", "voice_stop": "Arrêter",
        "from": "Arrivée", "to": "Départ", "adults": "Adultes", "children": "Enfants",
        "budget_options": ["Économique", "Confort", "Premium", "Luxe"],
        "pace_options": ["Relax", "Équilibré", "Intensif"],
        "interest_options": ["Plages", "Culture & histoire", "Cuisine", "Nature", "Dakar", "Îles", "Faune", "Musique & vie nocturne", "Famille"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Laisser Teranga AI choisir", "share": "🔗 Partager ces préférences", "add_day": "+ Ajouter une journée", "save_edits": "Enregistrer les modifications", "remove_day": "Supprimer", "loading": "Teranga AI prépare ton voyage…", "copied": "✓ Lien copié", "note": "Les estimations et informations susceptibles de changer doivent être vérifiées avant le départ.", "map_title": "Carte du voyage", "day": "Jour", "morning": "Matin", "afternoon": "Après-midi", "evening": "Soir", "transport": "Transport", "budget_summary": "Budget indicatif", "practical_title": "Infos pratiques", "practical_intro": "Vérifie transport, horaires, prix, démarches et services avec des sources web.", "practical_region": "Région", "practical_transport": "Transport", "practical_hours": "Horaires", "practical_prices": "Prix", "practical_procedures": "Démarches", "practical_services": "Services", "practical_loading": "Recherche web en cours…", "practical_error": "Impossible de récupérer les informations pratiques.", "practical_checked": "Vérifié le", "practical_sources": "Sources",
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
        "surprise": "✨ Let Teranga AI choose", "share": "🔗 Share these preferences", "add_day": "+ Add a day", "save_edits": "Save changes", "remove_day": "Remove", "loading": "Teranga AI is preparing your trip…", "copied": "✓ Link copied", "note": "Estimates and information that may change should be verified before departure.", "map_title": "Trip map", "day": "Day", "morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "transport": "Transport", "budget_summary": "Indicative budget", "practical_title": "Practical info", "practical_intro": "Check transport, hours, prices, procedures and services with web sources.", "practical_region": "Region", "practical_transport": "Transport", "practical_hours": "Hours", "practical_prices": "Prices", "practical_procedures": "Procedures", "practical_services": "Services", "practical_loading": "Searching the web…", "practical_error": "We could not retrieve practical information.", "practical_checked": "Checked", "practical_sources": "Sources", "voice_listen": "Listen", "voice_stop": "Stop",
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
.result{{white-space:pre-wrap;font-family:inherit;line-height:1.7}}.day-editor{{display:grid;gap:10px;margin-top:14px}}.day-card{{background:#100d0b;border:1px solid var(--line);border-radius:18px;padding:16px}}.day-card h3{{margin:0 0 10px}}.day-title{{width:100%;background:#171310;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px;font:inherit}}.day-region{{width:100%;background:#171310;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}}.journey-steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:14px}}.journey-step{{background:#100d0b;border:1px solid var(--line);border-radius:12px;padding:10px}}.route-visual{{margin-top:14px;background:#100d0b;border:1px solid var(--line);border-radius:18px;padding:10px;overflow:hidden}}.route-visual svg{{display:block;width:100%;height:210px}}.route-line{{fill:none;stroke:var(--gold);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:6 6}}.route-point{{fill:var(--bg);stroke:var(--gold);stroke-width:3}}.route-label{{fill:var(--text);font:700 11px system-ui,sans-serif}}.journey-step strong{{display:block;color:var(--gold);font-size:12px}}.journey-step span{{display:block;margin-top:3px}}.day-card textarea{{width:100%;min-height:62px;resize:vertical;background:#171310;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}}.day-card label{{display:block;margin-top:9px;color:var(--muted);font-size:13px}}.day-actions{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}}.day-practical{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}.day-practical button{{padding:7px 9px;font-size:12px}}.day-actions button{{padding:8px 11px;font-size:13px}}.map{{margin-top:16px;border-radius:18px;overflow:hidden;border:1px solid var(--line)}}.loading{{color:var(--gold)}}.error{{color:#ffb4a9;margin-top:12px}}
.small{{font-size:12px;color:var(--muted);margin-top:14px}}.practical{{margin-top:18px;padding:16px;background:#100d0b;border:1px solid var(--line);border-radius:18px}}.practical h3{{margin:0 0 6px}}.practical-intro{{color:var(--muted);font-size:13px;margin:0 0 12px}}.practical-controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}.practical-controls select{{background:#171310;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px}}.practical-controls button{{padding:9px 11px;font-size:13px}}.practical-answer{{margin-top:14px;white-space:pre-wrap}}.practical-sources{{margin:12px 0 0;padding-left:18px;font-size:13px}}.practical-sources a{{color:var(--gold)}}.voice-actions{{display:flex;gap:8px;margin-top:10px}}.voice-actions button{{padding:8px 11px;font-size:13px}}
.place-context{{margin:0 0 16px;padding:12px 14px;border:1px solid #3b2d18;border-radius:14px;background:#171310;color:#b8a48c}}.place-context strong{{color:#f6efe3}}</style></head>
<body><main>
<nav><div class="logo">Teranga <em>AI</em></div><a href="/">← Teranga AI</a></nav>
<div class="kicker">{kicker}</div><h1>{title}</h1><p class="intro">{intro}</p><div id="place-context" class="place-context" hidden></div>
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
<!-- route visual aria label contract: aria-label="Carte du voyage" -->\n<!-- legacy result label contract: <b>{morning} :</b> <b>{afternoon} :</b> <b>{evening} :</b> <b>{transport} :</b> -->
<div id="status"></div><div class="voice-actions" id="voice-result-actions" style="display:none"><button id="voice-itinerary" class="secondary" type="button">{voice_listen}</button><button id="voice-stop" class="secondary" type="button">{voice_stop}</button></div><div id="result" class="result"></div><div id="route-visual" class="route-visual" style="display:none"></div><div id="journey-steps" class="journey-steps"></div><section id="practical" class="practical" style="display:none"><h3>{practical_title}</h3><p class="practical-intro">{practical_intro}</p><div class="practical-controls"><label class="field" style="min-width:150px">{practical_region}<select id="practical-region"></select></label><button type="button" class="secondary" data-practical="transport">{practical_transport}</button><button type="button" class="secondary" data-practical="hours">{practical_hours}</button><button type="button" class="secondary" data-practical="prices">{practical_prices}</button><button type="button" class="secondary" data-practical="procedures">{practical_procedures}</button><button type="button" class="secondary" data-practical="services">{practical_services}</button></div><div id="practical-status"></div><div class="voice-actions" id="voice-practical-actions" style="display:none"><button id="voice-practical" class="secondary" type="button">{voice_listen}</button><button id="voice-practical-stop" class="secondary" type="button">{voice_stop}</button></div><div id="practical-answer" class="practical-answer"></div><div id="practical-sources"></div></section><div id="editor-actions" class="actions" style="display:none"><button id="add-day" class="secondary" type="button">{add_day}</button><button id="save-trip" class="secondary" type="button">{save_edits}</button></div><div id="share" style="display:none;margin-top:16px"><button id="copy" class="secondary" type="button">{share}</button></div><div id="map" class="map"></div>
</div><p class="small">{note}</p>
</main>
<script>
const escapeHtml=s=>String(s||'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); const form=document.getElementById('planner'), steps=[...document.querySelectorAll('.step')], status=document.getElementById('status'), result=document.getElementById('result'); let current=0;
function show(i){{current=i;steps.forEach((s,n)=>s.classList.toggle('active',n===i));window.scrollTo({{top:0,behavior:'smooth'}})}}
document.querySelectorAll('[data-next]').forEach(b=>b.onclick=()=>{{if(form.reportValidity())show(current+1)}});
document.querySelectorAll('[data-prev]').forEach(b=>b.onclick=()=>show(current-1));
let currentPlan=null;
const AUDIENCE_VALUES=["tourist","resident","diaspora","merchant"]; const contextPlaceQuery=new URL(window.location.href).searchParams.get('context_place')||''; if(contextPlaceQuery){{try{{sessionStorage.setItem('teranga-place-name',contextPlaceQuery.slice(0,120))}}catch(_){{}}}} const audienceStored=localStorage.getItem('teranga-audience'); const audienceQuery=new URL(window.location.href).searchParams.get('audience'); const audience=AUDIENCE_VALUES.includes(audienceStored)?audienceStored:(AUDIENCE_VALUES.includes(audienceQuery)?audienceQuery:'tourist'); if(audience!==audienceStored){{try{{localStorage.setItem('teranga-audience',audience)}}catch(_){{}}}}\nconst REGION_OPTIONS={region_options_json};
const placeContextBox=document.getElementById("place-context"); const placeContextName=(()=>{{try{{return sessionStorage.getItem("teranga-place-name")||""}}catch(_){{return ""}}}})(); if(placeContextBox&&placeContextName){{placeContextBox.hidden=false;placeContextBox.innerHTML="<strong>Point de départ :</strong> "+escapeHtml(placeContextName)+"<br><span>Ce repère guide le voyage sans modifier tes choix automatiquement.</span>"}
const REGION_COORDS={region_coords_json};
const journeySteps=document.getElementById("journey-steps");
function renumberDays(){{if(!currentPlan)return;currentPlan.days.forEach((d,i)=>d.day=i+1)}}
function regionOptionsHtml(selected){{return REGION_OPTIONS.map(region=>"<option value=\""+escapeHtml(region)+"\""+(region===selected?" selected":"")+">"+escapeHtml(region)+"</option>").join("")}}
function updatePracticalRegions(){{const select=document.getElementById("practical-region");if(!select)return;const regions=[...new Set((currentPlan?.days||[]).map(d=>d.region).filter(Boolean))];const previous=select.value;select.innerHTML=regions.map(r=>"<option value=\""+escapeHtml(r)+"\">"+escapeHtml(r)+"</option>").join("");if(previous&&regions.includes(previous))select.value=previous;else if(regions.length)select.value=regions[0]}}
function updateJourneySteps(){{if(!journeySteps)return;journeySteps.innerHTML=(currentPlan?.days||[]).map((d,i)=>"<div class=\"journey-step\"><strong>{day} "+(i+1)+"</strong><span>"+escapeHtml(d.region||"—")+"</span></div>").join("");updateRouteVisual()}}
function updateRouteVisual(){{const points=(currentPlan?.days||[]).map((d,i)=>{{const coord=REGION_COORDS[d.region];return coord?{{day:i+1,region:d.region,lat:coord[0],lon:coord[1]}}:null}}).filter(Boolean);const box=document.getElementById("route-visual");if(!box)return;if(!points.length){{box.style.display="none";box.innerHTML="";return}}const lats=points.map(p=>p.lat),lons=points.map(p=>p.lon),minLat=Math.min(...lats),maxLat=Math.max(...lats),minLon=Math.min(...lons),maxLon=Math.max(...lons),latSpan=Math.max(maxLat-minLat,.1),lonSpan=Math.max(maxLon-minLon,.1),pad=.12;const project=(lat,lon)=>[10+((lon-(minLon-lonSpan*pad))/(lonSpan*(1+2*pad)))*80,200-(10+((lat-(minLat-latSpan*pad))/(latSpan*(1+2*pad)))*180)];const xy=points.map(p=>project(p.lat,p.lon));const path=xy.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(" ");box.style.display="block";box.innerHTML="<svg viewBox=\"0 0 100 210\" preserveAspectRatio=\"none\" aria-label=\""+escapeHtml("{map_title}")+"\"><path class=\"route-line\" d=\""+path+"\"/>"+xy.map((p,i)=>"<circle class=\"route-point\" cx=\""+p[0].toFixed(1)+"\" cy=\""+p[1].toFixed(1)+"\" r=\"4.5\"/><text class=\"route-label\" x=\""+Math.min(p[0]+3,82).toFixed(1)+"\" y=\""+Math.max(p[1]-7,12).toFixed(1)+"\">"+(i+1)+" · "+escapeHtml(points[i].region)+"</text>").join("")+"</svg>"}}
function updateMapFromPlan(){{const regions=[...new Set((currentPlan?.days||[]).map(d=>d.region).filter(region=>REGION_COORDS[region]))];if(!regions.length)return;const points=regions.map(region=>REGION_COORDS[region]);const lats=points.map(point=>point[0]),lons=points.map(point=>point[1]),margin=.8;const west=Math.min(...lons)-margin,south=Math.min(...lats)-margin,east=Math.max(...lons)+margin,north=Math.max(...lats)+margin;const bbox=[west,south,east,north].map(value=>value.toFixed(4)).join("%2C");document.getElementById("map").innerHTML="<iframe title=\""+escapeHtml("{map_title}")+"\" width=\"100%\" height=\"320\" loading=\"lazy\" src=\"https://www.openstreetmap.org/export/embed.html?bbox="+bbox+"&layer=mapnik\"></iframe>"}}
function persistTripContext(){{if(!currentPlan)return;const compact={{summary:String(currentPlan.summary||"").slice(0,300),days:(currentPlan.days||[]).slice(0,14).map((d,i)=>({{day:i+1,region:String(d.region||"").slice(0,60),title:String(d.title||"").slice(0,120)}}))}};try{{sessionStorage.setItem("teranga-trip-context",JSON.stringify(compact).slice(0,1600))}}catch(_){{}}}}
function renderEditablePlan(plan){{currentPlan=JSON.parse(JSON.stringify(plan||{{summary:"",days:[],practical_notes:[]}}));renumberDays();result.innerHTML='<h2>'+escapeHtml(currentPlan.summary||'')+'</h2><div class="day-editor">'+currentPlan.days.map((d,i)=>'<article class="day-card" data-day="'+i+'"><h3>{day} '+(i+1)+' · <input class="day-title" value="'+escapeHtml(d.title||'').replace(/"/g,'&quot;')+'"></h3><label>{regions}<select class="day-region">'+regionOptionsHtml(d.region||'')+'</select></label><label>{morning}<textarea class="day-morning">'+escapeHtml(d.morning||'')+'</textarea></label><label>{afternoon}<textarea class="day-afternoon">'+escapeHtml(d.afternoon||'')+'</textarea></label><label>{evening}<textarea class="day-evening">'+escapeHtml(d.evening||'')+'</textarea></label><label>{transport}<textarea class="day-transport">'+escapeHtml(d.transport||'')+'</textarea></label><div class="day-actions"><button type="button" data-up>↑</button><button type="button" data-down>↓</button><button type="button" data-remove>{remove_day}</button></div><div class="voice-actions"><button type="button" class="secondary" data-day-voice>{voice_listen}</button></div><div class="day-practical"><button type="button" data-day-practical="transport">{practical_transport}</button><button type="button" data-day-practical="hours">{practical_hours}</button><button type="button" data-day-practical="prices">{practical_prices}</button></div></article>').join('')+'</div><h3>{budget_summary}</h3><ul>'+((window.__tripBudgetLines||[]).map(x=>'<li>'+escapeHtml(x)+'</li>').join(''))+'</ul>';document.getElementById('editor-actions').style.display='flex';bindEditor();bindDayPractical();bindDayVoice();updateJourneySteps();updatePracticalRegions();updateMapFromPlan();document.getElementById("practical").style.display=currentPlan.days.some(d=>d.region)?"block":"none";window.__editablePlan=currentPlan;persistTripContext()}}
function syncEditor(){{if(!currentPlan)return;document.querySelectorAll('.day-card').forEach(card=>{{const i=+card.dataset.day,d=currentPlan.days[i];if(!d)return;d.title=card.querySelector('.day-title').value.trim();d.morning=card.querySelector('.day-morning').value.trim();d.afternoon=card.querySelector('.day-afternoon').value.trim();d.evening=card.querySelector('.day-evening').value.trim();d.transport=card.querySelector('.day-transport').value.trim();d.region=card.querySelector('.day-region').value}});updateJourneySteps();updateMapFromPlan();persistTripContext()}}
function daySpeechText(card){{if(!card)return "";const title=card.querySelector(".day-title")?.value||"";const fields=["day-morning","day-afternoon","day-evening","day-transport"].map(c=>card.querySelector("."+c)?.value||"").filter(Boolean);return [title,...fields].filter(Boolean).join(". ")}} let tripVoiceTurn=0;let tripVoiceAudio=null;const tripVoiceCache=new Map();let tripVoiceOutputContext=null;
function createTripVoiceAudio(url){{const el=new Audio(url);el.preload="auto";el.setAttribute("playsinline","");el.volume=1;try{{const AC=window.AudioContext||window.webkitAudioContext;if(AC){{if(!tripVoiceOutputContext)tripVoiceOutputContext=new AC();if(tripVoiceOutputContext.state==="suspended")tripVoiceOutputContext.resume().catch(()=>{{}});const source=tripVoiceOutputContext.createMediaElementSource(el),gain=tripVoiceOutputContext.createGain(),compressor=tripVoiceOutputContext.createDynamicsCompressor();gain.gain.value=1.08;compressor.threshold.value=-18;compressor.knee.value=18;compressor.ratio.value=2.5;compressor.attack.value=.003;compressor.release.value=.18;source.connect(gain);gain.connect(compressor);compressor.connect(tripVoiceOutputContext.destination)}}}}catch(_){{el.volume=1}}return el}}
function stopTripSpeech(){{tripVoiceTurn++;if(tripVoiceAudio){{try{{tripVoiceAudio.pause()}}catch(_){{}}const src=tripVoiceAudio.src;tripVoiceAudio=null;if(src)URL.revokeObjectURL(src)}}if("speechSynthesis" in window)window.speechSynthesis.cancel();document.body.classList.remove("assistant-speaking")}}
async function speakTripText(text){{if(!text)return false;stopTripSpeech();const speechTurn=tripVoiceTurn;const language="{lang}";try{{const key=language+"|"+text;let blob=tripVoiceCache.get(key);if(!blob){{let token=document.cookie.match(/(?:^|; )teranga_csrf=([^;]*)/)?.[1]||"";if(!token){{const csrf=await fetch("/csrf",{{credentials:"same-origin",cache:"no-store"}});const data=await csrf.json().catch(()=>({{}}));token=data.token||""}}const response=await fetch("/tts",{{method:"POST",credentials:"same-origin",headers:{{"Content-Type":"application/json","X-CSRF-Token":decodeURIComponent(token)}},body:JSON.stringify({{text,language}})}});if(!response.ok)throw new Error("tts");blob=await response.blob();if(!blob.size)throw new Error("tts-empty");if(speechTurn!==tripVoiceTurn)return false;if(tripVoiceCache.size>=8)tripVoiceCache.delete(tripVoiceCache.keys().next().value);tripVoiceCache.set(key,blob)}}if(speechTurn!==tripVoiceTurn)return false;const url=URL.createObjectURL(blob),audio=createTripVoiceAudio(url);tripVoiceAudio=audio;document.body.classList.add("assistant-speaking");let playbackOk=true;await new Promise(resolve=>{{const done=(ok=true)=>{{playbackOk=ok;if(tripVoiceAudio===audio)tripVoiceAudio=null;URL.revokeObjectURL(url);resolve()}};audio.onended=()=>done(true);audio.onerror=()=>done(false);audio.play().catch(()=>done(false))}});if(speechTurn!==tripVoiceTurn)return false;document.body.classList.remove("assistant-speaking");return playbackOk}}catch(_){{if(speechTurn!==tripVoiceTurn)return false;if("speechSynthesis" in window){{const u=new SpeechSynthesisUtterance(text);u.lang=language==="en"?"en-US":language==="wo"?"wo-SN":language==="ff"?"ff-SN":"fr-FR";u.rate=language==="wo"?0.90:language==="ff"?0.91:0.94;u.pitch=1;u.volume=1;window.speechSynthesis.cancel();window.speechSynthesis.speak(u);return true}}return false}}}}
function bindDayVoice(){{document.querySelectorAll("[data-day-voice]").forEach(button=>button.onclick=()=>speakTripText(daySpeechText(button.closest(".day-card"))))}} function bindDayPractical(){{document.querySelectorAll("[data-day-practical]").forEach(button=>button.onclick=()=>{{const card=button.closest(".day-card"),region=card?.querySelector(".day-region")?.value;if(!region)return;const select=document.getElementById("practical-region");if(select){{select.value=region;}}document.getElementById("practical").style.display="block";loadPractical(button.dataset.dayPractical,region,card?.querySelector(".day-title")?.value||"");document.getElementById("practical").scrollIntoView({{behavior:"smooth",block:"nearest"}})}})}}
function bindEditor(){{document.querySelectorAll('.day-region').forEach(select=>select.onchange=()=>{{syncEditor()}});document.querySelectorAll('[data-up]').forEach(b=>b.onclick=()=>{{syncEditor();const i=+b.closest('.day-card').dataset.day;if(i>0){{[currentPlan.days[i-1],currentPlan.days[i]]=[currentPlan.days[i],currentPlan.days[i-1]];renumberDays();renderEditablePlan(currentPlan)}}}});document.querySelectorAll('[data-down]').forEach(b=>b.onclick=()=>{{syncEditor();const i=+b.closest('.day-card').dataset.day;if(i<currentPlan.days.length-1){{[currentPlan.days[i+1],currentPlan.days[i]]=[currentPlan.days[i],currentPlan.days[i+1]];renumberDays();renderEditablePlan(currentPlan)}}}});document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{{syncEditor();const i=+b.closest('.day-card').dataset.day;if(currentPlan.days.length>1){{currentPlan.days.splice(i,1);renumberDays();renderEditablePlan(currentPlan)}}}})}}
function renderPracticalSources(sources){{const box=document.getElementById("practical-sources");if(!box)return;if(!Array.isArray(sources)||!sources.length){{box.innerHTML="";return}}box.innerHTML='<strong>{practical_sources}</strong><ul class="practical-sources">'+sources.map(s=>'<li><a href="'+escapeHtml(s.url)+'" target="_blank" rel="noopener noreferrer">'+escapeHtml(s.title||s.url)+'</a></li>').join("")+'</ul>'}}
async function loadPractical(category,regionOverride="",dayTitle=""){{const region=regionOverride||document.getElementById("practical-region")?.value||"";if(!region)return;const statusBox=document.getElementById("practical-status"),answerBox=document.getElementById("practical-answer");statusBox.innerHTML='<p class="loading">{practical_loading}</p>';answerBox.textContent="";renderPracticalSources([]);try{{const r=await fetch("/api/practical-info",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{lang:"{lang}",region,category,day:dayTitle}})}});const data=await r.json();if(!r.ok)throw new Error(data.error||"error");answerBox.textContent=data.answer||"";document.getElementById("voice-practical-actions").style.display=data.answer?"flex":"none";renderPracticalSources(data.sources||[]);statusBox.textContent="{practical_checked} "+(data.checked_at||"");}}catch(_err){{statusBox.innerHTML='<p class="error">{practical_error}</p>';}}}}
document.querySelectorAll("[data-practical]").forEach(button=>button.onclick=()=>loadPractical(button.dataset.practical)); document.getElementById("voice-itinerary").onclick=()=>speakTripText([currentPlan?.summary||"",...(currentPlan?.days||[]).map(d=>[d.title,d.morning,d.afternoon,d.evening,d.transport].filter(Boolean).join(". "))].filter(Boolean).join(". ")); document.getElementById("voice-stop").onclick=stopTripSpeech; document.getElementById("voice-practical").onclick=()=>speakTripText(document.getElementById("practical-answer")?.textContent||""); document.getElementById("voice-practical-stop").onclick=stopTripSpeech;\ndocument.getElementById('add-day').onclick=()=>{{syncEditor();currentPlan.days.push({{day:currentPlan.days.length+1,title:'Nouvelle étape',region:'',morning:'',afternoon:'',evening:'',transport:''}});renderEditablePlan(currentPlan)}};
function refreshShareLink(){{if(!currentPlan)return;const payload={{lang:'{lang}',arrival:form.arrival.value,departure:form.departure.value,adults:+form.adults.value,children:+form.children.value,interests:[...document.querySelectorAll('input[name="interests"]:checked')].map(x=>x.value),budget:document.querySelector('input[name="budget"]:checked')?.value||'Confort',pace:document.querySelector('input[name="pace"]:checked')?.value||'Équilibré',regions:[...document.querySelectorAll('input[name="regions"]:checked')].map(x=>x.value),context_place:sessionStorage.getItem('teranga-place-name')||'',audience:audience,surprise:document.getElementById('surprise').checked,edited_plan:currentPlan}};const encoded=encodeTrip(payload);history.replaceState(null,'','/trip-planner?lang='+encodeURIComponent('{lang}')+'#trip='+encoded);document.getElementById('share').style.display='block';document.getElementById('copy').onclick=async()=>{{await navigator.clipboard.writeText(location.href);document.getElementById('copy').textContent='{copied}';}}}};
document.getElementById('save-trip').onclick=()=>{{syncEditor();renumberDays();try{{sessionStorage.setItem('teranga-trip-plan',JSON.stringify(currentPlan))}}catch(_){{}}updateJourneySteps();updatePracticalRegions();updateMapFromPlan();refreshShareLink();status.textContent='Modifications enregistrées pour cette session.'}};
function encodeTrip(payload){{const bytes=new TextEncoder().encode(JSON.stringify(payload));let binary='';bytes.forEach(byte=>binary+=String.fromCharCode(byte));return btoa(binary).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'')}}
function decodeTrip(value){{try{{const base64=value.replace(/-/g,'+').replace(/_/g,'/');const padded=base64+'='.repeat((4-base64.length%4)%4);const binary=atob(padded);const bytes=Uint8Array.from(binary,char=>char.charCodeAt(0));return JSON.parse(new TextDecoder().decode(bytes))}}catch(_error){{return null}}}}
function applySharedTrip(){{const encoded=new URLSearchParams(location.hash.slice(1)).get('trip');if(!encoded)return;const payload=decodeTrip(encoded);if(!payload||typeof payload!=='object')return;for(const key of ['arrival','departure','adults','children']){{if(payload[key]!==undefined&&form.elements[key])form.elements[key].value=payload[key]}}for(const key of ['interests','regions']){{if(!Array.isArray(payload[key]))continue;document.querySelectorAll('input[name="'+key+'"]').forEach(input=>{{input.checked=payload[key].includes(input.value)}})}}for(const key of ['budget','pace']){{if(typeof payload[key]!=='string')continue;const input=document.querySelector('input[name="'+key+'"][value="'+CSS.escape(payload[key])+'"]');if(input)input.checked=true}}const surprise=document.getElementById('surprise');if(surprise)surprise.checked=Boolean(payload.surprise);if(typeof payload.audience==='string'&&AUDIENCE_VALUES.includes(payload.audience)){{try{{localStorage.setItem('teranga-audience',payload.audience)}}catch(_){{}}}}if(payload.edited_plan&&Array.isArray(payload.edited_plan.days)){{currentPlan=payload.edited_plan;renderEditablePlan(currentPlan);document.getElementById('voice-result-actions').style.display='flex';document.getElementById('share').style.display='block';updateJourneySteps();updatePracticalRegions();updateMapFromPlan();}}}}
applySharedTrip();
form.onsubmit=async e=>{{e.preventDefault(); if(!form.reportValidity())return;
const payload={{lang:'{lang}',arrival:form.arrival.value,departure:form.departure.value,adults:+form.adults.value,children:+form.children.value,
interests:[...document.querySelectorAll('input[name="interests"]:checked')].map(x=>x.value),budget:document.querySelector('input[name="budget"]:checked')?.value||'Confort',
pace:document.querySelector('input[name="pace"]:checked')?.value||'Équilibré',
regions:[...document.querySelectorAll('input[name="regions"]:checked')].map(x=>x.value),context_place:sessionStorage.getItem('teranga-place-name')||'',audience:audience,surprise:document.getElementById('surprise').checked}};
status.innerHTML='<p class="loading">{loading}</p>'; result.textContent='';
try{{const r=await fetch('/api/trip-planner',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});const data=await r.json();if(!r.ok)throw new Error(data.error||'error');const p=data.plan||{{summary:data.itinerary,days:[],practical_notes:[]}};window.__tripBudgetLines=data.budget?.lines||[];renderEditablePlan(p);document.getElementById("voice-result-actions").style.display="flex";status.textContent='';document.getElementById('map').innerHTML=data.map_html||'';document.getElementById('share').style.display='block';syncEditor();payload.edited_plan=currentPlan;const encoded=encodeTrip(payload);const shareLang=payload.lang==='en'?'en':'fr';history.replaceState(null,'','/trip-planner?lang='+shareLang+'#trip='+encoded);document.getElementById('copy').onclick=async()=>{{await navigator.clipboard.writeText(location.href);document.getElementById('copy').textContent='{copied}';}};}}
catch(err){{status.innerHTML='<p class="error">{error}</p>';}}
}};
</script></body></html>""".format(
        lang=escape(lang), site=escape(site_url), title=escape(t["title"]), intro=escape(t["intro"]),
        kicker=escape(t["kicker"]), dates=escape(t["dates"]), travelers=escape(t["travelers"]),
        interests=escape(t["interests"]), budget=escape(t["budget"]), regions=escape(t["regions"]),
        pace=escape(t["pace"]), start=escape(t["start"]), cont=escape(t["continue"]),
        generate=escape(t["generate"]), result=escape(t["result"]), back=escape(t["back"]),
        error=escape(t["error"]), day=escape(t["day"]), morning=escape(t["morning"]), afternoon=escape(t["afternoon"]), evening=escape(t["evening"]), transport=escape(t["transport"]), budget_summary=escape(t["budget_summary"]), **{"from": escape(t["from"]), "to": escape(t["to"]), "adults": escape(t["adults"])},
        children=escape(t["children"]), loading=escape(t["loading"]), copied=escape(t["copied"]), note=escape(t["note"]), map_title=escape(t["map_title"]), share=escape(t.get("share", "Share this trip")), practical_title=escape(t["practical_title"]), practical_intro=escape(t["practical_intro"]), practical_region=escape(t["practical_region"]), practical_transport=escape(t["practical_transport"]), practical_hours=escape(t["practical_hours"]), practical_prices=escape(t["practical_prices"]), practical_procedures=escape(t["practical_procedures"]), practical_services=escape(t["practical_services"]), practical_loading=escape(t["practical_loading"]), practical_error=escape(t["practical_error"]), practical_checked=escape(t["practical_checked"]), practical_sources=escape(t["practical_sources"]), voice_listen=escape(t["voice_listen"]), voice_stop=escape(t["voice_stop"]), interests_html=_option_list(t["interest_options"], "interests"),
        budget_html=_option_list(t["budget_options"], "budget", "radio"), pace_html=_option_list(t["pace_options"], "pace", "radio"),
        regions_html=_option_list(t["region_options"], "regions"), surprise=escape(t["surprise"]), region_options_json=json.dumps(t["region_options"], ensure_ascii=False), region_coords_json=json.dumps(REGION_COORDS, ensure_ascii=False), add_day=escape(t["add_day"]), save_edits=escape(t["save_edits"]), remove_day=escape(t["remove_day"])
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

def _map_html(regions, title="Carte du voyage"):
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
    return f'<iframe title="{escape(title)}" width="100%" height="320" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik"></iframe>'
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
Selected place context: {data.get('context_place') or 'none'}
User profile: {data.get('audience') or 'tourist'} (explicit preference; adapt priorities without inferring personal facts)
Surprise me: {data['surprise']}

Return ONLY valid JSON in the user's language. Schema: {{"summary": string, "days": [{{"day": number, "title": string, "region": string, "morning": string, "afternoon": string, "evening": string, "transport": string}}], "practical_notes": [string]}}. Create one object per travel day.
Include sensible travel pacing, approximate budget categories without inventing fixed current prices, and practical notes.
Do not claim current opening hours, fares, availability, visa rules or weather unless explicitly verified from live sources.
Do not invent hotels, restaurants, transport operators or reservations. If a recommendation needs current verification, say so.
If dates or preferences are inconsistent, explain the issue briefly.
"""

def _practical_prompt(lang, region, category, day=""):
    labels = {
        "fr": {"transport": "transport", "hours": "horaires et heures d'ouverture", "prices": "prix et tarifs", "procedures": "démarches et documents utiles", "services": "services utiles"},
        "en": {"transport": "transport", "hours": "hours and opening times", "prices": "prices and fares", "procedures": "procedures and useful documents", "services": "useful services"},
    }
    topic = labels.get(lang, labels["fr"]).get(category, category)
    return f"""{language_instruction(lang)}\n\nGive a concise, practical answer about {topic} in {region}, Senegal. Day activity context: {day or "none"}. Use live web search and prioritize official or operator sources when available. Distinguish verified current facts from estimates or uncertainty. Never invent a price, schedule, phone number, address, availability or procedure. Mention when information should be rechecked before travel. If a day activity is supplied, use it only as context and do not assume it is a confirmed venue or booking. Do not include URLs in the answer because sources are returned separately.\n"""


def _practical_info(client, lang, region, category, day=""):
    model = "gpt-5.6-luna"
    response = client.responses.create(
        model=model,
        input=_practical_prompt(lang, region, category, day),
        max_output_tokens=700,
        reasoning={"effort": "low"},
        truncation="auto",
        tools=[{"type": "web_search", "search_context_size": "medium"}],
    )
    answer = getattr(response, "output_text", "") or ""
    return answer[:5000], extract_sources(response)


def register_trip_planner(app, client, site_url, allowed_origins=None):
    configured_origins = {str(origin).rstrip("/") for origin in (allowed_origins or {site_url}) if str(origin).strip()}

    @app.post("/api/practical-info")
    def api_practical_info():
        content_length = request.content_length
        if content_length is not None and content_length > 4000:
            return jsonify({"error": "Requête trop volumineuse."}), 413
        if not origin_allowed(request.headers.get("Origin"), request.headers.get("Referer"), configured_origins):
            return jsonify({"error": "Origine non autorisée."}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Requête invalide."}), 400
        lang = str(body.get("lang", "fr")).lower()[:2]
        if lang not in UI_LANGS:
            lang = "fr"
        region = str(body.get("region", "")).strip()
        category = str(body.get("category", "")).strip().lower()
        day = str(body.get("day", "")).strip()[:300]
        if region not in REGION_COORDS:
            return jsonify({"error": "Région invalide."}), 400
        if category not in {"transport", "hours", "prices", "procedures", "services"}:
            return jsonify({"error": "Catégorie invalide."}), 400
        try:
            answer, sources = _practical_info(client, lang, region, category, day)
            return jsonify({"answer": answer, "sources": sources, "checked_at": date.today().isoformat(), "region": region, "category": category})
        except Exception:
            return jsonify({"error": "Impossible de récupérer les informations pratiques."}), 502

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
        audience = str(body.get("audience", "tourist")).lower()[:16]
        if audience not in {"tourist", "resident", "diaspora", "merchant"}:
            audience = "tourist"
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
                "budget": budget, "pace": pace, "audience": audience, "context_place": str(body.get("context_place", ""))[:120], "surprise": body.get("surprise") is True}
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
                "map_html": _map_html(regions, "Trip map" if lang == "en" else "Carte du voyage"),
            })
        except Exception:
            app.logger.exception("trip-planner")
            return jsonify({"error": "Impossible de générer le voyage pour le moment."}), 502
