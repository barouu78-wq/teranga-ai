from flask import Response
import json

SEO_PAGES = {
    "senegal": {
        "title": "Guide Senegal : Dakar, Goree, 14 regions | Teranga AI",
        "description": "Guide pratique du Senegal : Dakar, Goree, meteo, ou manger, AIBD. Assistant gratuit en francais, wolof et pulaar.",
        "h1": "Guide du Senegal",
        "intro": "Teranga AI aide a s'orienter au Senegal : une question, une reponse courte. Horaires et tarifs se verifient le jour J.",
        "sections": [
            ("Que demander", "Meteo Dakar, ferry Goree, trajet AIBD, ceebu jen, quartiers pour manger, les 14 regions."),
            ("Reperes", "14 regions. Dakar pour l'arrivee. Saint-Louis, Lac Rose, Petite Cote, Touba, Casamance au sud."),
            ("Langues", "Francais, anglais, wolof et pulaar."),
        ],
        "faq": [
            ("Teranga AI est-il gratuit ?", "Oui. Aucune inscription n'est obligatoire."),
            ("Ca marche dans quelle langue ?", "Francais, anglais, wolof et pulaar."),
        ],
        "related": [("meteo-dakar", "Meteo Dakar"), ("visiter-goree", "Goree"), ("regions-senegal", "14 regions")],
    },
    "meteo-dakar": {
        "title": "Meteo Dakar aujourd'hui : chaleur, vent, ciel | Teranga AI",
        "description": "Meteo Dakar du jour. Demandez a Teranga AI les conditions avant Goree, Ngor ou l'aeroport AIBD.",
        "h1": "Meteo Dakar",
        "intro": "Le temps a Dakar change vite. Demandez la meteo a Dakar aujourd'hui pour une reponse courte.",
        "sections": [
            ("Questions utiles", "Meteo Dakar aujourd'hui, demain a Ngor, verifier avant le ferry Goree."),
            ("Saisons", "Saison seche plutot novembre-mai, pluies souvent de juin a octobre. Ce sont des reperes, pas une prevision."),
            ("Ensuite", "Ajoutez un lieu : plage, ile, AIBD. Teranga peut enchainer avec une carte."),
        ],
        "faq": [
            ("La meteo est-elle en direct ?", "L'assistant peut chercher les conditions recentes. Precisez aujourd'hui ou demain."),
            ("Et hors Dakar ?", "Oui : Saint-Louis, Saly, Ziguinchor, Cap Skirring."),
        ],
        "related": [("visiter-goree", "Goree"), ("restaurants-dakar", "Ou manger"), ("senegal", "Guide")],
    },
    "visiter-goree": {
        "title": "Visiter Goree : Maison des Esclaves, ferry, photos | Teranga AI",
        "description": "Ile de Goree : histoire, Maison des Esclaves, ferry depuis Dakar. Photos et carte avec Teranga AI.",
        "h1": "Visiter l'ile de Goree",
        "intro": "Goree fait face a Dakar. On y vient pour l'histoire et la Maison des Esclaves. Demandez une reponse courte, photos et carte.",
        "sections": [
            ("S'y rendre", "Ferry depuis le port de Dakar. Horaires et tarifs : a verifier le jour du depart."),
            ("Quoi voir", "Maison des Esclaves, ruelles, musees. Comptez 2 a 4 heures."),
            ("Question type", "Parle-moi de Goree et montre l'ile."),
        ],
        "faq": [
            ("Une demi-journee suffit-elle ?", "Oui, beaucoup de visites tiennent en une matinee."),
            ("Faut-il reserver le ferry ?", "Souvent non. Verifiez l'affluence le jour J."),
        ],
        "related": [("meteo-dakar", "Meteo"), ("restaurants-dakar", "Manger a Dakar"), ("senegal", "Guide")],
    },
    "restaurants-dakar": {
        "title": "Ou manger a Dakar : Plateau, Medina, Almadies, Ngor | Teranga AI",
        "description": "Ou manger a Dakar par quartier : Plateau, Medina, Almadies, Ngor, Ouakam. Ceebu jen, yassa, marches.",
        "h1": "Ou manger a Dakar",
        "intro": "On mange a Dakar par quartier, pas par meilleur resto unique. Demandez un quartier. Teranga oriente sans inventer une enseigne fermee.",
        "sections": [
            ("Quartiers", "Plateau : centre. Medina : cuisine du quotidien. Almadies et Ngor : mer. Ouakam : mix residentiel."),
            ("Plats", "Ceebu jen, yassa, mafe, dibi. Precisez Casamance ou Saint-Louis pour une specialite regionale."),
            ("Marches", "Demandez pres de... plutot qu'un classement."),
        ],
        "faq": [
            ("Y a-t-il des notes Google ?", "Non. L'assistant situe le quartier et le type de plat."),
            ("Hors Dakar ?", "Saint-Louis, Saly, Ziguinchor, Cap Skirring."),
        ],
        "related": [("specialites-senegal", "Specialites"), ("visiter-goree", "Goree"), ("meteo-dakar", "Meteo")],
    },
    "specialites-senegal": {
        "title": "Specialites du Senegal : ceebu jen, yassa, mafe | Teranga AI",
        "description": "Cuisine senegalaise : ceebu jen, yassa, mafe, plats du Nord et de Casamance. Ou les gouter.",
        "h1": "Specialites du Senegal",
        "intro": "La cuisine change selon la mer, le fleuve et la Casamance. Teranga cite 3 ou 4 plats, pas une liste infinie.",
        "sections": [
            ("Plats connus", "Ceebu jen, yassa, mafe, dibi."),
            ("Regions", "Nord : mil et fleuve. Centre : arachide. Casamance : riz, fruits, poisson fume."),
            ("Ou chercher", "Un quartier a Dakar, ou une ville : Saint-Louis, Kaolack, Ziguinchor."),
        ],
        "faq": [
            ("Quel plat est le plus cite ?", "Le ceebu jen, souvent le midi."),
            ("Y a-t-il des photos ?", "Pour certains sujets, oui, via Wikimedia."),
        ],
        "related": [("restaurants-dakar", "Ou manger"), ("regions-senegal", "Regions"), ("senegal", "Guide")],
    },
    "france-senegal": {
        "title": "Sénégal et France : voyage, diaspora, démarches | Teranga AI",
        "description": "Teranga AI accompagne les personnes au Sénégal et en France : voyage, Dakar, AIBD, démarches, culture, langues et vie de la diaspora.",
        "h1": "Sénégal ↔ France",
        "intro": "Un assistant pensé pour les personnes qui vivent au Sénégal, voyagent entre le Sénégal et la France, ou gardent un lien avec le pays.",
        "sections": [
            ("Pour le Sénégal", "Dakar, AIBD, transport, météo, régions, gastronomie, culture et informations pratiques."),
            ("Pour la France", "Questions de voyage, préparation du séjour, repères culturels, langues et informations utiles pour la diaspora sénégalaise."),
            ("Langues", "Français, anglais, wolof et pulaar, selon la demande."),
        ],
        "faq": [
            ("Teranga AI fonctionne-t-il depuis la France ?", "Oui. Le service est accessible sur le web depuis la France comme depuis le Sénégal."),
            ("Peut-on préparer un voyage au Sénégal ?", "Oui. Demandez les formalités, le transport, les lieux, la météo ou les repères utiles ; les informations changeantes sont à vérifier."),
        ],
        "related": [("senegal", "Guide du Sénégal"), ("regions-senegal", "14 régions"), ("meteo-dakar", "Météo Dakar")],
    },
    "diaspora-senegalaise": {
        "title": "Diaspora sénégalaise : France, Sénégal et informations pratiques | Teranga AI",
        "description": "Assistant pour la diaspora sénégalaise en France et ailleurs : démarches, voyage, régions, culture, langues et vie pratique au Sénégal.",
        "h1": "Diaspora sénégalaise",
        "intro": "Teranga AI aide à garder un lien pratique avec le Sénégal : préparer un voyage, comprendre une démarche, retrouver une région ou découvrir une spécialité.",
        "sections": [
            ("Depuis la France", "Préparez un séjour au Sénégal, recherchez des repères sur Dakar et les régions, ou posez une question sur la culture et les langues."),
            ("Au Sénégal", "Transport, météo, gastronomie, lieux, cartes et informations pratiques selon le contexte."),
            ("Une réponse adaptée", "Précisez votre ville, votre région ou votre situation pour obtenir une réponse plus pertinente."),
        ],
        "faq": [
            ("L'assistant est-il réservé aux voyageurs ?", "Non. Il s'adresse aussi aux résidents, à la diaspora et aux commerçants."),
            ("Peut-on parler wolof ou pulaar ?", "Oui, Teranga AI prend en charge le wolof et le pulaar en plus du français et de l'anglais."),
        ],
        "related": [("france-senegal", "France ↔ Sénégal"), ("senegal", "Guide du Sénégal"), ("specialites-senegal", "Spécialités")],
    },
    "a-propos": {
        "title": "À propos de Teranga AI : assistant numérique du Sénégal",
        "description": "Découvrez Teranga AI, assistant numérique consacré au Sénégal : informations pratiques, voyage, culture, langues et vie quotidienne.",
        "h1": "À propos de Teranga AI",
        "intro": "Teranga AI est un assistant numérique pensé autour du Sénégal et accessible depuis le Sénégal, la France et la diaspora.",
        "sections": [
            ("Un assistant pour le Sénégal", "Teranga AI aide à trouver des repères sur Dakar, les régions, les transports, la météo, la culture, la gastronomie et les langues."),
            ("Pour plusieurs publics", "Voyageurs, résidents, diaspora et commerçants peuvent poser leurs questions en français, anglais, wolof ou pulaar."),
            ("Informations à vérifier", "Pour les horaires, tarifs, formalités et autres informations susceptibles de changer, Teranga AI peut rechercher des sources récentes et invite à vérifier les informations officielles."),
        ],
        "faq": [
            ("Teranga AI est-il accessible depuis le Sénégal ?", "Oui, le service est accessible sur le web depuis le Sénégal."),
            ("Quelles langues sont disponibles ?", "Français, anglais, wolof et pulaar."),
        ],
        "related": [("senegal", "Guide du Sénégal"), ("france-senegal", "France ↔ Sénégal"), ("diaspora-senegalaise", "Diaspora sénégalaise")],
    },
    "presse": {
        "title": "Presse et médias : Teranga AI au Sénégal",
        "description": "Informations presse sur Teranga AI : présentation, usages, langues et ressources pour les médias sénégalais.",
        "h1": "Presse et médias",
        "intro": "Cette page rassemble les informations essentielles pour présenter Teranga AI dans un article, une émission ou une publication numérique.",
        "sections": [
            ("Présentation courte", "Teranga AI est un assistant numérique consacré au Sénégal. Il répond aux questions pratiques sur les villes, régions, voyage, transport, culture, gastronomie, météo et langues."),
            ("Présentation longue", "Pensé pour les personnes au Sénégal et pour la diaspora, Teranga AI permet de poser une question en français, anglais, wolof ou pulaar. Pour les informations changeantes, l'assistant peut rechercher des sources récentes."),
            ("Contact presse", "Pour une demande média, utilisez les coordonnées de contact publiées par Teranga AI sur son site. Ne reprenez pas une information sensible sans la vérifier."),
        ],
        "faq": [
            ("Teranga AI est-il un média ?", "Non. Teranga AI est un service d'assistance numérique ; les informations journalistiques doivent être attribuées à leurs sources."),
            ("Peut-on utiliser Teranga AI pour préparer un reportage ?", "Oui, comme outil de recherche et de préparation, avec vérification des informations auprès des sources originales."),
        ],
        "related": [("a-propos", "À propos"), ("senegal", "Guide du Sénégal"), ("france-senegal", "France ↔ Sénégal")],
    },
    "media-kit": {
        "title": "Kit média Teranga AI : logo, présentation et ressources",
        "description": "Kit média Teranga AI pour journalistes, créateurs et partenaires : présentation, identité et ressources de communication.",
        "h1": "Kit média Teranga AI",
        "intro": "Une fiche simple pour présenter Teranga AI de manière cohérente sur un site, un média, une newsletter ou les réseaux sociaux.",
        "sections": [
            ("Nom", "Teranga AI"),
            ("Description courte", "Assistant numérique du Sénégal, accessible depuis le Sénégal et la diaspora, en français, anglais, wolof et pulaar."),
            ("Usages", "Voyage, Dakar, AIBD, transport, météo, régions, culture, gastronomie, langues et informations pratiques."),
            ("Lien officiel", "https://teranga-ai-1.onrender.com/"),
        ],
        "faq": [
            ("Peut-on reprendre la description courte ?", "Oui, en conservant le nom Teranga AI et en renvoyant vers le site officiel."),
            ("Les réponses de Teranga AI remplacent-elles les sources officielles ?", "Non. Les informations administratives, juridiques, tarifaires ou très récentes doivent être vérifiées auprès des sources compétentes."),
        ],
        "related": [("a-propos", "À propos"), ("presse", "Presse"), ("senegal", "Guide du Sénégal")],
    },
    "regions-senegal": {
        "title": "14 regions du Senegal : villes et carte | Teranga AI",
        "description": "Les 14 regions du Senegal : Dakar, Thies, Saint-Louis, Ziguinchor, Tambacounda. Villes et Casamance.",
        "h1": "Les 14 regions du Senegal",
        "intro": "Teranga situe une region, une ville et un trajet, avec photo ou carte si le lieu est connu.",
        "sections": [
            ("Liste", "Dakar, Thies, Diourbel, Fatick, Kaolack, Kaffrine, Tambacounda, Kedougou, Kolda, Sedhiou, Ziguinchor, Saint-Louis, Louga, Matam."),
            ("Zones", "Ouest : Dakar-Thies. Nord : Saint-Louis, Louga, Matam. Sud / Casamance : Ziguinchor, Sedhiou, Kolda."),
            ("A demander", "Presente la Casamance. Ou est Saint-Louis. Comment aller a Ziguinchor."),
        ],
        "faq": [
            ("Combien de regions ?", "14 regions administratives."),
            ("La Casamance est-elle une region ?", "C'est le Sud, sur Ziguinchor, Sedhiou et Kolda."),
        ],
        "related": [("senegal", "Guide"), ("specialites-senegal", "Cuisine"), ("visiter-goree", "Goree")],
    },

    "dakar": {
        "title": "Dakar : guide pratique, quartiers, transport et voyage | Teranga AI",
        "description": "Guide de Dakar : AIBD, quartiers, transport, météo, Gorée, restaurants et repères pratiques pour habitants et voyageurs.",
        "h1": "Dakar",
        "intro": "Teranga AI vous aide à préparer ou comprendre Dakar : arrivée à AIBD, déplacements, quartiers, météo, gastronomie et sorties.",
        "sections": [
            ("Arriver à Dakar", "Demandez un itinéraire depuis AIBD, un repère sur les transports ou les informations utiles pour votre arrivée. Les horaires et tarifs doivent être vérifiés le jour du trajet."),
            ("Quartiers et sorties", "Plateau, Médina, Almadies, Ngor, Ouakam et d'autres quartiers peuvent être abordés selon votre besoin : manger, dormir, se déplacer ou découvrir la ville."),
            ("Dakar et Gorée", "Pour une visite de Gorée, demandez les repères sur le ferry, la météo et les points d'intérêt. Les horaires de traversée sont à vérifier avant le départ."),
            ("Météo et vie pratique", "Demandez la météo du jour, une tenue adaptée, un trajet ou une information pratique. Pour les données qui changent, Teranga AI recherche des informations récentes lorsque nécessaire.")
        ],
        "faq": [
            ("Comment aller de AIBD à Dakar ?", "Demandez votre destination ou votre quartier et Teranga AI peut rechercher les options de transport récentes."),
            ("Quels quartiers de Dakar peut-on explorer ?", "Plateau, Médina, Almadies, Ngor, Ouakam et d'autres quartiers peuvent être décrits selon votre activité."),
            ("Peut-on préparer une journée à Dakar ?", "Oui. Indiquez votre point de départ, le temps disponible et vos centres d'intérêt.")
        ],
        "related": [("meteo-dakar", "Météo Dakar"), ("visiter-goree", "Visiter Gorée"), ("restaurants-dakar", "Restaurants Dakar"), ("senegal", "Guide du Sénégal")]
    },
    "assistant-senegal": {
        "title": "Assistant Sénégal : informations pratiques, voyage et Dakar | Teranga AI",
        "description": "Assistant Sénégal en ligne : questions sur Dakar, voyage, transport, météo, culture, cuisine, régions et vie pratique, en français, anglais, wolof et pulaar.",
        "h1": "Assistant Sénégal",
        "intro": "Teranga AI est un assistant numérique consacré au Sénégal. Posez une question sur Dakar, un trajet, une région, la météo, la culture ou la vie pratique.",
        "sections": [
            ("Voyage et déplacements", "Préparez un séjour au Sénégal, demandez des repères sur AIBD, Dakar, Gorée, les transports, les quartiers et les régions."),
            ("Vie pratique", "Posez une question sur la météo, les spécialités, les langues, les services ou une situation du quotidien. Pour les informations changeantes, les sources récentes doivent être vérifiées."),
            ("Pour le Sénégal et la diaspora", "Le service est accessible depuis le Sénégal, la France et ailleurs. Vous pouvez préciser votre ville, votre région ou votre contexte pour obtenir une réponse plus ciblée."),
        ],
        "faq": [
            ("Quelles langues peut-on utiliser ?", "Teranga AI prend en charge le français, l'anglais, le wolof et le pulaar."),
            ("Peut-on préparer un voyage au Sénégal ?", "Oui. Demandez des informations sur les lieux, transports, météo, culture et repères pratiques, puis vérifiez les informations susceptibles de changer."),
        ],
        "related": [("senegal", "Guide du Sénégal"), ("france-senegal", "Sénégal ↔ France"), ("meteo-dakar", "Météo Dakar"), ("regions-senegal", "14 régions")],
    },
}


def render_seo_page(slug, site_url):
    page = SEO_PAGES.get(slug)
    if not page:
        return None
    sections = "".join(
        "<section><h2>%s</h2><p>%s</p></section>" % (heading, text)
        for heading, text in page["sections"]
    )
    faq_html = ""
    faq_ld = []
    if page.get("faq"):
        items = "".join("<div class='faq'><h3>%s</h3><p>%s</p></div>" % (q, a) for q, a in page["faq"])
        faq_html = "<section><h2>Questions frequentes</h2>%s</section>" % items
        faq_ld = [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in page["faq"]
        ]
    related = "".join('<a href="/%s">%s</a>' % (s, label) for s, label in page.get("related", []))
    related_html = ""
    if related:
        related_html = '<nav class="related">Voir aussi : %s<a href="/explorer">Explorer</a></nav>' % related
    if slug in {"senegal", "regions-senegal"}:
        source_link = (
            '<p class="source">Source : <a href="https://www.tourisme.gouv.sn/donnees-generales-sur-le-senegal.html" '
            'target="_blank" rel="noopener noreferrer">Ministere du Tourisme du Senegal</a>.</p>'
        )
    else:
        source_link = (
            '<p class="source">Reperes : <a href="https://www.au-senegal.com/" '
            'target="_blank" rel="noopener noreferrer">Au Senegal</a>.</p>'
        )
    url = "%s/%s" % (site_url, slug)
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "name": page["title"],
                "description": page["description"],
                "url": url,
                "isPartOf": {"@type": "WebSite", "name": "Teranga AI", "url": site_url + "/"},
                "inLanguage": "fr",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": site_url + "/"},
                    {"@type": "ListItem", "position": 2, "name": page["h1"], "item": url},
                ],
            },
        ],
    }
    if faq_ld:
        ld["@graph"].append({"@type": "FAQPage", "mainEntity": faq_ld})
    ld_json = json.dumps(ld, ensure_ascii=True).replace("<", "\\u003c")
    html = """<!doctype html>
<html lang=\"fr\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"robots\" content=\"index,follow\">
<meta name=\"description\" content=\"%(description)s\">
<link rel=\"canonical\" href=\"%(url)s\">
<meta property=\"og:site_name\" content=\"Teranga AI\">
<meta property=\"og:title\" content=\"%(title)s\">
<meta property=\"og:description\" content=\"%(description)s\">
<meta property=\"og:type\" content=\"article\">
<meta property=\"og:locale\" content=\"fr_SN\">
<meta property=\"og:url\" content=\"%(url)s\">
<meta property=\"og:image\" content=\"%(site)s/og.png\">
<meta name=\"twitter:card\" content=\"summary_large_image\">
<meta name=\"twitter:title\" content=\"%(title)s\">
<meta name=\"twitter:description\" content=\"%(description)s\">
<meta name=\"twitter:image\" content=\"%(site)s/og.png\">
<title>%(title)s</title>
<script type=\"application/ld+json\">%(ld)s</script>
<style>
:root{color-scheme:dark;--bg:#0b0907;--text:#f6efe3;--muted:#b8a48c;--gold:#e2b34a;--line:rgba(226,179,74,.18)}
*{box-sizing:border-box}body{margin:0;background:#0b0907;color:var(--text);font:16px/1.65 system-ui,sans-serif}
main{width:min(860px,100%% - 32px);margin:auto;padding:28px 0 56px}
nav{display:flex;justify-content:space-between;margin-bottom:20px}
.logo{font-weight:800}.logo em{color:var(--gold);font-style:normal}
nav a,.cta,.related a{color:var(--gold);text-decoration:none;font-weight:750}
.related{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 16px;font-size:14px}
article{background:#171310;border:1px solid var(--line);border-radius:28px;padding:28px}
.kicker{color:var(--gold);font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:800}
h1{font:700 clamp(32px,6vw,48px)/1.08 Georgia,serif;margin:10px 0 16px}
.intro{font-size:18px;color:var(--muted)}
section{padding:18px 0;border-top:1px solid var(--line)}
h2{font-size:20px;margin:0 0 6px}h3{font-size:16px;margin:12px 0 4px}
.ctaBox{margin-top:24px;padding:18px;border-radius:18px;background:#20190f;border:1px solid var(--line)}
.source,footer{font-size:12px;color:var(--muted)}
</style>
</head>
<body><main>
<nav><div class=\"logo\">Teranga <em>AI</em></div><a href=\"/\">Poser une question</a></nav>
%(related)s
<article>
<div class=\"kicker\">Senegal · Teranga AI</div>
<h1>%(h1)s</h1>
<p class=\"intro\">%(intro)s</p>
%(sections)s
%(faq)s
<div class=\"ctaBox\"><strong>Une question precise ?</strong><p>Reponse courte, photo et carte quand le lieu est connu.</p><a class=\"cta\" href=\"/\">Ouvrir Teranga AI</a></div>
%(source)s
</article>
<footer>Teranga AI · FR · EN · WO · PU</footer>
</main></body></html>""" % {
        "description": page["description"],
        "url": url,
        "title": page["title"],
        "site": site_url,
        "ld": ld_json,
        "related": related_html,
        "h1": page["h1"],
        "intro": page["intro"],
        "sections": sections,
        "faq": faq_html,
        "source": source_link,
    }
    return Response(html, mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})
