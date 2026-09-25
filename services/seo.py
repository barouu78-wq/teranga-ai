from flask import Response
import json

SEO_PAGES = {
    "senegal": {
        "title": "Guide S\u00e9n\u00e9gal : Dakar, Gor\u00e9e, 14 r\u00e9gions | Teranga AI",
        "description": "Guide pratique du S\u00e9n\u00e9gal : Dakar, Gor\u00e9e, m\u00e9t\u00e9o, o\u00f9 manger, AIBD. Assistant gratuit en fran\u00e7ais, wolof et pulaar.",
        "h1": "Guide du S\u00e9n\u00e9gal",
        "intro": "Teranga AI aide \u00e0 s\u2019orienter au S\u00e9n\u00e9gal : une question, une r\u00e9ponse courte. Horaires et tarifs se v\u00e9rifient le jour J.",
        "sections": [
            ("Que demander", "M\u00e9t\u00e9o Dakar, ferry Gor\u00e9e, trajet AIBD, ceebu j\u00ebn, quartiers pour manger, les 14 r\u00e9gions."),
            ("Rep\u00e8res", "14 r\u00e9gions. Dakar pour l\u2019arriv\u00e9e. Saint-Louis, Lac Rose, Petite C\u00f4te, Touba, Casamance au sud."),
            ("Langues", "Fran\u00e7ais, anglais, wolof et pulaar."),
        ],
        "faq": [
            ("Teranga AI est-il gratuit ?", "Oui. Aucune inscription n\u2019est obligatoire."),
            ("\u00c7a marche dans quelle langue ?", "Fran\u00e7ais, anglais, wolof et pulaar."),
        ],
        "related": [("meteo-dakar", "M\u00e9t\u00e9o Dakar"), ("visiter-goree", "Gor\u00e9e"), ("regions-senegal", "14 r\u00e9gions")],
    },
    "meteo-dakar": {
        "title": "M\u00e9t\u00e9o Dakar aujourd\u2019hui : chaleur, vent, ciel | Teranga AI",
        "description": "M\u00e9t\u00e9o Dakar du jour. Demandez \u00e0 Teranga AI les conditions avant Gor\u00e9e, Ngor ou l\u2019a\u00e9roport AIBD.",
        "h1": "M\u00e9t\u00e9o Dakar",
        "intro": "Le temps \u00e0 Dakar change vite. Demandez \u00ab Quelle m\u00e9t\u00e9o \u00e0 Dakar aujourd\u2019hui ? \u00bb pour une r\u00e9ponse courte.",
        "sections": [
            ("Questions utiles", "M\u00e9t\u00e9o Dakar aujourd\u2019hui, demain \u00e0 Ngor, v\u00e9rifier avant le ferry Gor\u00e9e."),
            ("Saisons", "Saison s\u00e8che plut\u00f4t novembre\u2013mai, pluies souvent de juin \u00e0 octobre. Ce sont des rep\u00e8res, pas une pr\u00e9vision."),
            ("Ensuite", "Ajoutez un lieu : plage, \u00eele, AIBD. Teranga peut encha\u00eener avec une carte."),
        ],
        "faq": [
            ("La m\u00e9t\u00e9o est-elle en direct ?", "L\u2019assistant peut chercher les conditions r\u00e9centes. Pr\u00e9cisez aujourd\u2019hui ou demain."),
            ("Et hors Dakar ?", "Oui : Saint-Louis, Saly, Ziguinchor, Cap Skirring."),
        ],
        "related": [("visiter-goree", "Gor\u00e9e"), ("restaurants-dakar", "O\u00f9 manger"), ("senegal", "Guide")],
    },
    "visiter-goree": {
        "title": "Visiter Gor\u00e9e : Maison des Esclaves, ferry, photos | Teranga AI",
        "description": "\u00cele de Gor\u00e9e : histoire, Maison des Esclaves, ferry depuis Dakar. Photos et carte avec Teranga AI.",
        "h1": "Visiter l\u2019\u00eele de Gor\u00e9e",
        "intro": "Gor\u00e9e fait face \u00e0 Dakar. On y vient pour l\u2019histoire et la Maison des Esclaves. Demandez une r\u00e9ponse courte + photos + carte.",
        "sections": [
            ("S\u2019y rendre", "Ferry depuis le port de Dakar. Horaires et tarifs : \u00e0 v\u00e9rifier le jour du d\u00e9part."),
            ("Quoi voir", "Maison des Esclaves, ruelles, mus\u00e9es. Comptez 2 \u00e0 4 heures."),
            ("Question type", "\u00ab Parle-moi de Gor\u00e9e et montre l\u2019\u00eele \u00bb."),
        ],
        "faq": [
            ("Une demi-journ\u00e9e suffit-elle ?", "Oui, beaucoup de visites tiennent en une matin\u00e9e."),
            ("Faut-il r\u00e9server le ferry ?", "Souvent non. V\u00e9rifiez l\u2019affluence le jour J."),
        ],
        "related": [("meteo-dakar", "M\u00e9t\u00e9o"), ("restaurants-dakar", "Manger \u00e0 Dakar"), ("senegal", "Guide")],
    },
    "restaurants-dakar": {
        "title": "O\u00f9 manger \u00e0 Dakar : Plateau, M\u00e9dina, Almadies, Ngor | Teranga AI",
        "description": "O\u00f9 manger \u00e0 Dakar par quartier : Plateau, M\u00e9dina, Almadies, Ngor, Ouakam. Ceebu j\u00ebn, yassa, march\u00e9s.",
        "h1": "O\u00f9 manger \u00e0 Dakar",
        "intro": "On mange \u00e0 Dakar par quartier, pas par \u00ab meilleur resto unique \u00bb. Demandez un quartier. Teranga oriente sans inventer une enseigne ferm\u00e9e.",
        "sections": [
            ("Quartiers", "Plateau : centre. M\u00e9dina : cuisine du quotidien. Almadies et Ngor : mer. Ouakam : mix r\u00e9sidentiel."),
            ("Plats", "Ceebu j\u00ebn, yassa, maf\u00e9, dibi. Pr\u00e9cisez Casamance ou Saint-Louis pour une sp\u00e9cialit\u00e9 r\u00e9gionale."),
            ("March\u00e9s", "Demandez \u00ab pr\u00e8s de\u2026 \u00bb plut\u00f4t qu\u2019un classement."),
        ],
        "faq": [
            ("Y a-t-il des notes Google ?", "Non. L\u2019assistant situe le quartier et le type de plat."),
            ("Hors Dakar ?", "Saint-Louis, Saly, Ziguinchor, Cap Skirring."),
        ],
        "related": [("specialites-senegal", "Sp\u00e9cialit\u00e9s"), ("visiter-goree", "Gor\u00e9e"), ("meteo-dakar", "M\u00e9t\u00e9o")],
    },
    "specialites-senegal": {
        "title": "Sp\u00e9cialit\u00e9s du S\u00e9n\u00e9gal : ceebu j\u00ebn, yassa, maf\u00e9 | Teranga AI",
        "description": "Cuisine s\u00e9n\u00e9galaise : ceebu j\u00ebn, yassa, maf\u00e9, plats du Nord et de Casamance. O\u00f9 les go\u00fbter.",
        "h1": "Sp\u00e9cialit\u00e9s du S\u00e9n\u00e9gal",
        "intro": "La cuisine change selon la mer, le fleuve et la Casamance. Teranga cite 3 ou 4 plats, pas une liste infinie.",
        "sections": [
            ("Plats connus", "Ceebu j\u00ebn, yassa, maf\u00e9, dibi."),
            ("R\u00e9gions", "Nord : mil et fleuve. Centre : arachide. Casamance : riz, fruits, poisson fum\u00e9."),
            ("O\u00f9 chercher", "Un quartier \u00e0 Dakar, ou une ville : Saint-Louis, Kaolack, Ziguinchor."),
        ],
        "faq": [
            ("Quel plat est le plus cit\u00e9 ?", "Le ceebu j\u00ebn, souvent le midi."),
            ("Y a-t-il des photos ?", "Pour certains sujets, oui, via Wikimedia."),
        ],
        "related": [("restaurants-dakar", "O\u00f9 manger"), ("regions-senegal", "R\u00e9gions"), ("senegal", "Guide")],
    },
    "regions-senegal": {
        "title": "14 r\u00e9gions du S\u00e9n\u00e9gal : villes et carte | Teranga AI",
        "description": "Les 14 r\u00e9gions du S\u00e9n\u00e9gal : Dakar, Thi\u00e8s, Saint-Louis, Ziguinchor, Tambacounda. Villes et Casamance.",
        "h1": "Les 14 r\u00e9gions du S\u00e9n\u00e9gal",
        "intro": "Teranga situe une r\u00e9gion, une ville et un trajet, avec photo ou carte si le lieu est connu.",
        "sections": [
            ("Liste", "Dakar, Thi\u00e8s, Diourbel, Fatick, Kaolack, Kaffrine, Tambacounda, K\u00e9dougou, Kolda, S\u00e9dhiou, Ziguinchor, Saint-Louis, Louga, Matam."),
            ("Zones", "Ouest : Dakar\u2013Thi\u00e8s. Nord : Saint-Louis, Louga, Matam. Sud / Casamance : Ziguinchor, S\u00e9dhiou, Kolda."),
            ("\u00c0 demander", "\u00ab Pr\u00e9sente la Casamance \u00bb, \u00ab O\u00f9 est Saint-Louis ? \u00bb, \u00ab Comment aller \u00e0 Ziguinchor ? \u00bb"),
        ],
        "faq": [
            ("Combien de r\u00e9gions ?", "14 r\u00e9gions administratives."),
            ("La Casamance est-elle une r\u00e9gion ?", "C\u2019est le Sud, sur Ziguinchor, S\u00e9dhiou et Kolda."),
        ],
        "related": [("senegal", "Guide"), ("specialites-senegal", "Cuisine"), ("visiter-goree", "Gor\u00e9e")],
    },
}


def sitemap_xml(site_url):
    urls = [(\"/\", \"daily\", \"1.0\"), (\"/explorer\", \"weekly\", \"0.9\")]
    urls += [(f\"/{slug}\", \"weekly\", \"0.8\") for slug in SEO_PAGES]
    parts = [
        '<?xml version=\"1.0\" encoding=\"UTF-8\"?>',
        '<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">',
    ]
    for path, freq, pri in urls:
        parts.append(
            f\"<url><loc>{site_url}{path}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>\"
        )
    parts.append(\"</urlset>\")
    return Response(
        \"\".join(parts),
        mimetype=\"application/xml\",
        headers={\"Cache-Control\": \"public, max-age=86400\"},
    )


def render_seo_page(slug, site_url):
    page = SEO_PAGES.get(slug)
    if not page:
        return None
    sections = \"\".join(
        f\"<section><h2>{heading}</h2><p>{text}</p></section>\"
        for heading, text in page[\"sections\"]
    )
    faq_html = \"\"
    faq_ld = []
    if page.get(\"faq\"):
        items = \"\".join(f\"<div class='faq'><h3>{q}</h3><p>{a}</p></div>\" for q, a in page[\"faq\"])
        faq_html = f\"<section><h2>Questions fr\u00e9quentes</h2>{items}</section>\"
        faq_ld = [
            {\"@type\": \"Question\", \"name\": q, \"acceptedAnswer\": {\"@type\": \"Answer\", \"text\": a}}
            for q, a in page[\"faq\"]
        ]
    related = \"\".join(f'<a href=\"/{s}\">{label}</a>' for s, label in page.get(\"related\", []))
    related_html = (
        f'<nav class=\"related\">Voir aussi : {related}<a href=\"/explorer\">Explorer</a></nav>'
        if related
        else \"\"
    )
    if slug in {\"senegal\", \"regions-senegal\"}:
        source_link = (
            '<p class=\"source\">Source : <a href=\"https://www.tourisme.gouv.sn/donnees-generales-sur-le-senegal.html\" '
            'target=\"_blank\" rel=\"noopener noreferrer\">Minist\u00e8re du Tourisme du S\u00e9n\u00e9gal</a>.</p>'
        )
    else:
        source_link = (
            '<p class=\"source\">Rep\u00e8res : <a href=\"https://www.au-senegal.com/\" '
            'target=\"_blank\" rel=\"noopener noreferrer\">Au S\u00e9n\u00e9gal</a>.</p>'
        )
    url = f\"{site_url}/{slug}\"
    ld = {
        \"@context\": \"https://schema.org\",
        \"@graph\": [
            {
                \"@type\": \"WebPage\",
                \"name\": page[\"title\"],
                \"description\": page[\"description\"],
                \"url\": url,
                \"isPartOf\": {\"@type\": \"WebSite\", \"name\": \"Teranga AI\", \"url\": site_url + \"/\"},
                \"inLanguage\": \"fr\",
            },
            {
                \"@type\": \"BreadcrumbList\",
                \"itemListElement\": [
                    {\"@type\": \"ListItem\", \"position\": 1, \"name\": \"Accueil\", \"item\": site_url + \"/\"},
                    {\"@type\": \"ListItem\", \"position\": 2, \"name\": page[\"h1\"], \"item\": url},
                ],
            },
        ],
    }
    if faq_ld:
        ld[\"@graph\"].append({\"@type\": \"FAQPage\", \"mainEntity\": faq_ld})
    ld_json = json.dumps(ld, ensure_ascii=False).replace(\"<\", \"\\u003c\")
    html = f\"\"\"<!doctype html>
<html lang=\"fr\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"robots\" content=\"index,follow\">
<meta name=\"description\" content=\"{page[\"description\"]}\">
<link rel=\"canonical\" href=\"{url}\">
<meta property=\"og:site_name\" content=\"Teranga AI\">
<meta property=\"og:title\" content=\"{page[\"title\"]}\">
<meta property=\"og:description\" content=\"{page[\"description\"]}\">
<meta property=\"og:type\" content=\"article\">
<meta property=\"og:locale\" content=\"fr_SN\">
<meta property=\"og:url\" content=\"{url}\">
<meta property=\"og:image\" content=\"{site_url}/og.png\">
<meta name=\"twitter:card\" content=\"summary_large_image\">
<meta name=\"twitter:title\" content=\"{page[\"title\"]}\">
<meta name=\"twitter:description\" content=\"{page[\"description\"]}\">
<meta name=\"twitter:image\" content=\"{site_url}/og.png\">
<title>{page[\"title\"]}</title>
<script type=\"application/ld+json\">{ld_json}</script>
<style>
:root{{color-scheme:dark;--bg:#0b0907;--text:#f6efe3;--muted:#b8a48c;--gold:#e2b34a;--line:rgba(226,179,74,.18)}}
*{{box-sizing:border-box}}body{{margin:0;background:#0b0907;color:var(--text);font:16px/1.65 system-ui,sans-serif}}
main{{width:min(860px,100% - 32px);margin:auto;padding:28px 0 56px}}
nav{{display:flex;justify-content:space-between;margin-bottom:20px}}
.logo{{font-weight:800}}.logo em{{color:var(--gold);font-style:normal}}
nav a,.cta,.related a{{color:var(--gold);text-decoration:none;font-weight:750}}
.related{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 16px;font-size:14px}}
article{{background:#171310;border:1px solid var(--line);border-radius:28px;padding:28px}}
.kicker{{color:var(--gold);font-size:12px;letter-spacing:.12em;text-transform:uppercase;font-weight:800}}
h1{{font:700 clamp(32px,6vw,48px)/1.08 Georgia,serif;margin:10px 0 16px}}
.intro{{font-size:18px;color:var(--muted)}}
section{{padding:18px 0;border-top:1px solid var(--line)}}
h2{{font-size:20px;margin:0 0 6px}}h3{{font-size:16px;margin:12px 0 4px}}
.ctaBox{{margin-top:24px;padding:18px;border-radius:18px;background:#20190f;border:1px solid var(--line)}}
.source,footer{{font-size:12px;color:var(--muted)}}
</style>
</head>
<body><main>
<nav><div class=\"logo\">Teranga <em>AI</em></div><a href=\"/\">Poser une question \u2192</a></nav>
{related_html}
<article>
<div class=\"kicker\">S\u00e9n\u00e9gal \u00b7 Teranga AI</div>
<h1>{page[\"h1\"]}</h1>
<p class=\"intro\">{page[\"intro\"]}</p>
{sections}
{faq_html}
<div class=\"ctaBox\"><strong>Une question pr\u00e9cise ?</strong><p>R\u00e9ponse courte, photo et carte quand le lieu est connu.</p><a class=\"cta\" href=\"/\">Ouvrir Teranga AI \u2192</a></div>
{source_link}
</article>
<footer>Teranga AI \u00b7 FR \u00b7 EN \u00b7 WO \u00b7 PU</footer>
</main></body></html>\"\"\"
    return Response(html, mimetype=\"text/html\", headers={\"Cache-Control\": \"public, max-age=3600\"})
