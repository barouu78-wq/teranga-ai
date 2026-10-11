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


# Lieux et mots du marché où l'on marchande.
_MARKET_PLACE_TERMS = (
    "au marche", "le marche", "un marche", "les marches", "aux marches", "du marche",
    "market", "markets",
    "sandaga", "kermel", "hlm", "soumbedioune", "tilene", "colobane", "village artisanal",
)
# Gestes de négociation, avec ou sans marché cité.
_MARKET_BARGAIN_TERMS = (
    "negocier", "negocie", "negociation", "marchander", "marchandage", "marchande",
    "trop cher", "bon prix", "juste prix", "prix juste", "faire baisser", "baisser le prix",
    "bargain", "bargaining", "haggle", "haggling",
)
_MARKET_TERMS = _MARKET_PLACE_TERMS + _MARKET_BARGAIN_TERMS
# « souvenirs » seul parle aussi de mémoire (« mes souvenirs d'enfance ») : il ne compte qu'avec un geste d'achat.
_SOUVENIR_TERMS = ("souvenir", "souvenirs")
_SHOPPING_TERMS = (
    "acheter", "achete", "achat", "achats", "rapporter", "rapporte", "ramener", "ramene", "offrir", "cadeau", "cadeaux",
    "prix", "combien", "buy", "bring back", "gift", "gifts", "price", "how much", "cost",
)
# Sens du mot « marché » qui n'est pas le marché où l'on marchande (« le marché du travail »).
_NOT_A_BAZAAR = re.compile(
    r"(?<![\w])(?:(?:le|du|un|au|aux|les|des) )?marches? "
    r"(?:du travail|de l['’ ]emploi|immobilier|financier|boursier|noir|parallele|des changes|des capitaux|"
    r"de l['’ ]art|mondial|international|cible|porteur)(?![\w])|"
    r"(?<![\w])(?:stock|job|labou?r|real estate|housing|financial|black|target) markets?(?![\w])|"
    r"(?<![\w])market (?:research|share|trends?|study|opportunit\w+|analysis|size)(?![\w])"
)
# « Négocier mon loyer » n'est pas une négociation de marché (« prêt » = « pret » sans accent : « prêt à négocier »).
_NOT_MARKET_OBJECTS = (
    "loyer", "bail", "salaire", "contrat", "dette", "credit", "un pret", "mon pret", "le pret", "assurance",
    "proprietaire", "employeur", "patron", "banque", "indemnite", "licenciement", "impot", "impots",
)
# Un vol ou une perte au marché demande l'aide d'urgence, pas une leçon de marchandage.
_INCIDENT_TERMS = ("vole", "volee", "voleur", "voleurs", "vol", "agresse", "agression", "perdu", "pickpocket", "pickpockets")
_PRACTICE_TERMS = (
    "entraine-moi", "entraine moi", "entrainer", "simule", "simulation", "joue le vendeur",
    "fais le vendeur", "jeu de role", "role play", "roleplay", "practice", "pretend",
)
# Le guide sert à découvrir un lieu : ces mots disent « visite touristique ». « quartier » et « coin » seuls n'y
# suffisent pas (« mon quartier n'a plus d'eau »).
_GUIDE_TERMS = (
    "visite guidee", "guide-moi", "guide moi", "sois mon guide", "raconte", "racontes", "histoire de",
    "l'histoire", "histoire du", "que voir", "quoi voir", "a voir",
    "balade", "promenade", "faire le tour", "visiter", "visite", "monument", "patrimoine",
    "tell me about", "history of", "what to see", "guided tour", "walking tour",
)
# Emplois de ces mots qui ne parlent pas d'une visite touristique.
_NOT_A_TOUR = re.compile(
    r"(?<![\w])(?:rendre|rends|rendu|rendons|rendez) visite|"
    r"(?<![\w])visites? (?:medicale|medicales|technique|techniques|de controle|prenatale|prenatales|a domicile|chez|au medecin|du medecin)|"
    r"(?<![\w])visiter (?:un|une|des|mon|ma|mes|notre) (?:appartement|maison|logement|terrain|chambre|studio|villa|local|bureau|immeuble|boutique)|"
    r"(?<![\w])racontes?[- ](?:moi |nous )?(?:une |un |des )?(?:blague|plaisanterie|devinette|journee|vie)s?|"
    r"(?<![\w])patrimoine (?:familial|immobilier|foncier|financier|personnel)|"
    r"(?<![\w])histoire (?:de|du|des|d') ?(?:mon|ma|mes|ton|ta|tes|son|sa|ses|notre|nos|votre|vos|leur|leurs)(?![\w])"
)


_STOP_TERMS = ("stop", "arrete", "fin du jeu", "on arrete", "termine", "end", "quit")


# Pendant un entraînement, une question qui change de sujet (« Quel temps fait-il demain ? ») n'en fait pas partie ;
# une réplique de négociation (un montant, « trop cher », « dernier prix »…) en fait toujours partie.
_QUESTION_START = re.compile(
    r"^(?:quel|quelle|quels|quelles|comment|qui|quand|pourquoi|est ce que|est ce qu|peux tu|pouvez vous|"
    r"ou (?:est|sont|trouver|se trouve|puis je|peut on)|"
    r"where|what|how|when|who|which|why|can you|could you|do you)(?![\w])"
)
_HAGGLING_WORDS = re.compile(
    r"\d|\b(?:prix|cher|chere|baiss\w*|offre|propos\w*|francs?|fcfa|cfa|euros?|accept\w*|achet\w*|prends?|vend\w*|"
    r"rabais|remise|price|offer|cheap|expensive|buy|sell|waaw|deedeet)\b"
)


def _practice_continues(text: str, history) -> bool:
    if _has(text, _STOP_TERMS) or (_QUESTION_START.match(text.strip()) and not _HAGGLING_WORDS.search(text)):
        return False
    recent = [item.get("content", "") for item in (history or [])[-6:] if isinstance(item, dict) and item.get("role") == "user"]
    return any(_has(_normalize(previous), _PRACTICE_TERMS) and _is_market(_normalize(previous)) for previous in recent)


def _is_market(text: str) -> bool:
    """Le message parle-t-il du marché où l'on marchande (et pas du marché du travail, d'un loyer ou d'un vol) ?"""
    text = _NOT_A_BAZAAR.sub(" ", text)
    place = _has(text, _MARKET_PLACE_TERMS) or (_has(text, _SOUVENIR_TERMS) and _has(text, _SHOPPING_TERMS))
    bargain = _has(text, _MARKET_BARGAIN_TERMS)
    if place and not bargain and _has(text, _INCIDENT_TERMS):
        return False
    if bargain and not place and _has(text, _NOT_MARKET_OBJECTS):
        return False
    return place or bargain


def detect_modes(message: object, history=None) -> set[str]:
    text = _normalize(message)
    modes = set()
    # Un entraînement en cours continue aux tours suivants (« je te propose 5000 »)
    # jusqu'à ce que l'utilisateur dise « stop » ou change de sujet.
    if _practice_continues(text, history):
        modes.update({"market", "market_practice"})
    if _is_market(text):
        modes.add("market")
        if _has(text, _PRACTICE_TERMS):
            modes.add("market_practice")
    if _has(_NOT_A_TOUR.sub(" ", text), _GUIDE_TERMS):
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
