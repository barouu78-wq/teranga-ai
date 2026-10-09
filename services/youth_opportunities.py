"""Curated youth opportunity radar backed by official Senegalese program sources.

The list intentionally avoids volatile deadlines. Each entry points to an official
source where the current eligibility, dates and application status can be checked.
"""

OPPORTUNITIES = (
    {
        "title": "Financement DER/FJ",
        "organization": "DER/FJ",
        "type": "financement",
        "categories": ("business", "agriculture", "craft", "commerce", "digital", "food"),
        "audience": "Jeunes entrepreneurs et porteurs de projets",
        "location": "Sénégal",
        "status": "service",
        "description": "Guichets de financement et accompagnement pour démarrer ou développer une activité.",
        "url": "https://www.der.sn/devenez-entrepreneur/",
        "source": "DER/FJ",
    },
    {
        "title": "BE YES",
        "organization": "DER/FJ",
        "type": "accompagnement",
        "categories": ("business", "agriculture", "craft", "digital", "commerce"),
        "audience": "Jeunes de 15 à 35 ans, notamment jeunes en formation professionnelle",
        "location": "14 régions du Sénégal",
        "status": "programme",
        "description": "Programme d'accompagnement autour du business plan, mentorat, innovation, accès au marché et financement.",
        "url": "https://www.der.sn/nos-programmes/be-yes/",
        "source": "DER/FJ",
    },
    {
        "title": "Services ANPEJ",
        "organization": "ANPEJ",
        "type": "emploi_formation",
        "categories": ("business", "digital", "creative", "commerce", "tourism", "food"),
        "audience": "Jeunes demandeurs d'emploi et porteurs de projets",
        "location": "Sénégal",
        "status": "service",
        "description": "Orientation, formation, coaching, intermédiation, appui à la création d'entreprise et suivi des projets.",
        "url": "https://anpej.sn/accueil/",
        "source": "ANPEJ",
    },
    {
        "title": "Espoir Jeunes",
        "organization": "3FPT / ISEP",
        "type": "formation",
        "categories": ("digital", "creative", "agriculture", "craft", "tourism", "environment"),
        "audience": "Jeunes recherchant une formation professionnelle courte",
        "location": "Sénégal",
        "status": "programme",
        "description": "Dispositif de bons de formation pour des attestations et certificats de compétences professionnelles.",
        "url": "https://espoirjeunes.3fpt.sn/",
        "source": "Espoir Jeunes / 3FPT",
    },
)


def find_youth_opportunities(category="", city=""):
    wanted = str(category or "").strip().lower()
    city_text = str(city or "").strip().lower()
    results = []
    for item in OPPORTUNITIES:
        category_match = not wanted or wanted in item["categories"]
        location = item["location"].lower()
        # « Sénégal » ou « 14 régions du Sénégal » : programme national, valable pour toute ville.
        city_match = not city_text or city_text in location or location.endswith("sénégal")
        if category_match and city_match:
            results.append(dict(item))
    return results
