import json
import os
import re
from html import escape
from flask import Response, jsonify, request, stream_with_context
from datetime import date

from services.http_security import origin_allowed
from services.site_layout import HEAD_ASSETS, site_footer, site_header
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
        "title": "Planificateur de voyage au Sénégal",
        "kicker": "Teranga AI · Voyage au Sénégal",
        "intro": "Construis un itinéraire personnalisé en quelques étapes.",
        "dates": "Dates", "travelers": "Voyageurs", "interests": "Centres d'intérêt",
        "budget": "Budget", "regions": "Régions", "pace": "Rythme",
        "start": "Créer mon voyage", "continue": "Continuer", "generate": "Générer mon itinéraire",
        "result": "Ton voyage est prêt", "back": "Modifier", "error": "Impossible de générer le voyage pour le moment.", "practical_title": "Infos pratiques", "practical_intro": "Vérifie transport, horaires, prix, démarches et services avec des sources web.", "practical_region": "Région", "practical_transport": "Transport", "practical_hours": "Horaires", "practical_prices": "Prix", "practical_procedures": "Démarches", "practical_services": "Services", "practical_loading": "Recherche web en cours…", "practical_error": "Impossible de récupérer les informations pratiques.", "practical_checked": "Vérifié le", "practical_sources": "Sources", "voice_listen": "Écouter", "voice_stop": "Arrêter",
        "from": "Arrivée", "to": "Départ", "date_error": "La date de départ doit être après la date d'arrivée.", "adults": "Adultes", "children": "Enfants",
        "budget_options": ["Économique", "Confort", "Premium", "Luxe"],
        "pace_options": ["Relax", "Équilibré", "Intensif"],
        "interest_options": ["Plages", "Culture & histoire", "Cuisine", "Nature", "Dakar", "Îles", "Faune", "Musique & vie nocturne", "Famille"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Laisser Teranga AI choisir", "places_label": "Fiches lieux :", "share": "🔗 Partager ces préférences", "add_day": "+ Ajouter une journée", "save_edits": "Enregistrer les modifications", "review_chat": "💬 Demander à Teranga de revoir mon séjour", "remove_day": "Supprimer", "loading": "Teranga AI prépare ton voyage…", "copied": "✓ Lien copié", "note": "Les estimations et informations susceptibles de changer doivent être vérifiées avant le départ.", "map_title": "Carte du voyage", "day": "Jour", "morning": "Matin", "afternoon": "Après-midi", "evening": "Soir", "transport": "Transport", "budget_summary": "Budget indicatif", 
    },
    "en": {
        "title": "Senegal Trip Planner", "kicker": "Teranga AI · Travel Senegal",
        "intro": "Build a personalized Senegal itinerary in a few steps.",
        "dates": "Dates", "travelers": "Travelers", "interests": "Interests", "budget": "Budget", "regions": "Regions", "pace": "Pace",
        "start": "Create my trip", "continue": "Continue", "generate": "Generate my itinerary", "result": "Your trip is ready",
        "back": "Edit", "error": "We could not generate the trip right now.", "date_error": "Departure must be after arrival.", "from": "Arrival", "to": "Departure",
        "adults": "Adults", "children": "Children",
        "budget_options": ["Budget", "Comfort", "Premium", "Luxury"], "pace_options": ["Relaxed", "Balanced", "Intensive"],
        "interest_options": ["Beaches", "Culture & history", "Food", "Nature", "Dakar", "Islands", "Wildlife", "Music & nightlife", "Family"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Let Teranga AI choose", "places_label": "Place guides:", "share": "🔗 Share these preferences", "add_day": "+ Add a day", "save_edits": "Save changes", "review_chat": "💬 Ask Teranga to review my trip", "remove_day": "Remove", "loading": "Teranga AI is preparing your trip…", "copied": "✓ Link copied", "note": "Estimates and information that may change should be verified before departure.", "map_title": "Trip map", "day": "Day", "morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "transport": "Transport", "budget_summary": "Indicative budget", "practical_title": "Practical info", "practical_intro": "Check transport, hours, prices, procedures and services with web sources.", "practical_region": "Region", "practical_transport": "Transport", "practical_hours": "Hours", "practical_prices": "Prices", "practical_procedures": "Procedures", "practical_services": "Services", "practical_loading": "Searching the web…", "practical_error": "We could not retrieve practical information.", "practical_checked": "Checked", "practical_sources": "Sources", "voice_listen": "Listen", "voice_stop": "Stop",
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
<meta name="description" content="{intro}">
<meta property="og:description" content="{intro}">
<title>{title} | Teranga AI</title>
{head}
<style>
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,sans-serif}}
main{{width:min(920px,calc(100% - 28px));margin:auto;padding:28px 0 70px}}
.kicker{{color:var(--gold);font-size:12px;letter-spacing:.13em;text-transform:uppercase;font-weight:900}}
h1{{font:600 clamp(34px,6vw,54px)/1.04 var(--font-display);letter-spacing:-.02em;margin:9px 0 14px}}.intro{{color:var(--muted);font-size:18px}}
.card{{margin-top:22px;background:var(--surface);border:1px solid var(--line);border-radius:28px;padding:24px}}
section{{border-top:0;padding:0}}.step{{display:none}}.step.active{{display:block}}h2{{font-size:24px;margin:0 0 16px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}
label.field{{display:flex;flex-direction:column;gap:7px;color:var(--muted);font-size:14px}}
input[type=date],input[type=number]{{width:100%;background:var(--bg);border:1px solid var(--line);color:var(--text);border-radius:13px;padding:13px;font:inherit}}
.chips{{display:flex;flex-wrap:wrap;gap:10px}}.chip input{{position:absolute;opacity:0}}.chip span{{display:block;padding:11px 14px;border:1px solid var(--line);border-radius:999px;cursor:pointer;color:var(--muted)}}.chip input:checked+span{{border-color:var(--accent);color:var(--text);background:var(--accent-soft)}}
.actions{{display:flex;justify-content:space-between;gap:12px;margin-top:24px}}button{{border:0;border-radius:14px;padding:13px 18px;font:800 15px system-ui;cursor:pointer}}.primary{{background:var(--accent);color:var(--accent-ink)}}.secondary{{background:var(--surface-2);color:var(--ink);border:1px solid var(--line)}}
.result{{white-space:pre-wrap;font-family:inherit;line-height:1.7}}.day-editor{{display:grid;gap:10px;margin-top:14px}}.day-card{{background:var(--surface-2);border:1px solid var(--line);border-radius:18px;padding:16px}}.day-card h3{{margin:0 0 10px}}.day-title{{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px;font:inherit}}.day-region{{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}}.journey-steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:14px}}.journey-step{{background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:10px}}.route-visual{{margin-top:14px;background:var(--surface-2);border:1px solid var(--line);border-radius:18px;padding:10px;overflow:hidden}}.route-visual svg{{display:block;width:100%;height:210px}}.route-line{{fill:none;stroke:var(--accent);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:6 6}}.route-point{{fill:var(--surface);stroke:var(--accent);stroke-width:3}}.route-label{{fill:var(--text);font:700 11px system-ui,sans-serif}}.journey-step strong{{display:block;color:var(--gold);font-size:12px}}.journey-step span{{display:block;margin-top:3px}}.day-card textarea{{width:100%;min-height:62px;resize:vertical;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}}.day-card label{{display:block;margin-top:9px;color:var(--muted);font-size:13px}}.day-actions{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}}.day-practical{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}.day-practical button{{padding:7px 9px;font-size:12px}}.day-actions button{{padding:8px 11px;font-size:13px}}.map{{margin-top:16px;border-radius:18px;overflow:hidden;border:1px solid var(--line)}}.map:empty,.route-visual:empty,.journey-steps:empty{{display:none}}.loading{{color:var(--gold)}}.error{{color:var(--sen-red);margin-top:12px}}
.small{{font-size:12px;color:var(--muted);margin-top:14px}}.practical{{margin-top:18px;padding:16px;background:var(--surface-2);border:1px solid var(--line);border-radius:18px}}.practical h3{{margin:0 0 6px}}.practical-intro{{color:var(--muted);font-size:13px;margin:0 0 12px}}.practical-controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}.practical-controls select{{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px}}.practical-controls button{{padding:9px 11px;font-size:13px}}.practical-answer{{margin-top:14px;white-space:pre-wrap}}.practical-sources{{margin:12px 0 0;padding-left:18px;font-size:13px}}.practical-sources a{{color:var(--gold)}}.voice-actions{{display:flex;gap:8px;margin-top:10px}}.voice-actions button{{padding:8px 11px;font-size:13px}}
.place-context{{margin:0 0 16px;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--bg);color:var(--muted)}}.place-context strong{{color:var(--ink)}}@media(max-width:560px){{main{{width:min(100% - 20px,920px);padding-top:18px}}.card{{padding:18px;border-radius:22px}}.actions{{flex-direction:column}}.actions button{{width:100%}}.day-card{{padding:13px}}.day-actions button,.day-practical button,.voice-actions button{{min-height:42px}}.practical-controls{{align-items:stretch}}.practical-controls select,.practical-controls button{{width:100%;min-height:42px}}.journey-steps{{grid-template-columns:1fr}}.route-visual svg{{height:180px}}}}@media(max-width:360px){{h1{{font-size:32px}}.intro{{font-size:16px}}.chips{{gap:7px}}.chip span{{padding:10px 12px}}}}</style></head>
<body>{header}<main>
<div class="kicker">{kicker}</div><h1>{title}</h1><p class="intro">{intro}</p><div id="place-context" class="place-context" hidden></div><div id="trip-edit-proposal" class="place-context" hidden></div>
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
<div id="status"></div><div class="voice-actions" id="voice-result-actions" style="display:none"><button id="voice-itinerary" class="secondary" type="button">{voice_listen}</button><button id="voice-stop" class="secondary" type="button">{voice_stop}</button></div><div id="result" class="result"></div><div id="route-visual" class="route-visual" style="display:none"></div><div id="journey-steps" class="journey-steps"></div><section id="practical" class="practical" style="display:none"><h3>{practical_title}</h3><p class="practical-intro">{practical_intro}</p><div class="practical-controls"><label class="field" style="min-width:150px">{practical_region}<select id="practical-region"></select></label><button type="button" class="secondary" data-practical="transport">{practical_transport}</button><button type="button" class="secondary" data-practical="hours">{practical_hours}</button><button type="button" class="secondary" data-practical="prices">{practical_prices}</button><button type="button" class="secondary" data-practical="procedures">{practical_procedures}</button><button type="button" class="secondary" data-practical="services">{practical_services}</button></div><div id="practical-status"></div><div class="voice-actions" id="voice-practical-actions" style="display:none"><button id="voice-practical" class="secondary" type="button">{voice_listen}</button><button id="voice-practical-stop" class="secondary" type="button">{voice_stop}</button></div><div id="practical-answer" class="practical-answer"></div><div id="practical-sources"></div></section><div id="editor-actions" class="actions" style="display:none"><button id="add-day" class="secondary" type="button">{add_day}</button><button id="save-trip" class="secondary" type="button">{save_edits}</button><button id="review-chat" class="secondary" type="button">{review_chat}</button></div><div id="share" style="display:none;margin-top:16px"><button id="copy" class="secondary" type="button">{share}</button></div><div id="map" class="map"></div>
</div><p class="small">{note}</p>
</main>{footer}
<script>
// Stockage sûr (mode privé, cookies bloqués) : jamais d'exception, repli mémoire.
const safeStore=kind=>{{let store=null;const mem=new Map();try{{store=window[kind];store.setItem('__t','1');store.removeItem('__t');}}catch(_){{store=null;}}return{{getItem:k=>{{try{{if(store)return store.getItem(k);}}catch(_){{}}return mem.has(k)?mem.get(k):null;}},setItem:(k,v)=>{{mem.set(k,String(v));try{{if(store)store.setItem(k,String(v));}}catch(_){{}}}},removeItem:k=>{{mem.delete(k);try{{if(store)store.removeItem(k);}}catch(_){{}}}}}};}};
const LS=safeStore('localStorage'),SS=safeStore('sessionStorage');
const escapeHtml=s=>String(s||'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); const form=document.getElementById('planner'), steps=[...document.querySelectorAll('.step')], status=document.getElementById('status'), result=document.getElementById('result'); const arrivalInput=form.querySelector('input[name="arrival"]'), departureInput=form.querySelector('input[name="departure"]'); let current=0;
function show(i){{current=Math.max(0,Math.min(i,steps.length-1));steps.forEach((s,n)=>s.classList.toggle('active',n===current));window.scrollTo({{top:0,behavior:'smooth'}})}}
function validDateStep(){{const arrival=String(arrivalInput?.value||'');const departure=String(departureInput?.value||'');if(!arrival||!departure){{status.textContent="{date_required}";if(!arrival)arrivalInput?.focus();else departureInput?.focus();return false}}if(arrival>=departure){{status.textContent="{date_error}";departureInput?.focus();return false}}status.textContent='';return true}}
arrivalInput?.addEventListener('change',()=>{{if(arrivalInput.value)departureInput?.setAttribute('min',arrivalInput.value)}});\ndocument.querySelectorAll('[data-next]').forEach(b=>b.addEventListener('click',()=>{{
  if(current===0){{if(!validDateStep())return}}else if(!form.reportValidity())return;
  show(current+1);
}}));
document.querySelectorAll('[data-prev]').forEach(b=>b.addEventListener('click',()=>show(current-1)));
let currentPlan=null;
const AUDIENCE_VALUES=["tourist","resident","diaspora","merchant"]; const contextPlaceQuery=new URL(window.location.href).searchParams.get('context_place')||''; if(contextPlaceQuery){{try{{SS.setItem('teranga-place-name',contextPlaceQuery.slice(0,120))}}catch(_){{}}}} const audienceStored=LS.getItem('teranga-audience'); const audienceQuery=new URL(window.location.href).searchParams.get('audience'); const audience=AUDIENCE_VALUES.includes(audienceStored)?audienceStored:(AUDIENCE_VALUES.includes(audienceQuery)?audienceQuery:'tourist'); if(audience!==audienceStored){{try{{LS.setItem('teranga-audience',audience)}}catch(_){{}}}}\nconst REGION_OPTIONS={region_options_json};
const placeContextBox=document.getElementById("place-context"); const placeContextName=(()=>{{try{{return SS.getItem("teranga-place-name")||""}}catch(_){{return ""}}}})(); if(placeContextBox&&placeContextName){{placeContextBox.hidden=false;placeContextBox.innerHTML="<strong>Point de départ :</strong> "+escapeHtml(placeContextName)+"<br><span>Ce repère guide le voyage sans modifier tes choix automatiquement.</span>"}}
const REGION_COORDS={region_coords_json};
const journeySteps=document.getElementById("journey-steps");
function renumberDays(){{if(!currentPlan)return;currentPlan.days.forEach((d,i)=>d.day=i+1)}}
function regionOptionsHtml(selected){{return REGION_OPTIONS.map(region=>"<option value=\\""+escapeHtml(region)+"\\""+(region===selected?" selected":"")+">"+escapeHtml(region)+"</option>").join("")}}
function updatePracticalRegions(){{const select=document.getElementById("practical-region");if(!select)return;const regions=[...new Set((currentPlan?.days||[]).map(d=>d.region).filter(Boolean))];const previous=select.value;select.innerHTML=regions.map(r=>"<option value=\\""+escapeHtml(r)+"\\">"+escapeHtml(r)+"</option>").join("");if(previous&&regions.includes(previous))select.value=previous;else if(regions.length)select.value=regions[0]}}
function updateJourneySteps(){{if(!journeySteps)return;journeySteps.innerHTML=(currentPlan?.days||[]).map((d,i)=>"<div class=\\"journey-step\\"><strong>{day} "+(i+1)+"</strong><span>"+escapeHtml(d.region||"—")+"</span></div>").join("");updateRouteVisual()}}
function updateRouteVisual(){{const points=(currentPlan?.days||[]).map((d,i)=>{{const coord=REGION_COORDS[d.region];return coord?{{day:i+1,region:d.region,lat:coord[0],lon:coord[1]}}:null}}).filter(Boolean);const box=document.getElementById("route-visual");if(!box)return;if(!points.length){{box.style.display="none";box.innerHTML="";return}}const lats=points.map(p=>p.lat),lons=points.map(p=>p.lon),minLat=Math.min(...lats),maxLat=Math.max(...lats),minLon=Math.min(...lons),maxLon=Math.max(...lons),latSpan=Math.max(maxLat-minLat,.1),lonSpan=Math.max(maxLon-minLon,.1),pad=.12;const project=(lat,lon)=>[10+((lon-(minLon-lonSpan*pad))/(lonSpan*(1+2*pad)))*80,200-(10+((lat-(minLat-latSpan*pad))/(latSpan*(1+2*pad)))*180)];const xy=points.map(p=>project(p.lat,p.lon));const path=xy.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(" ");box.style.display="block";box.innerHTML="<svg viewBox=\\"0 0 100 210\\" preserveAspectRatio=\\"none\\" aria-label=\\""+escapeHtml("{map_title}")+"\\"><path class=\\"route-line\\" d=\\""+path+"\\"/>"+xy.map((p,i)=>"<circle class=\\"route-point\\" cx=\\""+p[0].toFixed(1)+"\\" cy=\\""+p[1].toFixed(1)+"\\" r=\\"4.5\\"/><text class=\\"route-label\\" x=\\""+Math.min(p[0]+3,82).toFixed(1)+"\\" y=\\""+Math.max(p[1]-7,12).toFixed(1)+"\\">"+(i+1)+" · "+escapeHtml(points[i].region)+"</text>").join("")+"</svg>"}}
function updateMapFromPlan(){{const regions=[...new Set((currentPlan?.days||[]).map(d=>d.region).filter(region=>REGION_COORDS[region]))];if(!regions.length)return;const points=regions.map(region=>REGION_COORDS[region]);const lats=points.map(point=>point[0]),lons=points.map(point=>point[1]),margin=.8;const west=Math.min(...lons)-margin,south=Math.min(...lats)-margin,east=Math.max(...lons)+margin,north=Math.max(...lats)+margin;const bbox=[west,south,east,north].map(value=>value.toFixed(4)).join("%2C");document.getElementById("map").innerHTML="<iframe title=\\""+escapeHtml("{map_title}")+"\\" width=\\"100%\\" height=\\"320\\" loading=\\"lazy\\" src=\\"https://www.openstreetmap.org/export/embed.html?bbox="+bbox+"&layer=mapnik\\"></iframe>"}}
function persistTripContext(){{if(!currentPlan)return;const clip=(value,max)=>String(value||"").replace(/\\s+/g," ").trim().slice(0,max);const compact={{summary:clip(currentPlan.summary,220),days:[]}};for(let i=0;i<(currentPlan.days||[]).length&&i<14;i++){{const d=currentPlan.days[i]||{{}};const day={{day:i+1,region:clip(d.region,45),title:clip(d.title,80),morning:clip(d.morning,95),afternoon:clip(d.afternoon,95),evening:clip(d.evening,75),transport:clip(d.transport,65)}};const candidate={{summary:compact.summary,days:[...compact.days,day]}};if(JSON.stringify(candidate).length>1550)break;compact.days.push(day)}}try{{SS.setItem("teranga-trip-context",JSON.stringify(compact))}}catch(_){{}}}}
function placeLinks(d){{const p=Array.isArray(d.places)?d.places:[];return p.length?'<p class="day-places">{places_label} '+p.map(x=>'<a href="'+'/lieux/'+encodeURIComponent(x.id)+'" target="_blank" rel="noopener">'+escapeHtml(x.name)+'</a>').join(' · ')+'</p>':''}}
function renderEditablePlan(plan){{currentPlan=JSON.parse(JSON.stringify(plan||{{summary:"",days:[],practical_notes:[]}}));renumberDays();result.innerHTML='<h2>'+escapeHtml(currentPlan.summary||'')+'</h2><div class="day-editor">'+currentPlan.days.map((d,i)=>'<article class="day-card" data-day="'+i+'"><h3>{day} '+(i+1)+' · <input class="day-title" value="'+escapeHtml(d.title||'').replace(/"/g,'&quot;')+'"></h3><label>{regions}<select class="day-region">'+regionOptionsHtml(d.region||'')+'</select></label><label>{morning}<textarea class="day-morning">'+escapeHtml(d.morning||'')+'</textarea></label><label>{afternoon}<textarea class="day-afternoon">'+escapeHtml(d.afternoon||'')+'</textarea></label><label>{evening}<textarea class="day-evening">'+escapeHtml(d.evening||'')+'</textarea></label><label>{transport}<textarea class="day-transport">'+escapeHtml(d.transport||'')+'</textarea></label>'+placeLinks(d)+'<div class="day-actions"><button type="button" data-up>↑</button><button type="button" data-down>↓</button><button type="button" data-remove>{remove_day}</button></div><div class="voice-actions"><button type="button" class="secondary" data-day-voice>{voice_listen}</button></div><div class="day-practical"><button type="button" data-day-practical="transport">{practical_transport}</button><button type="button" data-day-practical="hours">{practical_hours}</button><button type="button" data-day-practical="prices">{practical_prices}</button></div></article>').join('')+'</div><h3>{budget_summary}</h3><ul>'+((window.__tripBudgetLines||[]).map(x=>'<li>'+escapeHtml(x)+'</li>').join(''))+'</ul>';document.getElementById('editor-actions').style.display='flex';bindEditor();bindDayPractical();bindDayVoice();updateJourneySteps();updatePracticalRegions();updateMapFromPlan();document.getElementById("practical").style.display=currentPlan.days.some(d=>d.region)?"block":"none";window.__editablePlan=currentPlan;persistTripContext()}}
function syncEditor(){{if(!currentPlan)return;document.querySelectorAll('.day-card').forEach(card=>{{const i=+card.dataset.day,d=currentPlan.days[i];if(!d)return;d.title=card.querySelector('.day-title').value.trim();d.morning=card.querySelector('.day-morning').value.trim();d.afternoon=card.querySelector('.day-afternoon').value.trim();d.evening=card.querySelector('.day-evening').value.trim();d.transport=card.querySelector('.day-transport').value.trim();d.region=card.querySelector('.day-region').value}});updateJourneySteps();updatePracticalRegions();updateMapFromPlan();persistTripContext()}}
function daySpeechText(card){{if(!card)return "";const title=card.querySelector(".day-title")?.value||"";const fields=["day-morning","day-afternoon","day-evening","day-transport"].map(c=>card.querySelector("."+c)?.value||"").filter(Boolean);return [title,...fields].filter(Boolean).join(". ")}} let tripVoiceTurn=0;let tripVoiceAudio=null;const tripVoiceCache=new Map();let tripVoiceOutputContext=null;
function createTripVoiceAudio(url){{const el=new Audio(url);el.preload="auto";el.setAttribute("playsinline","");el.volume=1;try{{const AC=window.AudioContext||window.webkitAudioContext;if(AC){{if(!tripVoiceOutputContext)tripVoiceOutputContext=new AC();if(tripVoiceOutputContext.state==="suspended")tripVoiceOutputContext.resume().catch(()=>{{}});const source=tripVoiceOutputContext.createMediaElementSource(el),gain=tripVoiceOutputContext.createGain(),compressor=tripVoiceOutputContext.createDynamicsCompressor();gain.gain.value=1.08;compressor.threshold.value=-18;compressor.knee.value=18;compressor.ratio.value=2.5;compressor.attack.value=.003;compressor.release.value=.18;source.connect(gain);gain.connect(compressor);compressor.connect(tripVoiceOutputContext.destination)}}}}catch(_){{el.volume=1}}return el}}
function stopTripSpeech(){{tripVoiceTurn++;if(tripVoiceAudio){{try{{tripVoiceAudio.pause()}}catch(_){{}}const src=tripVoiceAudio.src;tripVoiceAudio=null;if(src)URL.revokeObjectURL(src)}}if("speechSynthesis" in window)window.speechSynthesis.cancel();document.body.classList.remove("assistant-speaking")}}
async function speakTripText(text){{if(!text)return false;stopTripSpeech();const speechTurn=tripVoiceTurn;const language="{lang}";try{{const key=language+"|"+text;let blob=tripVoiceCache.get(key);if(!blob){{let token=document.cookie.match(/(?:^|; )teranga_csrf=([^;]*)/)?.[1]||"";if(!token){{const csrf=await fetch("/csrf",{{credentials:"same-origin",cache:"no-store"}});const data=await csrf.json().catch(()=>({{}}));token=data.token||""}}const response=await fetch("/tts",{{method:"POST",credentials:"same-origin",headers:{{"Content-Type":"application/json","X-CSRF-Token":decodeURIComponent(token)}},body:JSON.stringify({{text,language}})}});if(!response.ok)throw new Error("tts");blob=await response.blob();if(!blob.size)throw new Error("tts-empty");if(speechTurn!==tripVoiceTurn)return false;if(tripVoiceCache.size>=8)tripVoiceCache.delete(tripVoiceCache.keys().next().value);tripVoiceCache.set(key,blob)}}if(speechTurn!==tripVoiceTurn)return false;const url=URL.createObjectURL(blob),audio=createTripVoiceAudio(url);tripVoiceAudio=audio;document.body.classList.add("assistant-speaking");let playbackOk=true;await new Promise(resolve=>{{const done=(ok=true)=>{{playbackOk=ok;if(tripVoiceAudio===audio)tripVoiceAudio=null;URL.revokeObjectURL(url);resolve()}};audio.onended=()=>done(true);audio.onerror=()=>done(false);audio.play().catch(()=>done(false))}});if(speechTurn!==tripVoiceTurn)return false;document.body.classList.remove("assistant-speaking");return playbackOk}}catch(_){{if(speechTurn!==tripVoiceTurn)return false;if("speechSynthesis" in window){{const u=new SpeechSynthesisUtterance(text);u.lang=language==="en"?"en-US":language==="wo"?"wo-SN":language==="ff"?"ff-SN":"fr-FR";u.rate=language==="wo"?0.90:language==="ff"?0.91:0.94;u.pitch=1;u.volume=1;window.speechSynthesis.cancel();window.speechSynthesis.speak(u);return true}}return false}}}}
function bindDayVoice(){{document.querySelectorAll("[data-day-voice]").forEach(button=>button.onclick=()=>speakTripText(daySpeechText(button.closest(".day-card"))))}} function bindDayPractical(){{document.querySelectorAll("[data-day-practical]").forEach(button=>button.onclick=()=>{{const card=button.closest(".day-card"),region=card?.querySelector(".day-region")?.value;if(!region)return;const select=document.getElementById("practical-region");if(select){{select.value=region;}}document.getElementById("practical").style.display="block";loadPractical(button.dataset.dayPractical,region,card?.querySelector(".day-title")?.value||"");document.getElementById("practical").scrollIntoView({{behavior:"smooth",block:"nearest"}})}})}}
function bindEditor(){{document.querySelectorAll('.day-region').forEach(select=>select.onchange=()=>{{syncEditor()}});document.querySelectorAll('[data-up]').forEach(b=>b.onclick=()=>{{syncEditor();const i=+b.closest('.day-card').dataset.day;if(i>0){{[currentPlan.days[i-1],currentPlan.days[i]]=[currentPlan.days[i],currentPlan.days[i-1]];renumberDays();renderEditablePlan(currentPlan)}}}});document.querySelectorAll('[data-down]').forEach(b=>b.onclick=()=>{{syncEditor();const i=+b.closest('.day-card').dataset.day;if(i<currentPlan.days.length-1){{[currentPlan.days[i+1],currentPlan.days[i]]=[currentPlan.days[i],currentPlan.days[i+1]];renumberDays();renderEditablePlan(currentPlan)}}}});document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{{syncEditor();const i=+b.closest('.day-card').dataset.day;if(currentPlan.days.length>1){{currentPlan.days.splice(i,1);renumberDays();renderEditablePlan(currentPlan)}}}})}}
function renderPracticalSources(sources){{const box=document.getElementById("practical-sources");if(!box)return;if(!Array.isArray(sources)||!sources.length){{box.innerHTML="";return}}box.innerHTML='<strong>{practical_sources}</strong><ul class="practical-sources">'+sources.map(s=>'<li><a href="'+escapeHtml(s.url)+'" target="_blank" rel="noopener noreferrer">'+escapeHtml(s.title||s.url)+'</a></li>').join("")+'</ul>'}}
// Stockage bloqué (mode privé, cookies bloqués) : ne jamais faire échouer « Générer ».
function safePlaceName(){{try{{return SS.getItem('teranga-place-name')||''}}catch(_){{return ''}}}}
let practicalSeq=0;
async function loadPractical(category,regionOverride="",dayTitle=""){{const region=regionOverride||document.getElementById("practical-region")?.value||"";if(!region)return;const seq=++practicalSeq;const statusBox=document.getElementById("practical-status"),answerBox=document.getElementById("practical-answer");statusBox.innerHTML='<p class="loading">{practical_loading}</p>';answerBox.textContent="";renderPracticalSources([]);try{{const r=await fetch("/api/practical-info",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{lang:"{lang}",region,category,day:dayTitle}})}});const data=await r.json().catch(()=>({{}}));if(seq!==practicalSeq)return;if(!r.ok)throw new Error(data.error||"error");answerBox.textContent=data.answer||"";document.getElementById("voice-practical-actions").style.display=data.answer?"flex":"none";renderPracticalSources(data.sources||[]);statusBox.textContent="{practical_checked} "+(data.checked_at||"");}}catch(_err){{if(seq!==practicalSeq)return;statusBox.innerHTML='<p class="error">{practical_error}</p>';}}}}
document.querySelectorAll("[data-practical]").forEach(button=>button.onclick=()=>loadPractical(button.dataset.practical)); document.getElementById("voice-itinerary").onclick=()=>speakTripText([currentPlan?.summary||"",...(currentPlan?.days||[]).map(d=>[d.title,d.morning,d.afternoon,d.evening,d.transport].filter(Boolean).join(". "))].filter(Boolean).join(". ")); document.getElementById("voice-stop").onclick=stopTripSpeech; document.getElementById("voice-practical").onclick=()=>speakTripText(document.getElementById("practical-answer")?.textContent||""); document.getElementById("voice-practical-stop").onclick=stopTripSpeech;\ndocument.getElementById('add-day').onclick=()=>{{syncEditor();currentPlan.days.push({{day:currentPlan.days.length+1,title:'Nouvelle étape',region:'',morning:'',afternoon:'',evening:'',transport:''}});renderEditablePlan(currentPlan)}};
async function copyTripLink(){{const btn=document.getElementById('copy');try{{await navigator.clipboard.writeText(location.href);btn.textContent='{copied}';}}catch(_){{window.prompt('',location.href);}}}}function refreshShareLink(){{if(!currentPlan)return;const payload={{lang:'{lang}',arrival:form.arrival.value,departure:form.departure.value,adults:+form.adults.value,children:+form.children.value,interests:[...document.querySelectorAll('input[name="interests"]:checked')].map(x=>x.value),budget:document.querySelector('input[name="budget"]:checked')?.value||'Confort',pace:document.querySelector('input[name="pace"]:checked')?.value||'Équilibré',regions:[...document.querySelectorAll('input[name="regions"]:checked')].map(x=>x.value),context_place:safePlaceName(),audience:audience,surprise:document.getElementById('surprise').checked,edited_plan:currentPlan}};const encoded=encodeTrip(payload);history.replaceState(null,'','/trip-planner?lang='+encodeURIComponent('{lang}')+'#trip='+encoded);document.getElementById('share').style.display='block';document.getElementById('copy').onclick=copyTripLink}};
document.getElementById('review-chat').onclick=()=>{{syncEditor();try{{SS.setItem('teranga-journey','chat');SS.setItem('teranga-chat-prefill','Revois mon séjour et indique-moi les étapes qui semblent trop chargées, incohérentes ou difficiles à enchaîner.')}}catch(_){{}}window.location.href='/';}};
document.getElementById('save-trip').onclick=()=>{{syncEditor();renumberDays();try{{SS.setItem('teranga-trip-plan',JSON.stringify(currentPlan))}}catch(_){{}}updateJourneySteps();updatePracticalRegions();updateMapFromPlan();refreshShareLink();status.textContent='Modifications enregistrées pour cette session.'}};
function encodeTrip(payload){{const bytes=new TextEncoder().encode(JSON.stringify(payload));let binary='';bytes.forEach(byte=>binary+=String.fromCharCode(byte));return btoa(binary).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'')}}
function decodeTrip(value){{try{{const base64=value.replace(/-/g,'+').replace(/_/g,'/');const padded=base64+'='.repeat((4-base64.length%4)%4);const binary=atob(padded);const bytes=Uint8Array.from(binary,char=>char.charCodeAt(0));return JSON.parse(new TextDecoder().decode(bytes))}}catch(_error){{return null}}}}
function validateSharedPlan(plan){{if(!plan||typeof plan!=='object'||!Array.isArray(plan.days)||plan.days.length<1||plan.days.length>14)return null;const clean={{summary:String(plan.summary||'').slice(0,220),days:[]}};for(let i=0;i<plan.days.length;i++){{const day=plan.days[i];if(!day||typeof day!=='object')return null;const region=String(day.region||'').trim();if(region&&!REGION_OPTIONS.includes(region))return null;clean.days.push({{day:i+1,region:region.slice(0,60),title:String(day.title||'').slice(0,80),morning:String(day.morning||'').slice(0,95),afternoon:String(day.afternoon||'').slice(0,95),evening:String(day.evening||'').slice(0,75),transport:String(day.transport||'').slice(0,65)}})}}clean.practical_notes=Array.isArray(plan.practical_notes)?plan.practical_notes.map(note=>String(note||'').slice(0,160)).slice(0,12):[];return clean}}
function applySharedTrip(){{const encoded=new URLSearchParams(location.hash.slice(1)).get('trip');if(!encoded)return;const payload=decodeTrip(encoded);if(!payload||typeof payload!=='object')return;for(const key of ['arrival','departure','adults','children']){{if(payload[key]!==undefined&&form.elements[key])form.elements[key].value=payload[key]}}for(const key of ['interests','regions']){{if(!Array.isArray(payload[key]))continue;document.querySelectorAll('input[name="'+key+'"]').forEach(input=>{{input.checked=payload[key].includes(input.value)}})}}for(const key of ['budget','pace']){{if(typeof payload[key]!=='string')continue;const input=document.querySelector('input[name="'+key+'"][value="'+CSS.escape(payload[key])+'"]');if(input)input.checked=true}}const surprise=document.getElementById('surprise');if(surprise)surprise.checked=Boolean(payload.surprise);if(typeof payload.audience==='string'&&AUDIENCE_VALUES.includes(payload.audience)){{try{{LS.setItem('teranga-audience',payload.audience)}}catch(_){{}}}}const sharedPlan=validateSharedPlan(payload.edited_plan);if(sharedPlan){{currentPlan=sharedPlan;renderEditablePlan(currentPlan);document.getElementById('voice-result-actions').style.display='flex';document.getElementById('share').style.display='block';updateJourneySteps();updatePracticalRegions();updateMapFromPlan();}}}}
function restoreSessionTrip(){{
try{{
if(new URLSearchParams(location.hash.slice(1)).get('trip'))return;
const raw=SS.getItem('teranga-trip-plan');if(!raw)return;
const plan=JSON.parse(raw);if(!plan||!Array.isArray(plan.days))return;
currentPlan=plan;renderEditablePlan(currentPlan);document.getElementById('voice-result-actions').style.display='flex';document.getElementById('share').style.display='block';
}}catch(_){{}}
}}
applySharedTrip();restoreSessionTrip();function restoreTripEditProposal(){{
try{{
const raw=SS.getItem('teranga-trip-edit-proposal');if(!raw)return;
const proposal=JSON.parse(raw);if(!proposal||proposal.action!=='replace_day_region'||!proposal.requires_confirmation)return;
const box=document.getElementById('trip-edit-proposal');if(!box)return;
const dayNumber=Number(proposal.day);
const index=Number.isInteger(dayNumber)?dayNumber-1:-1;
if(!currentPlan||!Array.isArray(currentPlan.days)||index<0||index>=currentPlan.days.length)return;
const targetRegion=String(proposal.region||'').trim();
const regionIsAllowed=[...document.querySelectorAll('.day-region option')].some(option=>option.value===targetRegion);
if(!regionIsAllowed){{SS.removeItem('teranga-trip-edit-proposal');return;}}
const day=currentPlan.days[index]||{{}};
box.hidden=false;
box.innerHTML='<strong>'+({lang}==='en'?'Proposed change':'Modification proposée')+' — '+({lang}==='en'?'Day ':'Jour ')+escapeHtml(String(proposal.day))+'</strong><br><span>'+escapeHtml(String(day.region||''))+' → '+escapeHtml(String(proposal.region||''))+'</span><div class="proposal-actions"><button type="button" id="apply-trip-edit">'+({lang}==='en'?'Confirm':'Confirmer')+'</button><button type="button" id="cancel-trip-edit">'+({lang}==='en'?'Cancel':'Annuler')+'</button></div>';
document.getElementById('apply-trip-edit').onclick=()=>{{
const target=currentPlan.days[index];if(!target)return;
const confirmedRegion=String(proposal.region||'').trim();
const confirmedRegionIsAllowed=[...document.querySelectorAll('.day-region option')].some(option=>option.value===confirmedRegion);
if(!confirmedRegionIsAllowed){{SS.removeItem('teranga-trip-edit-proposal');box.hidden=true;return;}}
target.region=confirmedRegion.slice(0,60);
updateJourneySteps();updatePracticalRegions();updateMapFromPlan();persistTripContext();
try{{SS.setItem('teranga-trip-plan',JSON.stringify(currentPlan));SS.removeItem('teranga-trip-edit-proposal')}}catch(_ ){{}}
renderEditablePlan(currentPlan);box.hidden=true;status.textContent={lang}==='en'?'Trip change applied for this session.':'Modification appliquée pour cette session.';
}};
document.getElementById('cancel-trip-edit').onclick=()=>{{box.hidden=true;try{{SS.removeItem('teranga-trip-edit-proposal')}}catch(_){{}}}};
}}catch(_){{}}
}}
restoreTripEditProposal();
async function readPlanStream(r,onChunk){{const reader=r.body.getReader();const dec=new TextDecoder();let buf='',result=null;const handle=line=>{{if(!line.trim())return;let ev;try{{ev=JSON.parse(line)}}catch(_){{return}}if(ev.error)throw new Error(ev.error);if(ev.progress&&ev.progress.day>0){{const p=document.createElement('p');p.className='loading';p.textContent='{loading} · {day} '+ev.progress.day+' / '+ev.progress.total;status.replaceChildren(p);}}if(ev.result)result=ev.result;}};while(true){{const {{value,done}}=await reader.read();if(done)break;onChunk();buf+=dec.decode(value,{{stream:true}});const lines=buf.split('\\n');buf=lines.pop();lines.forEach(handle);}}handle(buf);if(!result)throw new Error('');return result;}}
form.onsubmit=async e=>{{e.preventDefault(); if(!form.reportValidity())return;
const payload={{lang:'{lang}',arrival:form.arrival.value,departure:form.departure.value,adults:+form.adults.value,children:+form.children.value,
interests:[...document.querySelectorAll('input[name="interests"]:checked')].map(x=>x.value),budget:document.querySelector('input[name="budget"]:checked')?.value||'Confort',
pace:document.querySelector('input[name="pace"]:checked')?.value||'Équilibré',
regions:[...document.querySelectorAll('input[name="regions"]:checked')].map(x=>x.value),context_place:safePlaceName(),audience:audience,surprise:document.getElementById('surprise').checked}};
if(form.dataset.busy==='1')return;form.dataset.busy='1';
status.innerHTML='<p class="loading">{loading}</p>'; result.textContent='';
const submitBtn=form.querySelector('[type=submit]');if(submitBtn)submitBtn.disabled=true;const ctl=new AbortController();let killer=0;const arm=()=>{{clearTimeout(killer);killer=setTimeout(()=>ctl.abort(),60000);}};arm();
try{{const r=await fetch('/api/trip-planner',{{method:'POST',headers:{{'Content-Type':'application/json','X-Teranga-Stream':'1'}},body:JSON.stringify(payload),signal:ctl.signal}});let data;if(r.ok&&r.body&&(r.headers.get('Content-Type')||'').includes('ndjson')){{data=await readPlanStream(r,arm);}}else{{data=await r.json().catch(()=>({{}}));if(!r.ok)throw new Error(data.error||'');}}const p=data.plan||{{summary:data.itinerary,days:[],practical_notes:[]}};window.__tripBudgetLines=data.budget?.lines||[];renderEditablePlan(p);document.getElementById("voice-result-actions").style.display="flex";status.textContent='';document.getElementById('map').innerHTML=data.map_html||'';document.getElementById('share').style.display='block';syncEditor();payload.edited_plan=currentPlan;const encoded=encodeTrip(payload);const shareLang=payload.lang==='en'?'en':'fr';history.replaceState(null,'','/trip-planner?lang='+shareLang+'#trip='+encoded);document.getElementById('copy').onclick=copyTripLink;}}
catch(err){{const p=document.createElement('p');p.className='error';p.textContent=(err&&err.name!=='AbortError'&&err.message)||'{error}';status.replaceChildren(p);}}
finally{{clearTimeout(killer);form.dataset.busy='';if(submitBtn)submitBtn.disabled=false;}}
}};
</script></body></html>""".format(
        head=HEAD_ASSETS, header=site_header("/trip-planner", lang), footer=site_footer(lang),
        lang=escape(lang), site=escape(site_url), title=escape(t["title"]), intro=escape(t["intro"]), date_error=escape(t.get("date_error", "La date de départ doit être après la date d'arrivée.")), date_required=escape(t.get("date_required", "Sélectionne une date d’arrivée et une date de départ.")),
        kicker=escape(t["kicker"]), dates=escape(t["dates"]), travelers=escape(t["travelers"]),
        interests=escape(t["interests"]), budget=escape(t["budget"]), regions=escape(t["regions"]),
        pace=escape(t["pace"]), start=escape(t["start"]), cont=escape(t["continue"]),
        generate=escape(t["generate"]), result=escape(t["result"]), back=escape(t["back"]),
        error=escape(t["error"]), day=escape(t["day"]), morning=escape(t["morning"]), afternoon=escape(t["afternoon"]), evening=escape(t["evening"]), transport=escape(t["transport"]), budget_summary=escape(t["budget_summary"]), **{"from": escape(t["from"]), "to": escape(t["to"]), "adults": escape(t["adults"])},
        children=escape(t["children"]), loading=escape(t["loading"]), copied=escape(t["copied"]), note=escape(t["note"]), map_title=escape(t["map_title"]), share=escape(t.get("share", "Share this trip")), practical_title=escape(t["practical_title"]), practical_intro=escape(t["practical_intro"]), practical_region=escape(t["practical_region"]), practical_transport=escape(t["practical_transport"]), practical_hours=escape(t["practical_hours"]), practical_prices=escape(t["practical_prices"]), practical_procedures=escape(t["practical_procedures"]), practical_services=escape(t["practical_services"]), practical_loading=escape(t["practical_loading"]), practical_error=escape(t["practical_error"]), practical_checked=escape(t["practical_checked"]), practical_sources=escape(t["practical_sources"]), voice_listen=escape(t["voice_listen"]), voice_stop=escape(t["voice_stop"]), interests_html=_option_list(t["interest_options"], "interests"),
        budget_html=_option_list(t["budget_options"], "budget", "radio"), pace_html=_option_list(t["pace_options"], "pace", "radio"),
        regions_html=_option_list(t["region_options"], "regions"), surprise=escape(t["surprise"]), review_chat=escape(t["review_chat"]), region_options_json=json.dumps(t["region_options"], ensure_ascii=False), region_coords_json=json.dumps(REGION_COORDS, ensure_ascii=False), add_day=escape(t["add_day"]), save_edits=escape(t["save_edits"]), remove_day=escape(t["remove_day"]), places_label=escape(t.get("places_label", "Fiches lieux :"))
    )

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
def _normalize_plan(plan, fallback_text, expected_days=None, places_by_id=None):
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
        day = {"day": index, **{field: value.strip()[:500] for field, value in values.items()}}
        # Liens vers les fiches : uniquement des identifiants réellement présents dans la base.
        ids = item.get("places") if isinstance(item.get("places"), list) else []
        linked = []
        for place_id in ids:
            place = (places_by_id or {}).get(str(place_id))
            if place and all(entry["id"] != place["id"] for entry in linked):
                linked.append({"id": place["id"], "name": str(place.get("name", ""))})
        if linked:
            day["places"] = linked[:4]
        normalized_days.append(day)

    normalized_notes = [note.strip()[:500] for note in notes if isinstance(note, str) and note.strip()][:20]
    return {
        "summary": summary.strip()[:3000],
        "days": normalized_days,
        "practical_notes": normalized_notes,
    }

# Centres d'intérêt du formulaire (fr/en) → types de lieux de la base.
_INTEREST_TYPES = {
    "plages": {"beach", "coastal_site", "island"}, "beaches": {"beach", "coastal_site", "island"},
    "culture & histoire": {"heritage", "monument", "museum", "cultural_site", "religious_site"},
    "culture & history": {"heritage", "monument", "museum", "cultural_site", "religious_site"},
    "nature": {"natural_site", "coastal_site"}, "faune": {"natural_site"}, "wildlife": {"natural_site"},
    "îles": {"island"}, "islands": {"island"},
}


def _knowledge_places(data, places, limit=14):
    """Lieux vérifiés de la base, du plus pertinent au moins pertinent."""
    regions = set(data.get("regions") or [])
    wanted = set()
    for interest in data.get("interests") or []:
        wanted |= _INTEREST_TYPES.get(str(interest).casefold(), set())
    if any(str(i).casefold() == "dakar" for i in data.get("interests") or []):
        regions.add("Dakar")
    context = str(data.get("context_place") or "").casefold()

    def score(place):
        name = str(place.get("name", ""))
        return (
            3 * bool(context and (context in name.casefold() or name.casefold() in context))
            + 2 * (place.get("region") in regions)
            + (place.get("type") in wanted)
        )

    pool = [p for p in places or [] if p.get("id") and (not regions or p.get("region") in regions or score(p) >= 3)]
    return sorted(pool, key=score, reverse=True)[:limit]


def _places_block(known):
    if not known:
        return ""
    lines = "\n".join(
        f"- {p['id']} | {p.get('name', '')} ({p.get('region', '')}): {str(p.get('summary', ''))[:140]}" for p in known
    )
    return (
        "\nVerified places from the Teranga AI knowledge base (id | name (region): summary):\n" + lines + "\n"
        "Prefer these places when they fit the trip. For each day, list in \"places\" the ids of the places "
        "above that the day visits (only ids from this list; [] if none). Never invent an id.\n"
    )


def _prompt(data, known_places=()):
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
{_places_block(known_places)}
Return ONLY valid JSON in the user's language. Schema: {{"summary": string, "days": [{{"day": number, "title": string, "region": string, "morning": string, "afternoon": string, "evening": string, "transport": string, "places": [string]}}], "practical_notes": [string]}}. Create one object per travel day.
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


# Délai sous le timeout de Gunicorn (120 s) : une réponse trop lente renvoie
# une erreur JSON propre au lieu d'une page coupée par le serveur.
OPENAI_TIMEOUT = float(os.getenv("TRIP_OPENAI_TIMEOUT", "90"))
_MODEL_ERROR_MARKERS = ("not found", "does not exist", "not available", "unsupported", "not permitted")


def _trip_models():
    """Modèle du planificateur puis secours, comme pour le chat."""
    chain = [os.getenv("OPENAI_TRIP_MODEL"), os.getenv("OPENAI_MODEL"), "gpt-5.6-luna", "gpt-5.6-sol"]
    return [m for i, m in enumerate(chain) if m and m not in chain[:i]]


def _create(client, **kwargs):
    """responses.create avec délai borné et repli si le modèle est indisponible."""
    # Pas de nouvelle tentative : 90 s × 2 dépasserait les 120 s de Gunicorn.
    api = client.with_options(timeout=OPENAI_TIMEOUT, max_retries=0) if hasattr(client, "with_options") else client
    last = None
    for model in _trip_models():
        try:
            return api.responses.create(model=model, **kwargs)
        except Exception as exc:  # noqa: BLE001 - repli uniquement sur « modèle indisponible »
            text = f"{type(exc).__name__} {exc}".lower()
            if "model" not in text or not any(m in text for m in _MODEL_ERROR_MARKERS):
                raise
            last = exc
    raise last if last else RuntimeError("Aucun modèle disponible")


def _plan_result(data, text, expected_days, places_by_id):
    """Réponse finale du planificateur (identique en JSON et en flux)."""
    lang = data["lang"]
    budget_info = _budget(data)
    regions = data["regions"] or ["Dakar"]
    try:
        parsed_plan = json.loads(text)
    except json.JSONDecodeError:
        parsed_plan = None
    plan = _normalize_plan(parsed_plan, text, expected_days, places_by_id)
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
    return {
        "itinerary": json.dumps(plan, ensure_ascii=False),
        "plan": plan,
        "budget": {"currency": "USD", "lines": budget_lines, "total": budget_info["total"]},
        "language": lang,
        "map_html": _map_html(regions, "Trip map" if lang == "en" else "Carte du voyage"),
    }


def _plan_error(exc, lang):
    """(corps, statut, en-têtes) d'une erreur du planificateur, sans détail interne."""
    if "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower():
        message = ("The trip took too long to generate. Try again with fewer days or regions."
                   if lang == "en" else
                   "La génération a pris trop de temps. Réessaie avec moins de jours ou de régions.")
        return {"error": message}, 504, {}
    message = ("The trip planner is temporarily unavailable. Please try again in a moment."
               if lang == "en" else "Impossible de générer le voyage pour le moment. Réessaie dans un instant.")
    return {"error": message}, 503, {"Retry-After": "10"}


_DAY_MARKER = re.compile(r'"day"\s*:\s*\d')


def _stream_plan(app, client, request_kwargs, data, expected_days, places_by_id):
    """Plan en NDJSON : progression « jour N / M » puis résultat final.

    Les octets envoyés pendant la génération évitent aussi qu'un proxy coupe
    une connexion restée muette trop longtemps.
    """
    lang = data["lang"]

    def line(obj):
        return json.dumps(obj, ensure_ascii=False) + "\n"

    def generate():
        yield line({"progress": {"day": 0, "total": expected_days}})
        text = ""
        try:
            events = _create(client, stream=True, **request_kwargs)
            final_text = ""
            seen = 0
            for event in events:
                kind = getattr(event, "type", "")
                if kind == "response.output_text.delta":
                    text += getattr(event, "delta", "") or ""
                    count = min(expected_days, len(_DAY_MARKER.findall(text)))
                    if count > seen:
                        seen = count
                        yield line({"progress": {"day": count, "total": expected_days}})
                elif kind == "response.completed":
                    final_text = getattr(getattr(event, "response", None), "output_text", "") or ""
                elif kind in ("response.failed", "error"):
                    raise RuntimeError("trip-planner stream failed")
            text = final_text or text
            if not text:
                yield line({"error": "Réponse vide de l'assistant.", "status": 502})
                return
            yield line({"result": _plan_result(data, text, expected_days, places_by_id)})
        except Exception as exc:  # noqa: BLE001 - message public uniquement
            app.logger.exception("trip-planner")
            payload, status, _headers = _plan_error(exc, lang)
            yield line({**payload, "status": status})

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


def _practical_info(client, lang, region, category, day=""):
    response = _create(
        client,
        input=_practical_prompt(lang, region, category, day),
        max_output_tokens=700,
        reasoning={"effort": "low"},
        truncation="auto",
        tools=[{"type": "web_search", "search_context_size": "medium"}],
    )
    answer = getattr(response, "output_text", "") or ""
    return answer[:5000], extract_sources(response)


def register_trip_planner(app, client, site_url, allowed_origins=None, rate_guard=None, places=None):
    """Register Trip Planner routes.

    ``rate_guard(bucket)`` returns a ready-made 429 response when the caller
    exceeds its quota, or ``None``. Both API routes call OpenAI (one with web
    search), so they must not be reachable without rate limiting.
    """
    configured_origins = {str(origin).rstrip("/") for origin in (allowed_origins or {site_url}) if str(origin).strip()}

    @app.post("/api/practical-info")
    def api_practical_info():
        content_length = request.content_length
        if content_length is not None and content_length > 4000:
            return jsonify({"error": "Requête trop volumineuse."}), 413
        if not origin_allowed(request.headers.get("Origin"), request.headers.get("Referer"), configured_origins):
            return jsonify({"error": "Origine non autorisée."}), 403
        if rate_guard is not None:
            blocked = rate_guard("practical_info")
            if blocked is not None:
                return blocked
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
        if rate_guard is not None:
            blocked = rate_guard("trip_planner")
            if blocked is not None:
                return blocked
        expected_days = max(1, (departure_date - arrival_date).days)
        places_by_id = {str(p.get("id")): p for p in places or [] if p.get("id")}
        request_kwargs = dict(
            input=_prompt(data, _knowledge_places(data, places)),
            # Raisonnement court et sortie bornée : un plan de N jours tient
            # en ~450 jetons par jour ; évite les générations interminables.
            reasoning={"effort": "low"},
            max_output_tokens=min(16000, 1500 + 450 * expected_days),
            truncation="auto",
        )
        if request.headers.get("X-Teranga-Stream") == "1":
            return _stream_plan(app, client, request_kwargs, data, expected_days, places_by_id)
        try:
            response = _create(client, **request_kwargs)
            text = getattr(response, "output_text", "") or ""
            if not text:
                return jsonify({"error": "Réponse vide de l'assistant."}), 502
            return jsonify(_plan_result(data, text, expected_days, places_by_id))
        except Exception as exc:
            app.logger.exception("trip-planner")
            payload, status, headers = _plan_error(exc, lang)
            return jsonify(payload), status, headers
