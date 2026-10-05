"""Modes « guide local » et « négociation au marché » de l'assistant.

Ils ajoutent au contexte de l'IA une consigne de rôle (et, pour le marché,
le savoir-faire de la base de connaissances) quand la question s'y prête.
"""

from __future__ import annotations

import re
import unicodedata


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _has(text: str, terms) -> bool:
    return any(re.search(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text) for term in terms)


_MARKET_TERMS = (
    "negocier", "negocie", "negociation", "marchander", "marchandage", "marchande",
    "au marche", "le marche", "un marche", "les marches", "aux marches", "du marche",
    "trop cher", "bon prix", "juste prix", "prix juste", "faire baisser", "baisser le prix",
    "bargain", "bargaining", "haggle", "haggling", "market", "markets",
    "sandaga", "kermel", "hlm", "soumbedioune", "tilene", "colobane", "village artisanal", "souvenirs",
)
_PRACTICE_TERMS = (
    "entraine-moi", "entraine moi", "entrainer", "simule", "simulation", "joue le vendeur",
    "fais le vendeur", "jeu de role", "role play", "roleplay", "practice", "pretend",
)
_GUIDE_TERMS = (
    "visite guidee", "guide-moi", "guide moi", "sois mon guide", "raconte", "racontes", "histoire de",
    "l'histoire", "histoire du", "que voir", "quoi voir", "a voir", "quartier", "quartiers", "coin", "coins",
    "balade", "promenade", "faire le tour", "visiter", "visite", "monument", "patrimoine",
    "tell me about", "history of", "what to see", "guided tour", "walking tour",
)


_STOP_TERMS = ("stop", "arrete", "fin du jeu", "on arrete", "termine", "end", "quit")


def detect_modes(message: object, history=None) -> set[str]:
    text = _normalize(message)
    modes = set()
    # Un entraînement en cours continue aux tours suivants (« je te propose 5000 »)
    # jusqu'à ce que l'utilisateur dise « stop ».
    recent = [item.get("content", "") for item in (history or [])[-6:] if isinstance(item, dict) and item.get("role") == "user"]
    if not _has(text, _STOP_TERMS) and any(
        _has(_normalize(previous), _PRACTICE_TERMS) and _has(_normalize(previous), _MARKET_TERMS) for previous in recent
    ):
        modes.update({"market", "market_practice"})
    if _has(text, _MARKET_TERMS):
        modes.add("market")
        if _has(text, _PRACTICE_TERMS):
            modes.add("market_practice")
    if _has(text, _GUIDE_TERMS):
        modes.add("guide")
    return modes


def _market_knowledge(knowledge: dict) -> str:
    module = (knowledge.get("knowledge_modules") or {}).get("markets_bargaining") or {}
    lines = []
    if module.get("anchors"):
        lines.append("Marchés de référence : " + ", ".join(module["anchors"]) + ".")
    for item in module.get("stable_knowledge") or []:
        lines.append("- " + item)
    where = module.get("where_to_buy") or []
    if where:
        lines.append("Où acheter : " + " ; ".join(f"{what} → {place}" for what, place in where) + ".")
    for item in module.get("price_method") or []:
        lines.append("- " + item)
    phrases = module.get("phrases_wolof") or []
    if phrases:
        lines.append("Phrases wolof sûres : " + " ; ".join(f"« {w} » = {fr}" for w, fr in phrases) + ".")
    return "\n".join(lines)


def mode_instructions(modes: set[str], knowledge: dict, language: str = "fr") -> str:
    parts = []
    if "guide" in modes:
        parts.append(
            "MODE GUIDE LOCAL : réponds comme un guide sénégalais passionné qui connaît chaque coin. "
            "Raconte l'histoire et une anecdote vraie du lieu (appuie-toi sur les LIEUX PERTINENTS et tes "
            "connaissances sûres), dis ce qu'on voit sur place, propose un petit parcours dans l'ordre, le "
            "meilleur moment pour y aller et un conseil de savoir-vivre. N'invente ni date ni chiffre incertain. "
            "Termine en proposant la suite : photos, carte ou lieu voisin."
        )
    if "market" in modes:
        parts.append(
            "MODE NÉGOCIATION AU MARCHÉ : agis comme un ami sénégalais qui accompagne au marché. Donne où aller "
            "selon l'objet, la méthode pas à pas, 3 à 5 phrases wolof utiles avec leur traduction, et le "
            "savoir-vivre. N'invente jamais de prix précis : au mieux une fourchette prudente notée « à vérifier "
            "sur place ».\n" + _market_knowledge(knowledge)
        )
    if "market_practice" in modes:
        parts.append(
            "ENTRAÎNEMENT : joue le vendeur. Réponses courtes, en français avec quelques mots de wolof ; annonce "
            "un prix d'ouverture élevé, cède petit à petit si l'utilisateur négocie bien, reste chaleureux. "
            "Quand l'accord est trouvé ou si l'utilisateur dit « stop », sors du rôle et fais un bilan avec un conseil."
        )
    if parts and language == "en":
        parts.append("Write the answer in English; keep Wolof phrases with their English meaning.")
    return "\n\n".join(parts)
