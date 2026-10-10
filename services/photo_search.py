"""Photo query helpers that keep precise Senegal place searches precise."""
from __future__ import annotations
import re
import unicodedata
from functools import lru_cache

PLACE_ALIASES = {
    "dakar": ("Dakar", "Sénégal"), "diourbel": ("Diourbel", "Sénégal"),
    "fatick": ("Fatick", "Sénégal"), "kaffrine": ("Kaffrine", "Sénégal"),
    "kaolack": ("Kaolack", "Sénégal"), "kedougou": ("Kédougou", "Sénégal"),
    "kolda": ("Kolda", "Sénégal"), "louga": ("Louga", "Sénégal"), "matam": ("Matam", "Sénégal"),
    "sedhiou": ("Sédhiou", "Sénégal"), "tambacounda": ("Tambacounda", "Sénégal"),
    "thies": ("Thiès", "Sénégal"), "ziguinchor": ("Ziguinchor", "Casamance", "Sénégal"),
    "delta du saloum": ("Delta du Saloum", "Sine-Saloum", "Sénégal"),
    "pays bassari": ("Pays Bassari", "Bassari", "Kédougou"),
    "dindefelo": ("Dindéfelo", "Dindéfello", "Kédougou"), "rufisque": ("Rufisque", "Vieux Rufisque", "Sénégal"),
    "carabane": ("Carabane", "Casamance", "Sénégal"), "popenguine": ("Popenguine", "Sénégal"),
    "saly": ("Saly", "Saly Portudal", "Sénégal"), "tivaouane": ("Tivaouane", "Sénégal"),
    "touba": ("Touba", "Grande Mosquée de Touba", "Sénégal"),
    "goree": ("Gorée", "Île de Gorée", "Goree Island"),
    "lac rose": ("Lac Rose", "Lac Retba", "Lake Retba", "Sénégal"),
    "saint-louis": ("Saint-Louis", "Saint Louis", "Sénégal"),
    "joal-fadiouth": ("Joal-Fadiouth", "Fadiouth", "Joal", "Sénégal"),
    "cap skirring": ("Cap Skirring", "Casamance", "Sénégal"),
    "toubab dialaw": ("Toubab Dialaw", "Sénégal"),
    "saloum": ("Delta du Saloum", "Sine-Saloum", "Saloum"),
    "niokolo-koba": ("Niokolo-Koba", "Sénégal"),
    "djoudj": ("Djoudj", "Parc national des oiseaux du Djoudj", "Sénégal"),
}

def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


@lru_cache(maxsize=1024)
def _fold(value: str) -> str:
    text = re.sub(r"[-‐‑‒–—]+", " ", _normalize(value))
    text = re.sub(r"(?<!\w)ste(?!\w)\.?", "sainte", text)
    text = re.sub(r"(?<!\w)st(?!\w)\.?", "saint", text)
    return re.sub(r"\s+", " ", text).strip()


def fold_place_text(value: object) -> str:
    """Texte comparable pour reconnaître un lieu, quelle que soit sa graphie.

    Sans accents ni majuscules ; tirets et espaces se valent (« Joal-Fadiouth » =
    « Joal Fadiouth ») ; « St » et « Ste » valent « Saint » et « Sainte »
    (« St Louis » = « Saint-Louis »).
    """
    return _fold(str(value or ""))


def term_position(text: object, term: object) -> int | None:
    """Position (dans le texte comparable) du terme entier cité, ou None s'il est absent.

    Les deux côtés passent par `fold_place_text` : « Goree », « Gorée » et « GORÉE »
    sont le même lieu, comme « St Louis » et « Saint-Louis ».
    """
    wanted = fold_place_text(term)
    if not wanted:
        return None
    found = re.search(r"(?<!\w)" + re.escape(wanted) + r"(?!\w)", fold_place_text(text))
    return found.start() if found else None

# Mots qui n'apportent aucune précision sur le lieu cherché.
_GENERIC_WORDS = {
    "photo", "photos", "image", "images", "picture", "pictures", "de", "du", "des", "d", "la", "le",
    "les", "l", "a", "au", "aux", "en", "et", "of", "the", "in", "senegal", "voir", "montre", "moi",
}


def _has_term(text: str, term: str) -> bool:
    """Terme entier : « touba » ne doit pas trouver « toubab » ni « toubacouta »."""
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None


def _match_place(low: str):
    """Lieu le plus précis cité (clé ou alias le plus long), avec le texte trouvé."""
    best = None
    for key, aliases in PLACE_ALIASES.items():
        for term in (key, *aliases):
            norm = _normalize(term)
            if norm in {"senegal"} or not _has_term(low, norm):
                continue
            if best is None or len(norm) > len(best[2]):
                best = (key, aliases, norm)
    return best


def _extra_words(low: str, match) -> list[str]:
    """Mots de la recherche qui ne viennent ni du lieu (ou de ses alias) ni du vocabulaire courant."""
    known = set(_GENERIC_WORDS)
    for term in (match[0], *match[1]):
        known.update(re.findall(r"[a-z0-9]+", _normalize(term)))
    return [w for w in re.findall(r"[a-z0-9]+", low) if w not in known and len(w) > 1]


def normalize_place_query(query: str) -> str:
    value = re.sub(r"\s+", " ", str(query or "").strip())
    low = _normalize(value)
    match = _match_place(low)
    # « Île de Ngor Dakar » ou « mangrove Toubacouta » sont déjà précis : on ne les
    # remplace pas par la ville entière.
    if match and not _extra_words(low, match):
        return " ".join(match[1][:3])
    return value + " Sénégal" if "senegal" not in low else value


def relevant_image_evidence(query: str, title: str, description: str = "") -> bool:
    low = _normalize(query)
    match = _match_place(low)
    if not match or _extra_words(low, match):
        return True
    evidence = _normalize(f"{title} {description}")
    specific_aliases = tuple(alias for alias in match[1] if _normalize(alias) != "senegal")
    return any(_has_term(evidence, _normalize(alias)) for alias in specific_aliases)
