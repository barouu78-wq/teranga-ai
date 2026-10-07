import json
import os
import re
import time
from html import escape
from flask import Response, jsonify, request, stream_with_context
from datetime import date

from services.backup_ai import backup_complete, backup_enabled, claude_events, claude_is_primary, claude_response
from services.http_security import origin_allowed
from services.site_layout import HEAD_ASSETS, asset_url, site_footer, site_header
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
        "from": "Arrivée", "to": "Départ", "choose_date": "Choisir une date", "date_error": "La date de départ doit être après la date d'arrivée.", "adults": "Adultes", "children": "Enfants",
        "budget_options": ["Économique", "Confort", "Premium", "Luxe"],
        "pace_options": ["Relax", "Équilibré", "Intensif"],
        "interest_options": ["Plages", "Culture & histoire", "Cuisine", "Nature", "Dakar", "Îles", "Faune", "Musique & vie nocturne", "Famille"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Laisser Teranga AI choisir", "places_label": "Fiches lieux :", "share": "🔗 Partager ces préférences", "add_day": "+ Ajouter une journée", "save_edits": "Enregistrer les modifications", "review_chat": "💬 Demander à Teranga de revoir mon séjour", "remove_day": "Supprimer", "edit_day": "Modifier ce jour", "day_title": "Titre", "move_up": "Monter ce jour", "move_down": "Descendre ce jour", "loading": "Teranga AI prépare ton voyage…", "copied": "✓ Lien copié", "note": "Les estimations et informations susceptibles de changer doivent être vérifiées avant le départ.", "map_title": "Carte du voyage", "day": "Jour", "morning": "Matin", "afternoon": "Après-midi", "evening": "Soir", "transport": "Transport", "budget_summary": "Budget indicatif", 
    },
    "en": {
        "title": "Senegal Trip Planner", "kicker": "Teranga AI · Travel Senegal",
        "intro": "Build a personalized Senegal itinerary in a few steps.",
        "dates": "Dates", "travelers": "Travelers", "interests": "Interests", "budget": "Budget", "regions": "Regions", "pace": "Pace",
        "start": "Create my trip", "continue": "Continue", "generate": "Generate my itinerary", "result": "Your trip is ready",
        "back": "Edit", "error": "We could not generate the trip right now.", "date_error": "Departure must be after arrival.", "from": "Arrival", "to": "Departure", "choose_date": "Pick a date",
        "adults": "Adults", "children": "Children",
        "budget_options": ["Budget", "Comfort", "Premium", "Luxury"], "pace_options": ["Relaxed", "Balanced", "Intensive"],
        "interest_options": ["Beaches", "Culture & history", "Food", "Nature", "Dakar", "Islands", "Wildlife", "Music & nightlife", "Family"],
        "region_options": list(SENEGAL_REGIONS),
        "surprise": "✨ Let Teranga AI choose", "places_label": "Place guides:", "share": "🔗 Share these preferences", "add_day": "+ Add a day", "save_edits": "Save changes", "review_chat": "💬 Ask Teranga to review my trip", "remove_day": "Remove", "edit_day": "Edit this day", "day_title": "Title", "move_up": "Move day up", "move_down": "Move day down", "loading": "Teranga AI is preparing your trip…", "copied": "✓ Link copied", "note": "Estimates and information that may change should be verified before departure.", "map_title": "Trip map", "day": "Day", "morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "transport": "Transport", "budget_summary": "Indicative budget", "practical_title": "Practical info", "practical_intro": "Check transport, hours, prices, procedures and services with web sources.", "practical_region": "Region", "practical_transport": "Transport", "practical_hours": "Hours", "practical_prices": "Prices", "practical_procedures": "Procedures", "practical_services": "Services", "practical_loading": "Searching the web…", "practical_error": "We could not retrieve practical information.", "practical_checked": "Checked", "practical_sources": "Sources", "voice_listen": "Listen", "voice_stop": "Stop",
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


# Textes passés au script statique static/trip-planner.js (mêmes valeurs,
# déjà échappées pour le HTML, que lorsque le script était dans la page).
_TRIP_CONFIG_KEYS = (
    "lang", "afternoon", "budget_summary", "copied", "date_error", "date_required", "day", "error",
    "evening", "loading", "map_title", "morning", "places_label", "practical_checked", "practical_error",
    "practical_hours", "practical_loading", "practical_prices", "practical_sources", "practical_transport",
    "regions", "remove_day", "transport", "voice_listen", "edit_day", "day_title", "move_up", "move_down",
)


def _trip_config(params):
    config = {key: params[key] for key in _TRIP_CONFIG_KEYS}
    config["region_options_json"] = json.loads(params["region_options_json"])
    config["region_coords_json"] = json.loads(params["region_coords_json"])
    # Dans une balise <script>, « < » ne doit jamais apparaître brut.
    return json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")

META_DESCRIPTIONS = {
    "fr": "Planifiez gratuitement votre voyage au Sénégal : itinéraire jour par jour selon vos dates, budget et envies (Dakar, Gorée, Saint-Louis, Casamance), avec carte.",
    "en": "Plan your Senegal trip for free: a day-by-day itinerary based on your dates, budget and interests (Dakar, Gorée, Saint-Louis, Saloum, Casamance), with a map.",
}


def _html(site_url, lang="fr"):
    t = UI.get(lang, UI["fr"])
    template = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{site}/trip-planner">
<meta property="og:title" content="{title} | Teranga AI">
<meta name="description" content="{meta_desc}">
<meta property="og:description" content="{meta_desc}">
<title>{title} | Teranga AI</title>
<script type="application/ld+json">{ld}</script>
{head}
<style>
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 var(--font,system-ui,sans-serif)}}
main{{width:min(920px,calc(100% - 28px));margin:auto;padding:28px 0 70px}}
.kicker{{color:var(--gold);font-size:12px;letter-spacing:.13em;text-transform:uppercase;font-weight:900}}
h1{{font:600 clamp(34px,6vw,54px)/1.04 var(--font-display);letter-spacing:-.02em;margin:9px 0 14px}}.intro{{color:var(--muted);font-size:18px}}
.card{{margin-top:22px;background:var(--surface);border:1px solid var(--line);border-radius:28px;padding:24px}}
section{{border-top:0;padding:0}}.step{{display:none}}.step.active{{display:block}}h2{{font-size:24px;margin:0 0 16px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}
label.field{{display:flex;flex-direction:column;gap:7px;color:var(--muted);font-size:14px}}
input[type=date],input[type=number]{{display:block;width:100%;max-width:100%;min-width:0;box-sizing:border-box;min-height:50px;-webkit-appearance:none;appearance:none;background:var(--bg);border:1px solid var(--line);color:var(--text);border-radius:13px;padding:13px;font:inherit;font-size:16px}}input[type=date]::-webkit-date-and-time-value{{text-align:left;min-height:1.4em}}.date-wrap{{position:relative;display:block}}.date-hint{{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}}.date-wrap.has-value .date-hint,.date-wrap:focus-within .date-hint{{display:none}}.date-wrap:not(.has-value):not(:focus-within) input[type=date]::-webkit-datetime-edit{{color:transparent}}
.chips{{display:flex;flex-wrap:wrap;gap:10px}}.chip input{{position:absolute;opacity:0}}.chip span{{display:block;padding:11px 14px;border:1px solid var(--line);border-radius:999px;cursor:pointer;color:var(--muted)}}.chip input:checked+span{{border-color:var(--accent);color:var(--text);background:var(--accent-soft)}}
.actions{{display:flex;justify-content:space-between;gap:12px;margin-top:24px}}button{{border:0;border-radius:14px;padding:13px 18px;font:800 15px system-ui;cursor:pointer}}.primary{{background:var(--accent);color:var(--accent-ink)}}.secondary{{background:var(--surface-2);color:var(--ink);border:1px solid var(--line)}}
.result{{white-space:pre-wrap;font-family:inherit;line-height:1.7}}.day-editor{{display:grid;gap:10px;margin-top:14px}}.day-card{{background:var(--surface-2);border:1px solid var(--line);border-radius:18px;padding:16px}}.day-card h3{{margin:0 0 10px}}.day-head{{display:flex;flex-direction:column;gap:2px;margin-bottom:10px}}.day-kicker{{color:var(--gold);font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}}.day-name{{font:700 20px/1.2 var(--font-display,inherit)}}.day-timeline{{list-style:none;margin:0;padding:0}}.day-timeline li{{position:relative;padding:0 0 14px 22px;border-left:2px solid var(--line-strong,var(--line));margin-left:6px}}.day-timeline li:last-child{{border-left-color:transparent;padding-bottom:4px}}.day-timeline li::before{{content:"";position:absolute;left:-7px;top:4px;width:12px;height:12px;border-radius:50%;background:var(--accent)}}.day-timeline li+li::before{{background:var(--ink,var(--text))}}.day-timeline span{{display:block;font-size:12px;color:var(--muted)}}.day-timeline p{{margin:2px 0 0;white-space:normal}}.day-edit{{margin-top:8px;border-top:1px solid var(--line);padding-top:8px}}.day-edit summary{{cursor:pointer;font-weight:700;min-height:44px;display:flex;align-items:center}}.day-title{{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px;font:inherit}}.day-region{{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}}.journey-steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:14px}}.journey-step{{background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:10px}}.route-visual{{margin-top:14px;background:var(--surface-2);border:1px solid var(--line);border-radius:18px;padding:10px;overflow:hidden}}.route-visual svg{{display:block;width:100%;height:210px}}.route-line{{fill:none;stroke:var(--accent);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:6 6}}.route-point{{fill:var(--surface);stroke:var(--accent);stroke-width:3}}.route-label{{fill:var(--text);font:700 11px system-ui,sans-serif}}.journey-step strong{{display:block;color:var(--gold);font-size:12px}}.journey-step span{{display:block;margin-top:3px}}.day-card textarea{{width:100%;min-height:62px;resize:vertical;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px;font:inherit}}.day-card label{{display:block;margin-top:9px;color:var(--muted);font-size:13px}}.day-actions{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}}.day-practical{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}.day-practical button{{padding:7px 9px;font-size:12px}}.day-actions button{{padding:8px 11px;font-size:13px}}.map{{margin-top:16px;border-radius:18px;overflow:hidden;border:1px solid var(--line)}}.map:empty,.route-visual:empty,.journey-steps:empty{{display:none}}.loading{{color:var(--gold)}}.error{{color:var(--sen-red);margin-top:12px}}
.small{{font-size:12px;color:var(--muted);margin-top:14px}}.practical{{margin-top:18px;padding:16px;background:var(--surface-2);border:1px solid var(--line);border-radius:18px}}.practical h3{{margin:0 0 6px}}.practical-intro{{color:var(--muted);font-size:13px;margin:0 0 12px}}.practical-controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}.practical-controls select{{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px}}.practical-controls button{{padding:9px 11px;font-size:13px}}.practical-answer{{margin-top:14px;white-space:pre-wrap}}.practical-sources{{margin:12px 0 0;padding-left:18px;font-size:13px}}.practical-sources a{{color:var(--gold)}}.voice-actions{{display:flex;gap:8px;margin-top:10px}}.voice-actions button{{padding:8px 11px;font-size:13px}}
.place-context{{margin:0 0 16px;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--bg);color:var(--muted)}}.place-context strong{{color:var(--ink)}}@media(max-width:560px){{main{{width:min(100% - 20px,920px);padding-top:18px}}.card{{padding:18px;border-radius:22px}}.actions{{flex-direction:column}}.actions button{{width:100%}}.day-card{{padding:13px}}.day-actions button,.day-practical button,.voice-actions button{{min-height:42px}}.practical-controls{{align-items:stretch}}.practical-controls select,.practical-controls button{{width:100%;min-height:42px}}.journey-steps{{grid-template-columns:1fr}}.route-visual svg{{height:180px}}}}@media(max-width:360px){{h1{{font-size:32px}}.intro{{font-size:16px}}.chips{{gap:7px}}.chip span{{padding:10px 12px}}}}</style></head>
<body>{header}<main>
<div class="kicker">{kicker}</div><h1>{title}</h1><p class="intro">{intro}</p><div id="place-context" class="place-context" hidden></div><div id="trip-edit-proposal" class="place-context" hidden></div>
<div class="card">
<form id="planner">
<section class="step active" data-step="1"><h2>{dates}</h2><div class="grid">
<label class="field">{from}<span class="date-wrap"><input name="arrival" type="date" required><span class="date-hint" aria-hidden="true">{choose_date}</span></span></label>
<label class="field">{to}<span class="date-wrap"><input name="departure" type="date" required><span class="date-hint" aria-hidden="true">{choose_date}</span></span></label></div>
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
<script type="application/json" id="trip-config">{trip_config}</script>
<script src="{trip_js}"></script></body></html>"""
    params = dict(
        head=HEAD_ASSETS, header=site_header("/trip-planner", lang), footer=site_footer(lang),
        lang=escape(lang), site=escape(site_url), title=escape(t["title"]), intro=escape(t["intro"]), date_error=escape(t.get("date_error", "La date de départ doit être après la date d'arrivée.")), date_required=escape(t.get("date_required", "Sélectionne une date d’arrivée et une date de départ.")),
        kicker=escape(t["kicker"]), dates=escape(t["dates"]), travelers=escape(t["travelers"]),
        interests=escape(t["interests"]), budget=escape(t["budget"]), regions=escape(t["regions"]),
        pace=escape(t["pace"]), start=escape(t["start"]), cont=escape(t["continue"]),
        generate=escape(t["generate"]), result=escape(t["result"]), back=escape(t["back"]),
        error=escape(t["error"]), day=escape(t["day"]), morning=escape(t["morning"]), afternoon=escape(t["afternoon"]), evening=escape(t["evening"]), transport=escape(t["transport"]), budget_summary=escape(t["budget_summary"]), choose_date=escape(t.get("choose_date", "Choisir une date")), **{"from": escape(t["from"]), "to": escape(t["to"]), "adults": escape(t["adults"])},
        children=escape(t["children"]), loading=escape(t["loading"]), copied=escape(t["copied"]), note=escape(t["note"]), map_title=escape(t["map_title"]), share=escape(t.get("share", "Share this trip")), practical_title=escape(t["practical_title"]), practical_intro=escape(t["practical_intro"]), practical_region=escape(t["practical_region"]), practical_transport=escape(t["practical_transport"]), practical_hours=escape(t["practical_hours"]), practical_prices=escape(t["practical_prices"]), practical_procedures=escape(t["practical_procedures"]), practical_services=escape(t["practical_services"]), practical_loading=escape(t["practical_loading"]), practical_error=escape(t["practical_error"]), practical_checked=escape(t["practical_checked"]), practical_sources=escape(t["practical_sources"]), voice_listen=escape(t["voice_listen"]), voice_stop=escape(t["voice_stop"]), interests_html=_option_list(t["interest_options"], "interests"),
        budget_html=_option_list(t["budget_options"], "budget", "radio"), pace_html=_option_list(t["pace_options"], "pace", "radio"),
        regions_html=_option_list(t["region_options"], "regions"), surprise=escape(t["surprise"]), review_chat=escape(t["review_chat"]), region_options_json=json.dumps(t["region_options"], ensure_ascii=False), region_coords_json=json.dumps(REGION_COORDS, ensure_ascii=False), add_day=escape(t["add_day"]), save_edits=escape(t["save_edits"]), remove_day=escape(t["remove_day"]), edit_day=escape(t["edit_day"]), day_title=escape(t["day_title"]), move_up=escape(t["move_up"]), move_down=escape(t["move_down"]), places_label=escape(t.get("places_label", "Fiches lieux :"))
    )
    meta_desc = META_DESCRIPTIONS.get(lang, META_DESCRIPTIONS["fr"])
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebApplication", "name": f"{t['title']} | Teranga AI",
        "url": f"{site_url}/trip-planner", "applicationCategory": "TravelApplication", "operatingSystem": "Web",
        "inLanguage": lang, "description": meta_desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
    }, ensure_ascii=True).replace("<", "\\u003c")
    return template.format(**params, trip_config=_trip_config(params), trip_js=asset_url("trip-planner.js"), meta_desc=escape(meta_desc), ld=ld)

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
_UNREADABLE = {
    "fr": "Le plan n'a pas pu être mis en forme. Réessaie : la deuxième tentative fonctionne en général.",
    "en": "The plan could not be formatted. Please try again: the second attempt usually works.",
}
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def _parse_plan_json(text):
    """JSON du modèle, même entouré de ``` ou coupé en cours de route (on garde les jours complets)."""
    raw = _FENCE.sub("", str(text or "").strip())
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0:
        return None
    try:
        return json.loads(raw[start:end + 1] if end > start else raw[start:])
    except json.JSONDecodeError:
        pass
    tail = raw[start:]
    cuts = [i for i, ch in enumerate(tail) if ch == "}"][::-1][:200]
    for cut in cuts:
        for closing in ("]}", "]}}"):
            try:
                return json.loads(tail[:cut + 1] + closing)
            except json.JSONDecodeError:
                continue
    return None


def _looks_like_json(text):
    return _FENCE.sub("", str(text or "").strip()).startswith(("{", "["))


def _text(value):
    return value.strip()[:500] if isinstance(value, str) else ""


def _normalize_plan(plan, fallback_text, expected_days=None, places_by_id=None, lang="fr"):
    """Plan affichable. Tolérant : un jour en trop, un champ vide ou un numéro décalé ne font plus tout perdre."""
    fallback_summary = _UNREADABLE.get(lang, _UNREADABLE["fr"]) if _looks_like_json(fallback_text) else str(fallback_text or "")[:3000]
    fallback = {"summary": fallback_summary, "days": [], "practical_notes": []}
    if not isinstance(plan, dict) or not isinstance(plan.get("days"), list):
        return fallback
    summary = plan["summary"].strip()[:3000] if isinstance(plan.get("summary"), str) else ""
    notes = plan.get("practical_notes") if isinstance(plan.get("practical_notes"), list) else []
    limit = (expected_days or MAX_TRIP_DAYS) + 1

    normalized_days = []
    fields = ("title", "region", "morning", "afternoon", "evening", "transport")
    for item in plan["days"]:
        if len(normalized_days) >= limit:
            break
        if not isinstance(item, dict):
            continue
        values = {field: _text(item.get(field)) for field in fields}
        if not any(values[field] for field in ("title", "morning", "afternoon", "evening")):
            continue
        index = len(normalized_days) + 1
        values["title"] = values["title"] or f"{'Day' if lang == 'en' else 'Jour'} {index}"
        day = {"day": index, **values}
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

    if not normalized_days:
        return fallback
    normalized_notes = [note.strip()[:500] for note in notes if isinstance(note, str) and note.strip()][:20]
    return {
        "summary": summary,
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


def _day_count(data):
    try:
        return max(1, (date.fromisoformat(data["departure"]) - date.fromisoformat(data["arrival"])).days)
    except (KeyError, TypeError, ValueError):
        return 1


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
Return ONLY valid JSON in the user's language. Schema: {{"summary": string, "days": [{{"day": number, "title": string, "region": string, "morning": string, "afternoon": string, "evening": string, "transport": string, "places": [string]}}], "practical_notes": [string]}}. Create exactly {_day_count(data)} day objects, numbered 1 to {_day_count(data)}: day 1 is the arrival date and the last day is the day before departure.
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
STREAM_DEADLINE_SECONDS = float(os.getenv("TRIP_STREAM_DEADLINE", "100"))
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
    plan = _normalize_plan(_parse_plan_json(text), text, expected_days, places_by_id, lang)
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


def _claude_kwargs(request_kwargs):
    return {"max_tokens": int(request_kwargs.get("max_output_tokens") or 8000), "timeout": OPENAI_TIMEOUT}


def _backup_plan_text(request_kwargs, app=None):
    """Plan rédigé par l'IA de secours (Claude) si OpenAI a échoué ; "" sinon."""
    if not backup_enabled() or claude_is_primary():
        return ""
    try:
        text = backup_complete(
            str(request_kwargs.get("input") or ""),
            max_tokens=int(request_kwargs.get("max_output_tokens") or 8000),
            timeout=OPENAI_TIMEOUT,
        )
    except Exception:  # noqa: BLE001 - l'erreur d'origine sera affichée
        if app is not None:
            app.logger.exception("trip-planner backup")
        return ""
    if text and app is not None:
        app.logger.warning("trip-planner backup_ai_used")
    return text


class _BackupEvent:
    """Fin de flux synthétique quand le plan vient de l'IA de secours."""

    type = "response.completed"

    def __init__(self, text):
        self.response = type("R", (), {"output_text": text})()


_HEARTBEAT = object()
HEARTBEAT_SECONDS = 10.0


def _events_with_heartbeat(open_stream):
    """Événements du flux OpenAI, entrecoupés de _HEARTBEAT pendant les silences.

    Le flux est lu dans un fil séparé ; une exception y est relancée ici.
    """
    import queue
    import threading

    box: "queue.Queue" = queue.Queue()
    done = object()

    def pump():
        try:
            for event in open_stream():
                box.put(event)
        except BaseException as exc:  # noqa: BLE001 - relancée côté générateur
            box.put(exc)
        finally:
            box.put(done)

    threading.Thread(target=pump, daemon=True, name="trip-stream").start()
    while True:
        try:
            item = box.get(timeout=HEARTBEAT_SECONDS)
        except queue.Empty:
            yield _HEARTBEAT
            continue
        if item is done:
            return
        if isinstance(item, BaseException):
            raise item
        yield item


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
        started = time.monotonic()
        try:
            def open_stream():
                # IA principale d'abord ; si elle échoue avant d'avoir écrit, l'autre prend
                # le relais (dans le même fil : les signes de vie continuent pendant ce temps).
                wrote = False
                if claude_is_primary():
                    try:
                        for event in claude_events(str(request_kwargs.get("input") or ""), **_claude_kwargs(request_kwargs)):
                            if event.type == "response.output_text.delta":
                                wrote = True
                            yield event
                        return
                    except Exception:
                        if wrote:
                            raise
                        app.logger.exception("trip-planner claude_primary_failed")
                try:
                    for event in _create(client, stream=True, **request_kwargs):
                        if getattr(event, "type", "") == "response.output_text.delta":
                            wrote = True
                        yield event
                except Exception:
                    backup = "" if wrote else _backup_plan_text(request_kwargs, app)
                    if not backup:
                        raise
                    yield _BackupEvent(backup)

            events = _events_with_heartbeat(open_stream)
            final_text = ""
            seen = 0
            for event in events:
                if event is _HEARTBEAT:
                    # Le modèle réfléchit sans rien écrire : un octet régulier évite que le
                    # navigateur ou un proxy prenne la connexion silencieuse pour morte.
                    yield line({"progress": {"day": seen, "total": expected_days}})
                    if time.monotonic() - started > STREAM_DEADLINE_SECONDS:
                        raise TimeoutError("trip-planner stream timed out")
                    continue
                # Durée totale bornée (le délai OpenAI ne compte que les silences) :
                # on répond par une erreur claire avant qu'un proxy coupe la connexion.
                if time.monotonic() - started > STREAM_DEADLINE_SECONDS:
                    raise TimeoutError("trip-planner stream timed out")
                kind = getattr(event, "type", "")
                if kind == "response.output_text.delta":
                    text += getattr(event, "delta", "") or ""
                    count = min(expected_days, len(_DAY_MARKER.findall(text)))
                    if count > seen:
                        seen = count
                        yield line({"progress": {"day": count, "total": expected_days}})
                elif kind in ("response.completed", "response.incomplete"):
                    # « incomplete » (limite de jetons atteinte) : on garde le texte reçu.
                    final_text = getattr(getattr(event, "response", None), "output_text", "") or ""
                    if kind == "response.incomplete":
                        app.logger.warning("trip-planner réponse incomplète (%d caractères)", len(text))
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
            # Plafond assez haut pour MAX_TRIP_DAYS jours : un plafond plus bas couperait
            # le JSON des longs séjours et le plan échouerait.
            max_output_tokens=min(1500 + 450 * MAX_TRIP_DAYS, 1500 + 450 * expected_days),
            truncation="auto",
        )
        if request.headers.get("X-Teranga-Stream") == "1":
            return _stream_plan(app, client, request_kwargs, data, expected_days, places_by_id)
        try:
            text = ""
            if claude_is_primary():
                try:
                    text = claude_response(str(request_kwargs.get("input") or ""), **_claude_kwargs(request_kwargs)).output_text
                except Exception:  # noqa: BLE001 - OpenAI prend le relais
                    app.logger.exception("trip-planner claude_primary_failed")
            try:
                if not text:
                    response = _create(client, **request_kwargs)
                    text = getattr(response, "output_text", "") or ""
            except Exception:
                text = _backup_plan_text(request_kwargs, app)
                if not text:
                    raise
            if not text:
                return jsonify({"error": "Réponse vide de l'assistant."}), 502
            return jsonify(_plan_result(data, text, expected_days, places_by_id))
        except Exception as exc:
            app.logger.exception("trip-planner")
            payload, status, headers = _plan_error(exc, lang)
            return jsonify(payload), status, headers
