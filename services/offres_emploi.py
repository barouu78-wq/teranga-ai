"""Offres d'emploi (/offres-emploi) : des liens vers les sites sénégalais d'offres, rien de recopié.

Décision du propriétaire du 22 novembre 2026 : « on met juste leur lien », l'offre s'ouvre sur le site qui la publie.
Chaque site a été ouvert à la main le jour noté dans `verifie_le` (offres récentes, rien de payant vu pour postuler).
Écartés le 22 novembre 2026 : Go Africa Online (403 aux robots) et Option Carrière (vérification anti-robot) : non
vérifiables, donc absents. Un site qui demande à ne plus figurer ici est retiré sans discussion (skill offres-emploi).
"""

from __future__ import annotations

import json
from html import escape

from services.site_layout import HEAD_ASSETS, site_footer, site_header, social_meta

SITES_EMPLOI = (
    {
        "nom": "Emploi Dakar", "domaine": "emploidakar.com",
        # Page d'accueil seulement : leurs conditions d'utilisation interdisent les liens profonds.
        "url": "https://www.emploidakar.com/",
        "description": "Offres d’emploi et de stages à Dakar et dans tout le Sénégal. Le site dit que postuler y est gratuit.",
        "verifie_le": "2026-11-22",
    },
    {
        "nom": "Senjob", "domaine": "senjob.com",
        "url": "https://www.senjob.com/sn/offres-d-emploi.php",
        "description": "Offres d’emploi et de stages, surtout à Dakar. Le site publie aussi pour d’autres pays d’Afrique de "
                       "l’Ouest : regarde la ville de l’offre.",
        "verifie_le": "2026-11-22",
    },
    {
        "nom": "Concoursn", "domaine": "concoursn.com",
        "url": "https://concoursn.com/",
        "description": "Concours, bourses, offres d’emploi et de stages, au Sénégal et ailleurs en Afrique : regarde le pays "
                       "de l’offre.",
        "verifie_le": "2026-11-22",
    },
    {
        "nom": "Guichet unique de l’ANPEJ", "domaine": "emploijeunes.sn", "public": True,
        "url": "https://emploijeunes.sn/",
        # Le 22 novembre 2026, sa page d'offres affichait « Aucune offre d'emploi en cours » : présenté comme service.
        "description": "Service public de l’Agence nationale pour la promotion de l’emploi des jeunes : inscription comme "
                       "demandeur d’emploi, orientation et formation.",
        "verifie_le": "2026-11-22",
    },
)

TITRE = "Offres d’emploi au Sénégal : où les trouver · Teranga AI"
DESCRIPTION = ("Les sites où trouver des offres d’emploi et de stages au Sénégal, vérifiés par Teranga. Prépare ton CV "
               "gratuit, puis postule directement sur leur site.")


def _carte(site: dict) -> str:
    etiquette = '<span class="emploi-public">Service public</span>' if site.get("public") else ""
    bouton = "Ouvrir le site" if site.get("public") else "Voir les offres"
    return (f'<li class="emploi-site"><h2>{escape(site["nom"])}{etiquette}</h2>'
            f'<p>{escape(site["description"])}</p>'
            f'<a class="cta" href="{escape(site["url"])}" target="_blank" rel="noopener noreferrer">{bouton}'
            f'<span class="emploi-domaine"> sur {escape(site["domaine"])}</span></a></li>')


def page_offres_emploi(site_url: str) -> str:
    url = site_url.rstrip("/") + "/offres-emploi"
    donnees = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage", "name": "Offres d’emploi au Sénégal", "url": url,
        "description": DESCRIPTION, "inLanguage": "fr",
    }, ensure_ascii=False).replace("</", "<\\/")
    cartes = "".join(_carte(s) for s in SITES_EMPLOI)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(TITRE)}</title>
<meta name="description" content="{escape(DESCRIPTION)}">
<link rel="canonical" href="{escape(url)}">
{social_meta(TITRE, DESCRIPTION, url, site_url)}
<script type="application/ld+json">{donnees}</script>
{HEAD_ASSETS}</head><body class="emploi-page">
{site_header("/offres-emploi")}
<main class="emploi-main">
<h1>Offres d’emploi au Sénégal</h1>
<p class="emploi-intro">Les offres sont publiées sur ces sites&nbsp;: le bouton ouvre leur page et tu postules chez eux.
Ces sites ne sont pas partenaires de Teranga.</p>
<div class="emploi-cv"><p><strong>Ton CV d’abord.</strong> Un CV clair, prêt en PDF, fait gratuitement sur Teranga.</p>
<a class="cta primary" href="/cv">Faire mon CV gratuit</a></div>
<ul class="emploi-sites">{cartes}</ul>
<div class="emploi-alerte" role="note"><p><strong>Ne paie jamais pour obtenir un emploi.</strong> Une vraie offre ne demande
ni frais de dossier, ni formation payante obligatoire, ni argent pour un visa. Vérifie l’entreprise (site, adresse,
numéro) avant d’envoyer tes pièces d’identité.</p></div>
<p class="emploi-note">Liens vérifiés le 22 novembre 2026.
Un site qui ne souhaite plus figurer ici est retiré sur simple demande.</p>
</main>
{site_footer("fr")}
</body></html>"""
