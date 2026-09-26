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
<title>{escape(title)}</title><script type="application/ld+json">{json.dumps(ld,ensure_ascii=False).replace("<","\\u003c")}</script>
<style>:root{{--bg:#0b0907;--text:#f6efe3;--muted:#b8a48c;--gold:#e2b34a;--line:rgba(226,179,74,.18)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,sans-serif}}main{{width:min(860px,calc(100% - 32px));margin:auto;padding:28px 0 56px}}nav{{display:flex;justify-content:space-between;margin-bottom:20px}}a{{color:var(--gold);text-decoration:none;font-weight:750}}article{{background:#171310;border:1px solid var(--line);border-radius:28px;padding:28px}}.kicker{{color:var(--gold);font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:800}}h1{{font:700 clamp(32px,6vw,48px)/1.08 Georgia,serif;margin:10px 0 16px}}.intro{{font-size:18px;color:var(--muted)}}section{{padding:18px 0;border-top:1px solid var(--line)}}h2{{font-size:20px;margin:0 0 6px}}h3{{font-size:16px;margin:12px 0 4px}}.related{{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 18px;font-size:14px}}.ctaBox{{margin-top:24px;padding:18px;border-radius:18px;background:#20190f;border:1px solid var(--line)}}footer{{font-size:12px;color:var(--muted);margin-top:18px}}</style>
</head><body><main><nav><strong>Teranga <span style="color:var(--gold)">AI</span></strong><a href="/">{escape({"en":"Ask Teranga AI","es":"Preguntar a Teranga AI","de":"Teranga AI fragen","it":"Chiedi a Teranga AI","fr":"Poser une question"}[lang])}</a></nav>
<div class="related">{related}</div><article><div class="kicker">Senegal · {escape(LANG_NAMES[lang])}</div>
<h1>{escape(title)}</h1><p class="intro">{escape(description)}</p>{sections}
<section><h2>{"Frequently asked questions" if lang=="en" else "Preguntas frecuentes" if lang=="es" else "Häufige Fragen" if lang=="de" else "Domande frequenti" if lang=="it" else "Questions fréquentes"}</h2>{faq}</section>
<div class="ctaBox"><strong>{escape(cta)}</strong><p><a href="/">{escape({"en":"Open Teranga AI","es":"Abrir Teranga AI","de":"Teranga AI öffnen","it":"Apri Teranga AI","fr":"Ouvrir Teranga AI"}[lang])}</a></p></div>
</article><footer>Teranga AI · {", ".join(LANG_NAMES.values())}</footer></main></body></html>"""
    return Response(html, mimetype="text/html", headers={"Cache-Control":"public, max-age=3600"})

def localized_sitemap_urls(site_url):
    return [
        f"{site_url.rstrip('/')}/{lang}/{topic}"
        for lang in LANGS for topic in TOPICS
    ]

def localized_routes():
    return {(lang, topic) for lang in LANGS for topic in TOPICS}
