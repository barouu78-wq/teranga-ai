from flask import Response

SEO_PAGES = {
    "senegal": {
        "title": "Sénégal : guide pratique et assistant IA | Teranga AI",
        "description": "Découvrez le Sénégal avec Teranga AI : Dakar, régions, cuisine, déplacements et informations pratiques.",
        "h1": "Sénégal : un assistant pour mieux s’orienter",
        "intro": "Teranga AI répond aux questions pratiques sur le Sénégal, en français, anglais, wolof et pulaar. L’objectif est simple : donner une réponse courte et signaler les informations qui peuvent changer.",
        "sections": [
            ("Que peut faire Teranga AI ?", "Météo, transports, lieux à visiter, cuisine, quartiers, démarches et questions du quotidien. Pour les informations sensibles au temps, l’assistant peut vérifier des sources en ligne."),
            ("Le Sénégal en quelques repères", "Le Sénégal est organisé en 14 régions. Dakar et sa presqu’île concentrent une grande partie des activités urbaines, tandis que le pays comprend aussi la vallée du fleuve, le Sine-Saloum, le Sénégal oriental et la Casamance."),
            ("Pour préparer un séjour", "Demandez un itinéraire, un quartier, une spécialité régionale ou une information pratique. Pour les horaires, tarifs, événements ou conditions du jour, demandez explicitement une vérification.")
        ],
        "source": "Données générales : Ministère du Tourisme et des Loisirs du Sénégal."
    },
    "meteo-dakar": {
        "title": "Météo Dakar : demander les conditions du jour | Teranga AI",
        "description": "Demandez la météo actuelle de Dakar à Teranga AI et obtenez une réponse adaptée à votre journée au Sénégal.",
        "h1": "Météo Dakar : vérifier le temps avant de sortir",
        "intro": "La météo est une information qui change. Teranga AI peut rechercher les conditions récentes lorsque vous demandez la météo de Dakar pour aujourd’hui, demain ou une date précise.",
        "sections": [
            ("Questions utiles", "Essayez : « Quelle météo à Dakar aujourd’hui ? », « Quel temps demain à Dakar ? » ou « Vérifie la météo avant ma sortie à Gorée »."),
            ("Pourquoi demander une date ?", "Une réponse météo dépend de la date et de l’heure. Précisez votre période pour éviter une information trop générale."),
            ("Dakar et ses déplacements", "Pour une journée à Dakar, vous pouvez aussi demander un itinéraire, un quartier, un trajet vers l’AIBD ou une idée de sortie en fonction de la météo.")
        ],
        "source": "Teranga AI privilégie les informations vérifiables et signale les données susceptibles de changer."
    },
    "visiter-goree": {
        "title": "Visiter l’île de Gorée : histoire et préparation | Teranga AI",
        "description": "Préparez une visite de l’île de Gorée au Sénégal : histoire, Maison des Esclaves et questions pratiques.",
        "h1": "Visiter l’île de Gorée",
        "intro": "Gorée est l’un des lieux historiques majeurs associés à Dakar. Teranga AI peut expliquer son histoire, présenter la Maison des Esclaves et aider à préparer les informations pratiques de la visite.",
        "sections": [
            ("Que voir ?", "La Maison des Esclaves et l’île elle-même sont des repères essentiels pour comprendre l’histoire de Gorée. L’assistant peut aussi expliquer les principaux lieux à découvrir."),
            ("Préparer le déplacement", "Pour les horaires de traversée, les tarifs ou les conditions du jour, demandez une vérification actuelle plutôt qu’un horaire mémorisé."),
            ("Une visite historique", "Pour une réponse plus complète, demandez à Teranga AI de replacer Gorée dans l’histoire de Dakar et de l’Afrique de l’Ouest.")
        ],
        "source": "Repères touristiques : documentation consacrée à Dakar et Gorée par Au Sénégal, le cœur du Sénégal."
    },
    "restaurants-dakar": {
        "title": "Restaurants à Dakar : choisir selon le quartier | Teranga AI",
        "description": "Cherchez où manger à Dakar selon le quartier : Plateau, Médina, Point E, Almadies, Ngor, Ouakam et la Corniche.",
        "h1": "Restaurants à Dakar : chercher par quartier",
        "intro": "À Dakar, le quartier compte autant que le type de cuisine. Teranga AI peut orienter une recherche vers une zone précise et éviter de présenter comme certain un restaurant, un prix ou un horaire qui aurait changé.",
        "sections": [
            ("Plateau et Médina", "Le centre de Dakar permet de chercher des adresses proches des grands axes et des marchés. Demandez une recherche selon votre budget et le type de cuisine."),
            ("Point E, Fann et Sicap", "Ces quartiers disposent d’une offre variée. Précisez si vous cherchez une cuisine sénégalaise, internationale, rapide ou un endroit adapté à un repas en famille."),
            ("Almadies, Ngor et Ouakam", "Pour la Corniche et l’ouest de Dakar, vous pouvez demander une recherche par proximité, plage ou ambiance. Les horaires et disponibilités doivent être vérifiés au moment de la demande.")
        ],
        "source": "Repères de quartiers : Au Sénégal, le cœur du Sénégal."
    },
    "specialites-senegal": {
        "title": "Spécialités du Sénégal : plats et cuisines régionales | Teranga AI",
        "description": "Découvrez les spécialités culinaires du Sénégal : ceebu jën, yassa, mafé et cuisines régionales.",
        "h1": "Spécialités du Sénégal : quoi goûter ?",
        "intro": "La cuisine sénégalaise varie selon les terroirs et les produits disponibles. Teranga AI peut présenter les plats, leur contexte régional et les endroits où chercher une cuisine traditionnelle.",
        "sections": [
            ("Plats connus", "Le ceebu jën, le yassa et le mafé font partie des plats très connus de la cuisine sénégalaise. Une recherche locale peut préciser où les chercher selon la ville."),
            ("Une cuisine régionale", "Les recettes et produits diffèrent selon les territoires. La Casamance, le Sine-Saloum, la vallée du fleuve et le Sénégal oriental possèdent leurs propres traditions culinaires."),
            ("À Dakar", "Dakar rassemble des cuisines venues de nombreuses régions du pays et des influences internationales. Pour trouver une adresse, demandez un quartier plutôt qu’un nom d’enseigne si vous n’avez pas de préférence.")
        ],
        "source": "Contexte culinaire : Au Sénégal, le cœur du Sénégal."
    },
    "regions-senegal": {
        "title": "Régions du Sénégal : carte et repères | Teranga AI",
        "description": "Découvrez les 14 régions du Sénégal et les grandes zones géographiques avec Teranga AI.",
        "h1": "Régions du Sénégal : les 14 régions",
        "intro": "Le Sénégal compte 14 régions administratives. Teranga AI peut expliquer leur localisation, leurs principales villes et les différences entre Dakar, le Nord, le Centre, la Casamance et l’Est.",
        "sections": [
            ("Les 14 régions", "Dakar, Thiès, Diourbel, Fatick, Kaolack, Kaffrine, Tambacounda, Kédougou, Kolda, Sédhiou, Ziguinchor, Saint-Louis, Louga et Matam."),
            ("De Dakar à la Casamance", "Dakar se situe à l’ouest. Le Nord comprend notamment Saint-Louis, Louga et Matam. Le Centre regroupe notamment Thiès, Diourbel, Fatick et Kaolack. La Casamance correspond au Sud, avec Ziguinchor, Sédhiou et Kolda."),
            ("Préparer un trajet", "Pour passer d’une région à une autre, demandez à Teranga AI un itinéraire et précisez votre moyen de transport. Les horaires, tarifs et conditions de circulation doivent être vérifiés lorsqu’ils sont importants.")
        ],
        "source": "Découpage administratif : Ministère du Tourisme et des Loisirs du Sénégal."
    },
}


def render_seo_page(slug, site_url):
    page = SEO_PAGES.get(slug)
    if not page:
        return None
    sections = "".join(
        f"<section><h2>{heading}</h2><p>{text}</p></section>"
        for heading, text in page["sections"]
    )
    source_link = ""
    if slug in {"senegal", "regions-senegal"}:
        source_link = '<p class="source">Source institutionnelle : <a href="https://www.tourisme.gouv.sn/donnees-generales-sur-le-senegal.html" target="_blank" rel="noopener noreferrer">Ministère du Tourisme et des Loisirs du Sénégal</a>.</p>'
    else:
        source_link = '<p class="source">Repères : <a href="https://www.au-senegal.com/" target="_blank" rel="noopener noreferrer">Au Sénégal, le cœur du Sénégal</a>.</p>'
    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<meta name="description" content="{page["description"]}">
<link rel="canonical" href="{site_url}/{slug}">
<meta property="og:title" content="{page["title"]}">
<meta property="og:description" content="{page["description"]}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE_URL}/{slug}">
<title>{page["title"]}</title>
<style>
:root{{color-scheme:dark;--bg:#0b0907;--card:#171310;--text:#f6efe3;--muted:#b8a48c;--gold:#e2b34a;--line:rgba(226,179,74,.18)}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(700px 300px at 90% 0,#2a2110 0,transparent 60%),var(--bg);color:var(--text);font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{width:min(860px,100% - 32px);margin:auto;padding:28px 0 56px}}
nav{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:42px}}
.logo{{font-weight:800;letter-spacing:-.04em}}.logo em{{color:var(--gold);font-style:normal}}
nav a,.cta{{color:var(--gold);text-decoration:none;font-weight:750}}
article{{background:rgba(23,19,16,.9);border:1px solid var(--line);border-radius:28px;padding:28px;box-shadow:0 24px 60px rgba(0,0,0,.35)}}
.kicker{{color:var(--gold);font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:800}}
h1{{font:700 clamp(32px,6vw,54px)/1.05 Georgia,serif;margin:10px 0 16px;letter-spacing:-.04em}}
.intro{{font-size:19px;color:var(--muted);max-width:65ch}}
section{{padding:18px 0;border-top:1px solid var(--line)}}h2{{font-size:21px;margin:0 0 6px}}p{{margin:0 0 8px}}
.ctaBox{{margin-top:24px;padding:18px;border-radius:18px;background:#20190f;border:1px solid var(--line)}}
.source{{font-size:12px;color:var(--muted);margin-top:22px}}footer{{margin-top:18px;color:var(--muted);font-size:12px}}
@media(max-width:600px){{main{{width:min(100% - 20px,860px);padding-top:16px}}article{{padding:20px;border-radius:22px}}nav{{margin-bottom:24px}}}}
</style>
</head>
<body><main>
<nav><div class="logo">Teranga <em>AI</em></div><a href="/">Poser une question →</a></nav>
<article>
<div class="kicker">Sénégal · Teranga AI</div>
<h1>{page["h1"]}</h1>
<p class="intro">{page["intro"]}</p>
{sections}
<div class="ctaBox"><strong>Besoin d’une réponse précise ?</strong><p>Posez votre question à Teranga AI et demandez une vérification lorsque l’information peut changer.</p><a class="cta" href="/">Ouvrir Teranga AI →</a></div>
{source_link}
</article>
<footer>Teranga AI · Assistant du Sénégal · Français · English · Wolof · Pulaar</footer>
</main></body></html>"""
    return Response(html, mimetype="text/html")


