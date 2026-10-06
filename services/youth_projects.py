"""Project-building helpers for Senegalese youth.

The service is deterministic: it turns a rough project idea into a small,
actionable brief without calling external services or changing the chat flow.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


PROJECT_CATEGORIES = (
    "business", "agriculture", "digital", "creative", "food",
    "craft", "commerce", "tourism", "environment", "ai",
)

_CATEGORY_KEYWORDS = {
    "agriculture": ("agriculture", "ferme", "élevage", "elevage", "maraîchage", "maraichage", "pêche", "peche"),
    "digital": ("application", "app", "site", "logiciel", "digital", "numérique", "numerique", "freelance"),
    "creative": ("musique", "design", "photo", "vidéo", "video", "mode", "art", "créateur", "createur"),
    "food": ("restaurant", "cuisine", "jus", "pâtisserie", "patisserie", "traiteur", "repas", "aliment"),
    "craft": ("artisan", "couture", "menuiserie", "bijoux", "artisanat", "cuir"),
    "commerce": ("boutique", "vente", "commerce", "revendre", "distributeur", "marché", "marche"),
    "tourism": ("tourisme", "guide", "excursion", "hébergement", "hebergement", "hôtel", "hotel", "voyage"),
    "environment": ("recyclage", "déchet", "dechet", "solaire", "environnement", "reboisement", "énergie", "energie"),
    "ai": ("intelligence artificielle", "ia", "machine learning", "automatisation", "chatbot"),
}

_STAGE_ORDER = ("idea", "validation", "prototype", "first_customers", "revenue")
_STAGE_LABELS = {
    "idea": "Idée",
    "validation": "Validation",
    "prototype": "Prototype",
    "first_customers": "Premiers clients",
    "revenue": "Revenus",
}


def advance_project_stage(project: dict[str, Any], stage: str | None = None) -> dict[str, Any]:
    """Move a saved project to the requested next stage without persistence."""
    current = _normalize(project.get("stage", "idea"))
    if current not in _STAGE_ORDER:
        current = "idea"
    if stage:
        target = _normalize(stage)
        if target not in _STAGE_ORDER:
            target = current
        if _STAGE_ORDER.index(target) > _STAGE_ORDER.index(current) + 1:
            target = _STAGE_ORDER[_STAGE_ORDER.index(current) + 1]
    else:
        index = _STAGE_ORDER.index(current)
        target = _STAGE_ORDER[min(index + 1, len(_STAGE_ORDER) - 1)]
    updated = dict(project)
    updated["stage"] = target
    updated["stage_label"] = _STAGE_LABELS[target]
    updated["stage_index"] = _STAGE_ORDER.index(target)
    if target == "validation":
        updated["next_action"] = "Tester l’idée auprès de 5 personnes et noter leurs objections ou demandes."
    elif target == "prototype":
        updated["next_action"] = "Créer une première version simple et la montrer à de vrais utilisateurs."
    elif target == "first_customers":
        updated["next_action"] = "Contacter des prospects et chercher les premières commandes ou précommandes."
    elif target == "revenue":
        updated["next_action"] = "Mesurer les ventes, la marge et préparer le prochain investissement."
    return updated



PARTNER_DIRECTORY = (
    {"name": "BNDE", "type": "Financement", "categories": ("business", "commerce", "agriculture", "digital"), "city": "Dakar", "description": "Banque dédiée notamment au financement des PME-PMI.", "url": "https://www.bnde.sn/", "contact": "contact@bnde.sn", "phone": "+221 33 829 20 20"},
    {"name": "APIX Sénégal", "type": "Investissement & accompagnement", "categories": ("business", "commerce", "tourism", "agriculture", "digital"), "city": "Dakar", "description": "Orientation des investisseurs et accompagnement des projets d’investissement.", "url": "https://investinsenegal.sn/", "contact": "infos@apix.sn", "phone": "+221 33 849 05 55"},
    {"name": "ADEPME", "type": "Accompagnement PME", "categories": ("business", "commerce", "digital", "food", "craft"), "city": "Dakar", "description": "Conseils et orientation pour les porteurs d’idées et dirigeants de PME.", "url": "https://www.senegalpme.sn/", "contact": "", "phone": "+221 33 869 70 70"},
    {"name": "ASEPEX", "type": "Export & marchés", "categories": ("commerce", "agriculture", "food", "craft", "tourism"), "city": "Dakar", "description": "Appui à la promotion et au développement des exportations sénégalaises.", "url": "https://www.senegalexport.com/", "contact": "asepex@asepex.sn", "phone": "+221 33 869 20 21"},
    {"name": "CCIAD", "type": "Réseau entreprises", "categories": ("business", "commerce", "food", "craft"), "city": "Dakar", "description": "Chambre de commerce, d’industrie et d’agriculture de Dakar.", "url": "https://www.cciad.sn/", "contact": "", "phone": "+221 33 823 71 89"},
    {"name": "Orange Sénégal / Sonatel", "type": "Digital & partenariat", "categories": ("digital", "ai", "commerce", "business"), "city": "Dakar", "description": "Acteur télécom et numérique disposant de services aux entreprises et de dispositifs de partenariat.", "url": "https://www.orange.sn/", "contact": "serviceclient@orange-sonatel.com", "phone": "1441"},
    {"name": "Compagnie Sucrière Sénégalaise", "type": "Agroalimentaire", "categories": ("agriculture", "food", "commerce"), "city": "Richard-Toll", "description": "Entreprise agro-industrielle avec contact public pour les demandes de partenariat.", "url": "https://www.css.sn/contact/", "contact": "", "phone": "+221 33 938 23 23"},
)

def find_project_partners(category: str = "", city: str = "") -> list[dict[str, Any]]:
    wanted_category = _normalize(category)
    wanted_city = _normalize(city)
    partners = []
    for partner in PARTNER_DIRECTORY:
        category_match = not wanted_category or wanted_category in partner["categories"]
        city_match = not wanted_city or wanted_city in _normalize(partner["city"]) or partner["city"] == "Dakar"
        if category_match and city_match:
            partners.append(dict(partner))
    return partners


def build_project_matches(project: dict[str, Any]) -> dict[str, Any]:
    """Create deterministic next-step matches from a saved project brief."""
    category = _normalize(project.get("category", "business"))
    city = str(project.get("city", "")).strip()
    partners = find_project_partners(category, city)
    from services.youth_opportunities import find_youth_opportunities

    opportunities = find_youth_opportunities(category, city)
    return {
        "category": category,
        "city": city,
        "partners": partners[:5],
        "opportunities": opportunities[:5],
        "counts": {
            "partners": len(partners),
            "opportunities": len(opportunities),
        },
        "next_action": (
            "Choisir une opportunité à vérifier puis préparer les pièces demandées."
            if opportunities
            else "Vérifier les partenaires locaux puis rechercher une opportunité adaptée."
        ),
    }

def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _money_amount(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value >= 0 else None
    text = _normalize(value)
    match = re.search(r"(?<!\d)(\d[\d\s.,]*)(?:\s*(?:fcfa|f cfa|cfa))?", text)
    if not match:
        return None
    raw = re.sub(r"[\s.,]", "", match.group(1))
    try:
        amount = int(raw)
    except ValueError:
        return None
    return amount if amount >= 0 else None


def detect_project_category(idea: str, category: str | None = None) -> str:
    requested = _normalize(category)
    if requested in PROJECT_CATEGORIES:
        return requested
    text = _normalize(idea)
    for name, keywords in _CATEGORY_KEYWORDS.items():
        # Mot entier (pluriel simple accepté) : « art » ne doit pas trouver « artisan ».
        if any(re.search(r"(?<!\w)" + re.escape(_normalize(k)) + r"(?:s|x)?(?!\w)", text) for k in keywords):
            return name
    return "business"


def build_project_brief(
    *,
    idea: str,
    city: str = "",
    budget_fcfa: int | str | None = None,
    skills: str = "",
    available_time: str = "",
    goal_fcfa: int | str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Build a practical 0-to-1 project brief from minimal youth inputs."""
    clean_idea = str(idea or "").strip()
    clean_city = str(city or "").strip()
    clean_skills = str(skills or "").strip()
    clean_time = str(available_time or "").strip()
    budget = _money_amount(budget_fcfa)
    goal = _money_amount(goal_fcfa)
    project_category = detect_project_category(clean_idea, category)

    steps = [
        {"id": "validate", "title": "Valider le besoin", "action": "Parler à 5 personnes qui pourraient devenir clientes et noter leur problème principal."},
        {"id": "offer", "title": "Construire une offre simple", "action": "Définir une offre test, son prix en FCFA et ce qui la rend utile localement."},
        {"id": "prototype", "title": "Créer une première version", "action": "Produire une version minimale que l’on peut montrer ou vendre sans attendre un produit parfait."},
        {"id": "test", "title": "Obtenir les premiers retours", "action": "Faire tester l’offre à quelques personnes et corriger selon leurs retours."},
        {"id": "sell", "title": "Chercher les premiers clients", "action": "Contacter directement des prospects et mesurer les demandes, ventes ou précommandes."},
    ]
    if clean_city:
        steps[0]["action"] += f" Commencer à {clean_city}."
    if clean_skills:
        steps[2]["action"] += f" S’appuyer d’abord sur la compétence : {clean_skills}."
    if clean_time:
        steps[4]["action"] += f" Organiser les actions autour du temps disponible : {clean_time}."

    next_action = steps[0]["action"]
    if budget is not None and budget > 0:
        next_action += f" Budget de départ déclaré : {budget:,} FCFA.".replace(",", " ")
    return {
        "name": clean_idea[:120],
        "category": project_category,
        "city": clean_city[:80],
        "budget_fcfa": budget,
        "skills": clean_skills[:200],
        "available_time": clean_time[:100],
        "goal_fcfa": goal,
        "stage": "idea",
        "stage_label": _STAGE_LABELS["idea"],
        "stage_index": 0,
        "stage_order": list(_STAGE_ORDER),
        "next_action": next_action,
        "steps": steps,
        "tracking": {
            "objective": f"Atteindre {goal:,} FCFA." if goal is not None else "Définir un objectif mesurable pour les 30 prochains jours.",
            "period": "30 jours",
            "indicators": ["Clients contactés", "Ventes réalisées", "Chiffre d’affaires (FCFA)", "Dépenses (FCFA)", "Bénéfice estimé (FCFA)"],
            "weekly_checklist": ["Ce que j’ai fait", "Ce qui a marché", "Ce qui bloque", "Action prioritaire de la semaine suivante"],
            "next_review": "Faire un point chaque fin de semaine et ajuster le plan.",
        },
        "principle": "Commencer petit, tester sur le terrain, mesurer, puis investir davantage.",
    }
