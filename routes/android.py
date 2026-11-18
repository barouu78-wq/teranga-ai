"""Page « Télécharger l'application Android » (/telecharger).

Deux façons d'installer l'appli (TWA, paquet `fr.teranga_ai`) :
- l'APK signé par Google Play, publié en pièce jointe de la dernière « Release » GitHub
  (fichier `teranga-ai.apk`) : aucun binaire n'est commité dans le dépôt ;
- la fiche Google Play, affichée « Bientôt » tant que `ANDROID_PLAY_PUBLIC` n'est pas à 1
  (l'appli n'est pas encore en production : test fermé en cours).
"""

from __future__ import annotations

import json
import os
from html import escape

from flask import Response

from services.site_layout import HEAD_ASSETS, site_footer, site_header, social_meta

ANDROID_PACKAGE = "fr.teranga_ai"
APK_URL = "https://github.com/barouu78-wq/teranga-ai/releases/latest/download/teranga-ai.apk"
PLAY_URL = f"https://play.google.com/store/apps/details?id={ANDROID_PACKAGE}"
# Test fermé Google Play : les testeurs sont les membres de ce Groupe Google (ouvert à tous).
TESTERS_GROUP_URL = "https://groups.google.com/g/testeurs-teranga-ai"
TESTING_OPT_IN_URL = f"https://play.google.com/apps/testing/{ANDROID_PACKAGE}"

TITLE = "Télécharger l'appli Teranga AI pour Android | Teranga AI"
DESCRIPTION = (
    "Installe Teranga AI sur ton téléphone Android : l'assistant qui répond à tes questions "
    "sur le Sénégal en français, anglais et wolof."
)

APK_STEPS = (
    "Appuie sur « Télécharger l'APK », puis ouvre le fichier teranga-ai.apk depuis tes notifications ou tes Téléchargements.",
    "Si Android affiche « installation bloquée », appuie sur Paramètres et autorise cette source pour ton navigateur.",
    "Reviens en arrière et appuie sur Installer : Teranga AI apparaît sur ton écran d'accueil.",
)


def play_store_public() -> bool:
    return os.getenv("ANDROID_PLAY_PUBLIC", "").strip() == "1"


def render_download_page(site_url: str, play_public: bool = False) -> str:
    base = site_url.rstrip("/")
    steps = "".join(f"<li>{escape(step)}</li>" for step in APK_STEPS)
    if play_public:
        play = (
            f'<p><a class="cta" href="{escape(PLAY_URL)}" target="_blank" rel="noopener noreferrer">Ouvrir Google Play</a></p>'
            '<p class="muted">Mises à jour automatiques depuis le Play Store.</p>'
        )
    else:
        play = (
            '<p><span class="cta" aria-disabled="true" style="background:transparent;color:inherit;opacity:.7">Bientôt sur Google Play</span></p>'
            '<p class="muted">Disponible après la validation de Google.</p>'
        )
    testers = "" if play_public else (
        '<section class="ctaBox"><h2>Deviens testeur de l\'appli</h2>'
        "<p>Google demande que l'appli soit testée avant sa sortie sur le Play Store. "
        "Aide-nous avec ton compte Gmail, ça prend une minute :</p><ol>"
        f'<li><a class="cta primary" href="{escape(TESTERS_GROUP_URL)}" target="_blank" rel="noopener noreferrer">1. Rejoindre le groupe des testeurs</a></li>'
        f'<li><a class="cta" href="{escape(TESTING_OPT_IN_URL)}" target="_blank" rel="noopener noreferrer">2. Accepter le test et installer l\'appli</a></li>'
        "</ol><p class=\"muted\">Garde l'appli installée au moins 14 jours et dis-nous ce qui ne va pas : c'est tout.</p></section>"
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "MobileApplication",
        "name": "Teranga AI – Guide du Sénégal",
        "operatingSystem": "Android",
        "applicationCategory": "TravelApplication",
        "url": base + "/telecharger",
        "inLanguage": ["fr", "en", "wo"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
    }
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(TITLE)}</title>
<meta name="description" content="{escape(DESCRIPTION)}">
<link rel="canonical" href="{escape(base)}/telecharger">
<meta name="robots" content="index,follow">{social_meta(TITLE, DESCRIPTION, base + '/telecharger', site_url)}{HEAD_ASSETS}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>
<body>{site_header()}<main><article><div class="kicker">Application</div>
<h1>Teranga AI dans ta poche</h1>
<p class="intro">Papiers, santé, argent, travail, études, culture, voyage : pose tes questions sur le Sénégal, en français, anglais ou wolof, depuis ton téléphone.</p>
<div class="grid">
<div class="card"><h2>Android (APK)</h2>
<p><a class="cta primary" href="{escape(APK_URL)}" download>Télécharger l'APK</a></p>
<p class="muted">Android 7 ou plus récent, environ 1 Mo. Signé par Google Play : les mises à jour du Play Store s'installent par-dessus.</p></div>
<div class="card"><h2>Google Play</h2>{play}</div>
</div>
{testers}
<section><h2>Installer l'APK en 3 étapes</h2><ol>{steps}</ol></section>
<section><h2>Sur iPhone</h2>
<p>Ouvre <a href="/">teranga-ai.fr</a> dans Safari, appuie sur Partager, puis « Sur l'écran d'accueil ».</p></section>
</article></main>{site_footer()}</body></html>"""


def register_android_routes(app, site_url: str) -> None:
    @app.get("/telecharger")
    def android_download_page():
        return Response(
            render_download_page(site_url, play_store_public()),
            mimetype="text/html",
            headers={"Cache-Control": "public, max-age=3600"},
        )
