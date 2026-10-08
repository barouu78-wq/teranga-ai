"""Page « Urgences et numéros utiles » : lisible hors connexion (service worker).

Numéros vérifiés le 6 octobre 2026 auprès de l'ambassade de France au Sénégal
(sn.ambafrance.org/Numeros-d-urgence) et d'annuaires sénégalais. Les numéros
nationaux (17, 18, 1515) sont gratuits depuis tous les téléphones, même sans crédit.
"""

from __future__ import annotations

import json
from html import escape

from flask import Response

from services.site_layout import HEAD_ASSETS, site_footer, site_header, social_meta

# (numéro affiché, numéro à composer, service, quand appeler)
EMERGENCY_NUMBERS = (
    ("17", "17", "Police secours", "Vol, agression, accident, toute situation qui demande les forces de l'ordre."),
    ("18", "18", "Sapeurs-pompiers", "Incendie, accident de la route, noyade, effondrement, secours aux personnes."),
    ("1515", "1515", "SAMU (urgence médicale)", "Malaise, maladie grave, accouchement difficile : envoi d'une ambulance médicalisée."),
    ("800 00 20 20", "+221800002020", "Gendarmerie nationale", "Numéro vert, gratuit. Hors des villes, la gendarmerie est souvent la plus proche."),
    ("33 889 15 15", "+221338891515", "SOS Médecins (Dakar)", "Médecin à domicile ou à l'hôtel, à Dakar."),
)

ADVICE = (
    "Les numéros 17, 18 et 1515 sont gratuits depuis tous les téléphones (Orange, Free, Expresso), même sans crédit.",
    "Donne d'abord le lieu exact (quartier, repère connu, nom de l'hôtel), puis ce qui se passe.",
    "Pharmacie de garde : demande à ton hôtel ou à ton hôte, ou regarde la liste affichée sur la porte des pharmacies.",
    "Voyageur étranger : signale-toi à ton ambassade ou à ton consulat en cas de problème grave (perte de passeport, hospitalisation, arrestation).",
)

EMBASSY_LINKS = (
    ("France", "https://sn.ambafrance.org/Numeros-d-urgence"),
    ("Conseils aux voyageurs (France)", "https://www.diplomatie.gouv.fr/fr/information-par-pays/senegal/conseils-aux-voyageurs-contacts-utiles"),
)

TITLE = "Urgences au Sénégal : police, pompiers, SAMU | Teranga AI"
DESCRIPTION = (
    "Numéros d'urgence du Sénégal : police 17, pompiers 18, SAMU 1515, gendarmerie, SOS Médecins Dakar. "
    "Gratuits, même sans crédit. Lisible hors connexion."
)


def render_emergency_page(site_url: str) -> str:
    cards = "".join(
        f'<div class="card"><h3>{escape(service)}</h3>'
        f'<p><a class="cta primary" href="tel:{escape(dial)}">📞 {escape(shown)}</a></p>'
        f"<p>{escape(when)}</p></div>"
        for shown, dial, service, when in EMERGENCY_NUMBERS
    )
    advice = "".join(f"<li>{escape(item)}</li>" for item in ADVICE)
    links = "".join(
        f'<li><a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a></li>'
        for label, url in EMBASSY_LINKS
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Urgences et numéros utiles au Sénégal",
        "url": site_url.rstrip("/") + "/urgences",
        "inLanguage": "fr",
        "about": {"@type": "Country", "name": "Sénégal"},
    }
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(TITLE)}</title>
<meta name="description" content="{escape(DESCRIPTION)}">
<link rel="canonical" href="{escape(site_url.rstrip('/'))}/urgences">
<meta name="robots" content="index,follow">{social_meta(TITLE, DESCRIPTION, site_url.rstrip('/') + '/urgences', site_url)}{HEAD_ASSETS}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>
<body>{site_header()}<main><article><div class="kicker">Sécurité</div>
<h1>Urgences et numéros utiles au Sénégal</h1>
<p class="intro">En cas d'urgence, appelle directement le bon service. Cette page reste lisible sans connexion une fois ouverte.</p>
<section><h2>Numéros d'urgence</h2><div class="grid">{cards}</div></section>
<section><h2>Bons réflexes</h2><ul>{advice}</ul></section>
<section><h2>Ambassades et conseils officiels</h2><ul>{links}</ul>
<p class="muted">Pour une autre nationalité, cherche « ambassade de ton pays à Dakar » : le site officiel donne le numéro de permanence.</p></section>
<p class="muted">Numéros vérifiés en octobre 2026 auprès de sources officielles. En cas de doute, le 17, le 18 et le 1515 restent les numéros nationaux.</p>
</article></main>{site_footer()}</body></html>"""


def register_emergency_routes(app, site_url: str) -> None:
    @app.get("/urgences")
    def emergency_page():
        return Response(
            render_emergency_page(site_url),
            mimetype="text/html",
            headers={"Cache-Control": "public, max-age=86400"},
        )
