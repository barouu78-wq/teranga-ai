from flask import Response
from html import escape
import json

LANGS = ("en", "es", "de", "it", "fr")

TOPICS = {
    "senegal-travel-guide": {
        "en": ("Senegal Travel Guide", "Senegal Travel Guide: Dakar, Gorée, Regions & Practical Tips", "Complete Senegal travel guide for Dakar, Gorée, transport, food, weather and regional ideas.", "Plan your Senegal trip with Teranga AI."),
        "es": ("Guía de viaje de Senegal", "Guía de viaje de Senegal: Dakar, Gorée, regiones y consejos", "Guía práctica de Senegal: Dakar, Gorée, transporte, gastronomía, clima y regiones.", "Planifica tu viaje a Senegal con Teranga AI."),
        "de": ("Senegal Reiseführer", "Senegal Reiseführer: Dakar, Gorée, Regionen & praktische Tipps", "Praktischer Senegal-Reiseführer zu Dakar, Gorée, Verkehr, Essen, Wetter und Regionen.", "Plane deine Senegal-Reise mit Teranga AI."),
        "it": ("Guida di viaggio Senegal", "Guida di viaggio Senegal: Dakar, Gorée, regioni e consigli", "Guida pratica al Senegal: Dakar, Gorée, trasporti, cucina, meteo e regioni.", "Organizza il tuo viaggio in Senegal con Teranga AI."),
        "fr": ("Guide voyage Sénégal", "Guide voyage Sénégal : Dakar, Gorée, régions et conseils", "Guide pratique du Sénégal : Dakar, Gorée, transports, cuisine, météo et régions.", "Préparez votre voyage au Sénégal avec Teranga AI."),
    },
    "dakar-travel-guide": {
        "en": ("Dakar Travel Guide", "Dakar Travel Guide: What to See, Eat & Do", "Practical Dakar travel guide covering neighborhoods, food, transport, Gorée and daily planning.", "Build your Dakar itinerary with Teranga AI."),
        "es": ("Guía de viaje de Dakar", "Guía de viaje de Dakar: qué ver, comer y hacer", "Guía práctica de Dakar: barrios, comida, transporte, Gorée y planificación.", "Crea tu itinerario de Dakar con Teranga AI."),
        "de": ("Dakar Reiseführer", "Dakar Reiseführer: Sehenswürdigkeiten, Essen & Aktivitäten", "Praktischer Dakar-Guide zu Vierteln, Essen, Verkehr, Gorée und Tagesplanung.", "Erstelle deinen Dakar-Plan mit Teranga AI."),
        "it": ("Guida di viaggio Dakar", "Guida di viaggio Dakar: cosa vedere, mangiare e fare", "Guida pratica di Dakar: quartieri, cucina, trasporti, Gorée e itinerari.", "Crea il tuo itinerario di Dakar con Teranga AI."),
        "fr": ("Guide voyage Dakar", "Guide voyage Dakar : que voir, manger et faire", "Guide pratique de Dakar : quartiers, cuisine, transports, Gorée et itinéraires.", "Créez votre itinéraire à Dakar avec Teranga AI."),
    },
    "things-to-do-in-dakar": {
        "en": ("Things to Do in Dakar", "15 Things to Do in Dakar", "Ideas for Dakar: Gorée, markets, monuments, beaches, food and neighborhoods.", "Tell Teranga AI your dates and interests to build a Dakar plan."),
        "es": ("Qué hacer en Dakar", "15 cosas que hacer en Dakar", "Ideas para Dakar: Gorée, mercados, monumentos, playas, gastronomía y barrios.", "Indica tus fechas e intereses a Teranga AI para crear tu plan."),
        "de": ("Was kann man in Dakar machen?", "15 Aktivitäten in Dakar", "Ideen für Dakar: Gorée, Märkte, Monumente, Strände, Essen und Viertel.", "Nenne Teranga AI deine Reisedaten und Interessen."),
        "it": ("Cosa fare a Dakar", "15 cose da fare a Dakar", "Idee per Dakar: Gorée, mercati, monumenti, spiagge, cucina e quartieri.", "Indica date e interessi a Teranga AI per creare il tuo piano."),
        "fr": ("Que faire à Dakar", "15 choses à faire à Dakar", "Idées à Dakar : Gorée, marchés, monuments, plages, cuisine et quartiers.", "Indiquez vos dates et centres d’intérêt à Teranga AI."),
    },
    "things-to-do-in-senegal": {
        "en": ("Things to Do in Senegal", "Things to Do in Senegal: Places & Experiences", "Ideas across Senegal: Dakar, Gorée, Saint-Louis, Sine-Saloum, Casamance and Kédougou.", "Create a Senegal itinerary with Teranga AI."),
        "es": ("Qué hacer en Senegal", "Qué hacer en Senegal: lugares y experiencias", "Ideas por Senegal: Dakar, Gorée, Saint-Louis, Sine-Saloum, Casamance y Kédougou.", "Crea un itinerario de Senegal con Teranga AI."),
        "de": ("Was kann man im Senegal machen?", "Aktivitäten im Senegal: Orte & Erlebnisse", "Ideen für Senegal: Dakar, Gorée, Saint-Louis, Sine-Saloum, Casamance und Kédougou.", "Erstelle einen Senegal-Reiseplan mit Teranga AI."),
        "it": ("Cosa fare in Senegal", "Cosa fare in Senegal: luoghi ed esperienze", "Idee in Senegal: Dakar, Gorée, Saint-Louis, Sine-Saloum, Casamance e Kédougou.", "Crea un itinerario in Senegal con Teranga AI."),
        "fr": ("Que faire au Sénégal", "Que faire au Sénégal : lieux et expériences", "Idées au Sénégal : Dakar, Gorée, Saint-Louis, Sine-Saloum, Casamance et Kédougou.", "Créez un itinéraire au Sénégal avec Teranga AI."),
    },
    "dakar-airport-to-city": {
        "en": ("Dakar Airport to City", "How to Get from Dakar Airport to Dakar", "Practical options from Blaise Diagne International Airport (AIBD) to Dakar and other destinations.", "Tell Teranga AI your arrival time and destination."),
        "es": ("Aeropuerto de Dakar al centro", "Cómo ir del aeropuerto de Dakar a Dakar", "Opciones prácticas desde el aeropuerto Blaise Diagne (AIBD) hacia Dakar y otros destinos.", "Indica a Teranga AI tu hora de llegada y destino."),
        "de": ("Flughafen Dakar ins Zentrum", "Vom Flughafen Dakar nach Dakar: Anreise", "Praktische Optionen vom Flughafen Blaise Diagne (AIBD) nach Dakar und andere Ziele.", "Nenne Teranga AI Ankunftszeit und Ziel."),
        "it": ("Aeroporto di Dakar al centro", "Come arrivare dall'aeroporto di Dakar a Dakar", "Opzioni pratiche dall'aeroporto Blaise Diagne (AIBD) verso Dakar e altre destinazioni.", "Indica a Teranga AI orario di arrivo e destinazione."),
        "fr": ("Aéroport de Dakar vers la ville", "Comment aller de l’aéroport de Dakar à Dakar", "Options pratiques depuis l’aéroport Blaise Diagne (AIBD) vers Dakar et d’autres destinations.", "Indiquez votre heure d’arrivée et votre destination à Teranga AI."),
    },
    "goree-island": {
        "en": ("Gorée Island Guide", "Gorée Island Guide: Ferry, History & Things to See", "Practical guide to Gorée Island from Dakar, including the ferry, history and visit planning.", "Ask Teranga AI to plan your Gorée visit."),
        "es": ("Guía de la isla de Gorée", "Guía de Gorée: ferry, historia y lugares que ver", "Guía práctica de Gorée desde Dakar: ferry, historia y planificación de la visita.", "Pide a Teranga AI que planifique tu visita."),
        "de": ("Gorée-Insel Reiseführer", "Gorée: Fähre, Geschichte & Sehenswürdigkeiten", "Praktischer Guide für Gorée ab Dakar: Fähre, Geschichte und Besuchsplanung.", "Lass Teranga AI deinen Gorée-Besuch planen."),
        "it": ("Guida all'isola di Gorée", "Gorée: traghetto, storia e cosa vedere", "Guida pratica a Gorée da Dakar: traghetto, storia e organizzazione della visita.", "Chiedi a Teranga AI di organizzare la visita."),
        "fr": ("Guide de l’île de Gorée", "Gorée : ferry, histoire et choses à voir", "Guide pratique de Gorée depuis Dakar : ferry, histoire et préparation de la visite.", "Demandez à Teranga AI de préparer votre visite."),
    },
    "where-to-eat-in-dakar": {
        "en": ("Where to Eat in Dakar", "Where to Eat in Dakar: Neighborhoods & Senegalese Food", "Where to look for Senegalese food in Dakar, from Plateau and Médina to Ngor and Almadies.", "Tell Teranga AI what food and neighborhood you want."),
        "es": ("Dónde comer en Dakar", "Dónde comer en Dakar: barrios y cocina senegalesa", "Dónde buscar cocina senegalesa en Dakar, de Plateau y Medina a Ngor y Almadies.", "Indica a Teranga AI qué comida y barrio buscas."),
        "de": ("Wo kann man in Dakar essen?", "Essen in Dakar: Viertel & senegalesische Küche", "Wo du in Dakar senegalesische Küche findest, von Plateau und Medina bis Ngor und Almadies.", "Nenne Teranga AI Küche und Viertel."),
        "it": ("Dove mangiare a Dakar", "Dove mangiare a Dakar: quartieri e cucina senegalese", "Dove cercare cucina senegalese a Dakar, da Plateau e Medina a Ngor e Almadies.", "Indica a Teranga AI cucina e quartiere."),
        "fr": ("Où manger à Dakar", "Où manger à Dakar : quartiers et cuisine sénégalaise", "Où chercher la cuisine sénégalaise à Dakar, du Plateau et de la Médina à Ngor et Almadies.", "Indiquez à Teranga AI le plat et le quartier recherchés."),
    },
    "senegal-transport": {
        "en": ("Senegal Transportation", "Senegal Transportation: Dakar, Intercity & Local Travel", "Overview of travel by road, rail, taxi and other options in Senegal, with current details to verify.", "Ask Teranga AI for a route based on your date and destination."),
        "es": ("Transporte en Senegal", "Transporte en Senegal: Dakar, viajes entre ciudades y desplazamientos", "Resumen de transporte por carretera, tren, taxi y otras opciones, con datos actuales por verificar.", "Pide a Teranga AI una ruta según fecha y destino."),
        "de": ("Transport im Senegal", "Transport im Senegal: Dakar, Fernverkehr & lokale Wege", "Überblick zu Straße, Bahn, Taxi und weiteren Optionen; aktuelle Details sollten geprüft werden.", "Frag Teranga AI nach einer Route mit Datum und Ziel."),
        "it": ("Trasporti in Senegal", "Trasporti in Senegal: Dakar, città e spostamenti", "Panoramica di strada, treno, taxi e altre opzioni; i dettagli attuali vanno verificati.", "Chiedi a Teranga AI un percorso per data e destinazione."),
        "fr": ("Transport au Sénégal", "Transport au Sénégal : Dakar, interurbain et déplacements", "Panorama des déplacements par route, train, taxi et autres options, avec vérification des données actuelles.", "Demandez à Teranga AI un trajet selon votre date et destination."),
    },
    "senegal-sim-card": {
        "en": ("Senegal SIM Card", "Senegal SIM Card for Tourists: What to Know", "Practical guide to staying connected in Senegal, including SIM/eSIM questions and what to verify on arrival.", "Tell Teranga AI your phone needs and trip dates."),
        "es": ("SIM de Senegal", "Tarjeta SIM de Senegal para turistas: qué saber", "Guía práctica para conectarte en Senegal: SIM/eSIM y puntos que conviene verificar al llegar.", "Indica a Teranga AI tus necesidades y fechas."),
        "de": ("SIM-Karte Senegal", "SIM-Karte im Senegal für Touristen: Das ist wichtig", "Praktischer Guide für mobile Verbindung im Senegal, inklusive SIM/eSIM und Prüfung vor Ort.", "Nenne Teranga AI deine Bedürfnisse und Reisedaten."),
        "it": ("SIM Senegal", "SIM in Senegal per turisti: cosa sapere", "Guida pratica alla connettività in Senegal, con SIM/eSIM e informazioni da verificare all'arrivo.", "Indica a Teranga AI esigenze e date del viaggio."),
        "fr": ("Carte SIM Sénégal", "Carte SIM Sénégal pour touristes : ce qu’il faut savoir", "Guide pratique pour rester connecté au Sénégal : SIM/eSIM et points à vérifier à l’arrivée.", "Indiquez vos besoins et dates à Teranga AI."),
    },
    "senegal-weather": {
        "en": ("Senegal Weather", "Senegal Weather: Seasons, Dakar & Trip Planning", "Seasonal climate overview for Senegal and practical guidance for checking current weather before travel.", "Ask Teranga AI for the weather on your travel dates."),
        "es": ("Clima de Senegal", "Clima de Senegal: estaciones, Dakar y planificación", "Resumen climático de Senegal y consejos para comprobar el tiempo actual antes del viaje.", "Pregunta a Teranga AI por el tiempo en tus fechas."),
        "de": ("Senegal Wetter", "Senegal Wetter: Jahreszeiten, Dakar & Reiseplanung", "Überblick über das Klima Senegals und Hinweise zur Prüfung des aktuellen Wetters.", "Frag Teranga AI nach dem Wetter für deine Reisedaten."),
        "it": ("Meteo Senegal", "Meteo Senegal: stagioni, Dakar e viaggio", "Panoramica del clima del Senegal e indicazioni per controllare il meteo attuale prima del viaggio.", "Chiedi a Teranga AI il meteo per le tue date."),
        "fr": ("Météo Sénégal", "Météo Sénégal : saisons, Dakar et préparation du voyage", "Repères climatiques du Sénégal et conseils pour vérifier la météo actuelle avant le voyage.", "Demandez à Teranga AI la météo de vos dates."),
    },
    "senegal-visa": {
        "en": ("Senegal Visa Information", "Senegal Visa Information: Entry & Travel Documents", "Travel-document guide for Senegal. Entry rules can change, so verify current requirements with official authorities.", "Tell Teranga AI your nationality and travel date for a current-source check."),
        "es": ("Visado de Senegal", "Visado de Senegal: entrada y documentos de viaje", "Guía sobre documentos de viaje para Senegal. Las reglas pueden cambiar: verifica las fuentes oficiales.", "Indica a Teranga AI tu nacionalidad y fecha para buscar información reciente."),
        "de": ("Senegal Visum", "Senegal Visum: Einreise & Reisedokumente", "Guide zu Reisedokumenten für Senegal. Einreisebestimmungen können sich ändern; prüfe offizielle Quellen.", "Nenne Teranga AI Nationalität und Reisedatum."),
        "it": ("Visto Senegal", "Visto Senegal: ingresso e documenti di viaggio", "Guida ai documenti per viaggiare in Senegal. Le regole possono cambiare: verifica le fonti ufficiali.", "Indica a Teranga AI nazionalità e data di viaggio."),
        "fr": ("Visa Sénégal", "Visa Sénégal : entrée et documents de voyage", "Guide des documents pour voyager au Sénégal. Les règles peuvent changer : vérifiez les sources officielles.", "Indiquez votre nationalité et date de voyage à Teranga AI."),
    },
    "senegal-trip-planner": {
        "en": ("Senegal Trip Planner", "Senegal Trip Planner: Build Your Itinerary", "Plan a Senegal trip around your dates, budget, destinations and interests with Teranga AI.", "Start with your dates, budget and interests."),
        "es": ("Planificador de viaje a Senegal", "Planificador de viaje a Senegal: crea tu itinerario", "Planifica tu viaje según fechas, presupuesto, destinos e intereses con Teranga AI.", "Empieza con fechas, presupuesto e intereses."),
        "de": ("Senegal Reiseplaner", "Senegal Reiseplaner: Erstelle deine Route", "Plane deine Senegal-Reise nach Daten, Budget, Zielen und Interessen mit Teranga AI.", "Starte mit Reisedaten, Budget und Interessen."),
        "it": ("Pianificatore viaggio Senegal", "Pianificatore viaggio Senegal: crea il tuo itinerario", "Organizza il viaggio in base a date, budget, destinazioni e interessi con Teranga AI.", "Inizia con date, budget e interessi."),
        "fr": ("Planificateur voyage Sénégal", "Planificateur voyage Sénégal : créez votre itinéraire", "Préparez votre voyage selon vos dates, budget, destinations et centres d’intérêt avec Teranga AI.", "Commencez par vos dates, votre budget et vos centres d’intérêt."),
    },
}

COPY = {
    "en": [
        ("Quick answer", "Use this page for practical orientation. For schedules, prices, weather, entry rules and other changing details, check current sources before acting."),
        ("What to plan", "Choose destinations, travel time, budget and interests first. Then use Teranga AI to turn those constraints into a practical route."),
        ("Local context", "Dakar is the main international arrival point. Senegal also includes Saint-Louis, Sine-Saloum, Petite Côte, Casamance and the Kédougou area."),
    ],
    "es": [
        ("Respuesta rápida", "Usa esta página como orientación práctica. Para horarios, precios, clima, requisitos de entrada y otros datos variables, comprueba fuentes actuales."),
        ("Qué planificar", "Define destinos, duración, presupuesto e intereses. Después usa Teranga AI para convertirlos en una ruta práctica."),
        ("Contexto local", "Dakar es el principal punto de llegada internacional. Senegal también incluye Saint-Louis, Sine-Saloum, Petite Côte, Casamance y Kédougou."),
    ],
    "de": [
        ("Kurz erklärt", "Nutze diese Seite zur praktischen Orientierung. Bei Fahrplänen, Preisen, Wetter und Einreiseangaben sollten aktuelle Quellen geprüft werden."),
        ("Was planen", "Lege Ziele, Reisedauer, Budget und Interessen fest. Danach kann Teranga AI daraus eine praktische Route erstellen."),
        ("Lokaler Kontext", "Dakar ist der wichtigste internationale Ankunftspunkt. Dazu kommen Saint-Louis, Sine-Saloum, Petite Côte, Casamance und Kédougou."),
    ],
    "it": [
        ("In breve", "Usa questa pagina come orientamento pratico. Per orari, prezzi, meteo, requisiti di ingresso e altri dati variabili, verifica fonti aggiornate."),
        ("Cosa pianificare", "Definisci destinazioni, durata, budget e interessi. Poi usa Teranga AI per trasformarli in un itinerario pratico."),
        ("Contesto locale", "Dakar è il principale punto di arrivo internazionale. Il Senegal comprende anche Saint-Louis, Sine-Saloum, Petite Côte, Casamance e Kédougou."),
    ],
    "fr": [
        ("En bref", "Utilisez cette page comme repère pratique. Pour les horaires, prix, météo, formalités et autres données variables, vérifiez les sources actuelles."),
        ("À planifier", "Définissez vos destinations, durée, budget et centres d’intérêt. Teranga AI peut ensuite transformer ces contraintes en itinéraire pratique."),
        ("Contexte local", "Dakar est le principal point d’arrivée international. Le Sénégal comprend aussi Saint-Louis, le Sine-Saloum, la Petite Côte, la Casamance et Kédougou."),
    ],
}

FAQ = {
    "en": [("Can Teranga AI create an itinerary?", "Yes. Give it your dates, destinations, budget and interests, then verify changing travel information before booking."), ("Are the answers current?", "For changing topics, Teranga AI can use recent web information; official sources remain the reference for entry rules and other sensitive requirements.")],
    "es": [("¿Teranga AI puede crear un itinerario?", "Sí. Indica fechas, destinos, presupuesto e intereses y comprueba los datos variables antes de reservar."), ("¿La información está actualizada?", "Para temas variables, Teranga AI puede consultar información reciente; las fuentes oficiales son la referencia para requisitos sensibles.")],
    "de": [("Kann Teranga AI eine Route erstellen?", "Ja. Nenne Daten, Ziele, Budget und Interessen und prüfe veränderliche Angaben vor einer Buchung."), ("Sind die Informationen aktuell?", "Bei veränderlichen Themen kann Teranga AI aktuelle Webinformationen nutzen; für sensible Anforderungen sind offizielle Quellen maßgeblich.")],
    "it": [("Teranga AI può creare un itinerario?", "Sì. Indica date, destinazioni, budget e interessi e verifica i dati variabili prima di prenotare."), ("Le informazioni sono aggiornate?", "Per temi variabili Teranga AI può usare informazioni web recenti; per requisiti sensibili fanno fede le fonti ufficiali.")],
    "fr": [("Teranga AI peut-il créer un itinéraire ?", "Oui. Indiquez vos dates, destinations, budget et centres d’intérêt, puis vérifiez les informations changeantes avant de réserver."), ("Les informations sont-elles à jour ?", "Pour les sujets variables, Teranga AI peut utiliser des informations web récentes ; les sources officielles restent la référence pour les exigences sensibles.")],
}

LANG_NAMES = {"en":"English","es":"Español","de":"Deutsch","it":"Italiano","fr":"Français"}

def _localized_path(lang, topic):
    return f"/{lang}/{topic}"

def render_international_page(lang, topic, site_url):
    page = TOPICS.get(topic)
    if not page or lang not in LANGS or lang not in page:
        return None
    label, title, description, cta = page[lang]
    sections = "".join(f"<section><h2>{escape(h)}</h2><p>{escape(p)}</p></section>" for h,p in COPY[lang])
    faq = "".join(f"<div class='faq'><h3>{escape(q)}</h3><p>{escape(a)}</p></div>" for q,a in FAQ[lang])
    url = f"{site_url.rstrip('/')}{_localized_path(lang, topic)}"
    alternates = "".join(
        f'<link rel="alternate" hreflang="{escape(l)}" href="{site_url.rstrip("/")}{_localized_path(l, topic)}">'
        for l in LANGS
    )
    alternates += f'<link rel="alternate" hreflang="x-default" href="{site_url.rstrip("/")}{_localized_path("en", topic)}">'
    related = "".join(
        f'<a href="{_localized_path(lang, t)}">{escape(TOPICS[t][lang][0])}</a>'
        for t in list(TOPICS)[:8] if t != topic
    )
    faq_ld = [{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in FAQ[lang]]
    ld = {
        "@context":"https://schema.org",
        "@graph":[
            {"@type":"WebPage","name":title,"description":description,"url":url,"inLanguage":lang,
             "isPartOf":{"@type":"WebSite","name":"Teranga AI","url":site_url.rstrip("/")+"/"}},
            {"@type":"BreadcrumbList","itemListElement":[
                {"@type":"ListItem","position":1,"name":"Teranga AI","item":site_url.rstrip("/")+"/"},
                {"@type":"ListItem","position":2,"name":label,"item":url}
            ]},
            {"@type":"FAQPage","mainEntity":faq_ld}
        ]
    }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")
    html = f"""<!doctype html>
<html lang="{escape(lang)}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow"><meta name="description" content="{escape(description)}">
<link rel="canonical" href="{escape(url)}">{alternates}
<meta property="og:site_name" content="Teranga AI"><meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}"><meta property="og:type" content="article">
<meta property="og:url" content="{escape(url)}"><meta property="og:image" content="{escape(site_url.rstrip("/")+"/og.png")}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)}">
<meta name="twitter:description" content="{escape(description)}"><meta name="twitter:image" content="{escape(site_url.rstrip("/")+"/og.png")}">
<title>{escape(title)}</title><script type="application/ld+json">{ld_json}</script>
<style>:root{{--bg:#0b0907;--text:#f6efe3;--muted:#b8a48c;--gold:#e2b34a;--line:rgba(226,179,74,.18)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,sans-serif}}main{{width:min(860px,calc(100% - 32px));margin:auto;padding:28px 0 56px}}nav{{display:flex;justify-content:space-between;margin-bottom:20px}}a{{color:var(--gold);text-decoration:none;font-weight:750}}article{{background:#171310;border:1px solid var(--line);border-radius:28px;padding:28px}}.kicker{{color:var(--gold);font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:800}}h1{{font:700 clamp(32px,6vw,48px)/1.08 Georgia,serif;margin:10px 0 16px}}.intro{{font-size:18px;color:var(--muted)}}section{{padding:18px 0;border-top:1px solid var(--line)}}h2{{font-size:20px;margin:0 0 6px}}h3{{font-size:16px;margin:12px 0 4px}}.related{{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 18px;font-size:14px}}.ctaBox{{margin-top:24px;padding:18px;border-radius:18px;background:#20190f;border:1px solid var(--line)}}footer{{font-size:12px;color:var(--muted);margin-top:18px}}</style>
</head><body><main><nav><strong>Teranga <span style="color:var(--gold)">AI</span></strong><a href="/">{escape({"en":"Ask Teranga AI","es":"Preguntar a Teranga AI","de":"Teranga AI fragen","it":"Chiedi a Teranga AI","fr":"Poser une question"}[lang])}</a></nav>
<div class="related">{related}</div><article><div class="kicker">Senegal · {escape(LANG_NAMES[lang])}</div>
<h1>{escape(title)}</h1><p class="intro">{escape(description)}</p>{sections}
<section><h2>{"Frequently asked questions" if lang=="en" else "Preguntas frecuentes" if lang=="es" else "Häufige Fragen" if lang=="de" else "Domande frequenti" if lang=="it" else "Questions fréquentes"}</h2>{faq}</section>
<div class="ctaBox"><strong>{escape(cta)}</strong><p><a href="/">{escape({"en":"Open Teranga AI","es":"Abrir Teranga AI","de":"Teranga AI öffnen","it":"Apri Teranga AI","fr":"Ouvrir Teranga AI"}[lang])}</a></p></div>
</article><footer>Teranga AI · {", ".join(LANG_NAMES.values())}</footer></main></body></html>"""
    return Response(html, mimetype="text/html", headers={"Cache-Control":"public, max-age=3600"})

def register_localized_routes(app, site_url):
    @app.get("/<lang>/<topic>")
    def localized_travel_page(lang, topic):
        response = render_international_page(lang, topic, site_url)
        if response is None:
            from flask import abort
            abort(404)
        return response


def localized_sitemap_urls(site_url):
    return [
        f"{site_url.rstrip('/')}/{lang}/{topic}"
        for lang in LANGS for topic in TOPICS
    ]

def localized_routes():
    return {(lang, topic) for lang in LANGS for topic in TOPICS}
\n\n# --- Rich topic-specific content layer ---\nconst TOPIC_VALUE = {
    "senegal-travel-guide": {
        "en": "Build the trip around a few hubs rather than trying to cover the whole country at once. Dakar works well as a base for Gorée and nearby coastal outings, while Saint-Louis, Sine-Saloum, Casamance and Kédougou offer very different landscapes and travel rhythms.",
        "es": "Conviene organizar el viaje alrededor de varias bases en lugar de intentar recorrer todo el país. Dakar facilita las excursiones a Gorée y la costa, mientras Saint-Louis, Sine-Saloum, Casamance y Kédougou ofrecen experiencias y ritmos muy distintos.",
        "de": "Plane die Reise besser über einige Etappen statt über das ganze Land auf einmal. Dakar eignet sich als Ausgangspunkt für Gorée und die Küste; Saint-Louis, Sine-Saloum, Casamance und Kédougou bieten jeweils andere Landschaften und Reiserhythmen.",
        "it": "È utile organizzare il viaggio intorno a poche basi invece di cercare di vedere tutto il paese. Dakar è pratica per Gorée e la costa, mentre Saint-Louis, Sine-Saloum, Casamance e Kédougou hanno paesaggi e ritmi di viaggio molto diversi.",
        "fr": "Organisez le voyage autour de quelques étapes plutôt que de vouloir couvrir tout le pays. Dakar est pratique pour Gorée et la côte proche, tandis que Saint-Louis, le Sine-Saloum, la Casamance et Kédougou offrent des paysages et des rythmes très différents."
    },
    "dakar-travel-guide": {
        "en": "Dakar is best planned by neighborhood and travel time. Group Plateau, Médina and the waterfront separately from Ngor, Almadies or Mamelles so that you spend less time crossing the city and more time visiting.",
        "es": "Dakar se planifica mejor por barrios y tiempos de desplazamiento. Agrupa Plateau, Medina y el frente marítimo por un lado, y Ngor, Almadies o Mamelles por otro para reducir los trayectos.",
        "de": "Dakar lässt sich am besten nach Vierteln und Fahrzeiten planen. Kombiniere Plateau, Medina und die Uferzone getrennt von Ngor, Almadies oder Mamelles, damit weniger Zeit für Wege verloren geht.",
        "it": "Dakar si organizza meglio per quartieri e tempi di spostamento. Raggruppa Plateau, Medina e zona costiera separatamente da Ngor, Almadies o Mamelles per ridurre gli attraversamenti della città.",
        "fr": "Dakar se planifie mieux par quartiers et temps de trajet. Regroupez Plateau, la Médina et le front de mer séparément de Ngor, Almadies ou Mamelles pour limiter les déplacements."
    },
    "things-to-do-in-dakar": {
        "en": "Mix cultural visits with open-air time: Gorée, museums and monuments can be combined with markets, coastal viewpoints, beaches and food stops. Leave some flexibility because traffic and opening times can affect a day.",
        "es": "Combina visitas culturales y actividades al aire libre: Gorée, museos y monumentos pueden alternarse con mercados, miradores, playas y pausas gastronómicas. Mantén margen por el tráfico y los horarios.",
        "de": "Kombiniere Kultur mit Zeit im Freien: Gorée, Museen und Monumente lassen sich mit Märkten, Küstenblicken, Stränden und Essen verbinden. Plane Puffer für Verkehr und wechselnde Öffnungszeiten ein.",
        "it": "Alterna cultura e attività all'aperto: Gorée, musei e monumenti possono essere combinati con mercati, panorami sulla costa, spiagge e soste gastronomiche. Lascia margine per traffico e orari.",
        "fr": "Alternez visites culturelles et plein air : Gorée, musées et monuments peuvent être combinés avec marchés, points de vue, plages et pauses gourmandes. Gardez une marge pour les trajets et les horaires."
    },
    "things-to-do-in-senegal": {
        "en": "Choose regions according to the experience you want: history and urban culture around Dakar and Saint-Louis, waterways and wildlife in Sine-Saloum, beaches and villages along the Petite Côte, and a different southern or southeastern atmosphere in Casamance and Kédougou.",
        "es": "Elige las regiones según la experiencia buscada: historia y cultura urbana en Dakar y Saint-Louis, agua y naturaleza en Sine-Saloum, playas en Petite Côte y ambientes diferentes en Casamance y Kédougou.",
        "de": "Wähle Regionen nach dem gewünschten Erlebnis: Geschichte und Stadtkultur in Dakar und Saint-Louis, Wasserlandschaften in Sine-Saloum, Strände an der Petite Côte sowie eine andere Atmosphäre in Casamance und Kédougou.",
        "it": "Scegli le regioni in base all'esperienza desiderata: storia e cultura urbana a Dakar e Saint-Louis, ambienti d'acqua nel Sine-Saloum, spiagge sulla Petite Côte e atmosfere diverse in Casamance e Kédougou.",
        "fr": "Choisissez les régions selon l’expérience recherchée : histoire et culture urbaine à Dakar et Saint-Louis, paysages d’eau au Sine-Saloum, plages sur la Petite Côte, et ambiances différentes en Casamance et à Kédougou."
    },
    "dakar-airport-to-city": {
        "en": "Blaise Diagne International Airport is outside central Dakar, so airport-to-city time matters when planning a first or last day. Compare the available transfer options for your arrival time, destination and luggage rather than relying on a fixed journey estimate.",
        "es": "El aeropuerto Blaise Diagne está fuera del centro de Dakar, por lo que el tiempo de traslado importa el primer y último día. Compara las opciones según hora de llegada, destino y equipaje.",
        "de": "Der Flughafen Blaise Diagne liegt außerhalb des Zentrums von Dakar. Berücksichtige daher die Transferzeit am ersten und letzten Tag und vergleiche Optionen nach Ankunftszeit, Ziel und Gepäck.",
        "it": "L'aeroporto Blaise Diagne è fuori dal centro di Dakar, quindi il trasferimento conta soprattutto il primo e l'ultimo giorno. Confronta le opzioni in base a orario di arrivo, destinazione e bagagli.",
        "fr": "L’aéroport Blaise Diagne se situe en dehors du centre de Dakar : le temps de transfert compte donc pour le premier et le dernier jour. Comparez les options selon l’heure d’arrivée, la destination et les bagages."
    },
    "goree-island": {
        "en": "Treat Gorée as a half-day or full-day outing depending on your pace. Check the current ferry timetable before leaving Dakar, then allow time for the island's historical sites, streets, waterfront and a meal or break.",
        "es": "Considera Gorée como una excursión de medio día o de día completo según tu ritmo. Comprueba el horario actual del ferry antes de salir de Dakar y reserva tiempo para los lugares históricos y el paseo por la isla.",
        "de": "Plane Gorée je nach Tempo als Halb- oder Ganztagesausflug. Prüfe den aktuellen Fährplan vor der Abfahrt und plane Zeit für historische Orte, Gassen, Ufer und eine Pause ein.",
        "it": "Considera Gorée un'escursione di mezza o intera giornata in base al ritmo. Controlla l'orario attuale del traghetto prima di partire e lascia tempo per luoghi storici, strade, costa e una pausa.",
        "fr": "Prévoyez Gorée comme une demi-journée ou une journée complète selon votre rythme. Vérifiez l’horaire actuel du ferry avant de partir et gardez du temps pour les lieux historiques, les ruelles et le bord de mer."
    },
    "where-to-eat-in-dakar": {
        "en": "Dakar's food scene varies strongly by neighborhood and budget. For a first visit, decide whether you want traditional Senegalese dishes, seafood, casual local food or a more contemporary restaurant, then choose an area that fits your itinerary.",
        "es": "La oferta gastronómica de Dakar cambia mucho según el barrio y el presupuesto. Decide si buscas cocina senegalesa tradicional, marisco, comida local informal o restaurantes contemporáneos y elige la zona según tu itinerario.",
        "de": "Dakar bietet je nach Viertel und Budget sehr unterschiedliche Küche. Entscheide zuerst, ob du traditionelle senegalesische Gerichte, Meeresfrüchte, einfache lokale Küche oder moderne Restaurants suchst, und wähle dann die passende Gegend.",
        "it": "La scena gastronomica di Dakar cambia molto per quartiere e budget. Decidi se cerchi piatti senegalesi tradizionali, pesce, cucina locale informale o ristoranti contemporanei, poi scegli la zona in base all'itinerario.",
        "fr": "La scène gastronomique de Dakar varie beaucoup selon le quartier et le budget. Déterminez si vous cherchez des plats sénégalais traditionnels, des produits de la mer, une cuisine locale simple ou une adresse contemporaine, puis choisissez le secteur selon votre itinéraire."
    },
    "senegal-transport": {
        "en": "Transport planning depends on distance, road conditions, departure time and comfort level. For intercity trips, compare current schedules and operators; inside Dakar, allow extra time for traffic and choose the mode that fits the neighborhood and time of day.",
        "es": "El transporte depende de la distancia, el estado de las carreteras, la hora y el nivel de comodidad. Para viajes entre ciudades, compara horarios y operadores actuales; en Dakar, deja margen por el tráfico.",
        "de": "Die Verkehrswahl hängt von Entfernung, Straßenlage, Abfahrtszeit und Komfort ab. Für Fernstrecken solltest du aktuelle Fahrpläne und Anbieter vergleichen; in Dakar ist zusätzlicher Puffer wegen des Verkehrs sinnvoll.",
        "it": "La scelta del trasporto dipende da distanza, strade, orario e comfort. Per gli spostamenti tra città confronta orari e operatori attuali; a Dakar considera margine extra per il traffico.",
        "fr": "Le choix du transport dépend de la distance, de l’état des routes, de l’horaire et du confort recherché. Pour les trajets interurbains, comparez les horaires et opérateurs actuels ; à Dakar, prévoyez une marge pour le trafic."
    },
    "senegal-sim-card": {
        "en": "For mobile connectivity, check whether your phone is unlocked and whether an eSIM is supported before departure. On arrival, compare current tourist or prepaid offers, coverage for your destinations and the identification requirements of the operator.",
        "es": "Antes de viajar, comprueba que el teléfono esté desbloqueado y sea compatible con eSIM si la necesitas. Al llegar, compara las ofertas actuales, la cobertura y los requisitos de identificación del operador.",
        "de": "Prüfe vor der Reise, ob dein Telefon entsperrt ist und eSIM unterstützt. Vor Ort solltest du aktuelle Prepaid-Angebote, Netzabdeckung für deine Ziele und die Identifikationsanforderungen vergleichen.",
        "it": "Prima della partenza verifica che il telefono sia sbloccato e compatibile con eSIM. All'arrivo confronta offerte attuali, copertura nelle destinazioni e requisiti di identificazione dell'operatore.",
        "fr": "Avant le départ, vérifiez que votre téléphone est désimlocké et compatible eSIM si besoin. À l’arrivée, comparez les offres actuelles, la couverture sur vos destinations et les exigences d’identification de l’opérateur."
    },
    "senegal-weather": {
        "en": "Senegal has distinct seasonal patterns, but conditions vary by region and can change day to day. Use climate information for broad planning and a current forecast for your exact dates, especially when planning outdoor activities or regional travel.",
        "es": "Senegal tiene patrones estacionales marcados, pero las condiciones varían según la región y el día. Usa el clima para planificar a grandes rasgos y un pronóstico actual para tus fechas exactas.",
        "de": "Senegal hat ausgeprägte Jahreszeiten, doch Wetter und Bedingungen unterscheiden sich regional und von Tag zu Tag. Nutze Klimadaten für die grobe Planung und eine aktuelle Prognose für deine Reisedaten.",
        "it": "Il Senegal ha stagioni ben definite, ma le condizioni cambiano in base alla regione e al giorno. Usa i dati climatici per la pianificazione generale e le previsioni attuali per le date precise.",
        "fr": "Le Sénégal connaît des saisons marquées, mais les conditions varient selon les régions et d’un jour à l’autre. Utilisez les repères climatiques pour préparer le voyage et une prévision actuelle pour vos dates."
    },
    "senegal-visa": {
        "en": "Entry requirements depend on nationality, travel document and current rules. Do not rely on an old blog or a generic visa summary: check the relevant official authority for your nationality and travel date before departure.",
        "es": "Los requisitos de entrada dependen de la nacionalidad, el documento de viaje y las reglas vigentes. No te bases en una página antigua: consulta la autoridad oficial correspondiente antes de viajar.",
        "de": "Einreisebestimmungen hängen von Nationalität, Reisedokument und den aktuell geltenden Regeln ab. Verlasse dich nicht auf alte Blogs, sondern prüfe vor der Reise die zuständige offizielle Stelle.",
        "it": "I requisiti di ingresso dipendono da nazionalità, documento di viaggio e norme vigenti. Non affidarti a vecchi blog: verifica prima della partenza l'autorità ufficiale competente.",
        "fr": "Les conditions d’entrée dépendent de la nationalité, du document de voyage et des règles en vigueur. Ne vous fiez pas à un ancien article : vérifiez l’autorité officielle compétente avant le départ."
    },
    "senegal-trip-planner": {
        "en": "A useful itinerary starts with constraints: dates, arrival point, budget, pace and must-see interests. Once those are clear, Teranga AI can help compare routes and organize days without pretending that changing schedules or prices are fixed.",
        "es": "Un buen itinerario empieza por las restricciones: fechas, punto de llegada, presupuesto, ritmo e intereses prioritarios. Con esos datos, Teranga AI puede comparar rutas y organizar días, verificando los datos variables.",
        "de": "Ein guter Reiseplan beginnt mit den Rahmenbedingungen: Daten, Ankunftsort, Budget, Tempo und Interessen. Danach kann Teranga AI Routen vergleichen und Tage strukturieren, während variable Angaben geprüft werden sollten.",
        "it": "Un buon itinerario parte dai vincoli: date, arrivo, budget, ritmo e interessi principali. Con questi dati Teranga AI può confrontare percorsi e organizzare le giornate, verificando le informazioni variabili.",
        "fr": "Un bon itinéraire commence par les contraintes : dates, arrivée, budget, rythme et centres d’intérêt prioritaires. Teranga AI peut ensuite comparer les options et structurer les journées, tout en vérifiant les données variables."
    }
};\n\nconst _base_render_international_page = render_international_page;\n\nfunction render_international_page(lang, topic, site_url) {\n    const response = _base_render_international_page(lang, topic, site_url);\n    if (!response) return response;\n    const text = response.get_data(as_text=true);\n    const value = TOPIC_VALUE[topic] && TOPIC_VALUE[topic][lang];\n    if (!value) return response;\n    const heading = {en:"Practical focus",es:"Enfoque práctico",de:"Praktischer Fokus",it:"Focus pratico",fr:"Focus pratique"}[lang];\n    const section = "<section><h2>" + escape(heading) + "</h2><p>" + escape(value) + "</p></section>";\n    const marker = "<section><h2>" + ({en:"Frequently asked questions",es:"Preguntas frecuentes",de:"Häufige Fragen",it:"Domande frequenti",fr:"Questions fréquentes"}[lang]) + "</h2>";\n    return new Response(text.replace(marker, section + marker), mimetype="text/html", headers={"Cache-Control":"public, max-age=3600"});\n}\n