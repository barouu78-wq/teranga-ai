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
        if any(keyword in text for keyword in keywords):
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
        "stage_order": list(_STAGE_ORDER),
        "next_action": next_action,
        "steps": steps,
        "principle": "Commencer petit, tester sur le terrain, mesurer, puis investir davantage.",
    }
