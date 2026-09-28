"""Photo query helpers that keep precise Senegal place searches precise."""
from __future__ import annotations
import re
import unicodedata

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

def normalize_place_query(query: str) -> str:
    value = re.sub(r"\s+", " ", str(query or "").strip())
    low = _normalize(value)
    for key, aliases in PLACE_ALIASES.items():
        if _normalize(key) in low or any(_normalize(alias) in low for alias in aliases):
            return " ".join(aliases[:3])
    return value + " Sénégal" if "senegal" not in low else value

def relevant_image_evidence(query: str, title: str, description: str = "") -> bool:
    low = _normalize(query)
    evidence = _normalize(f"{title} {description}")
    for key, aliases in PLACE_ALIASES.items():
        if _normalize(key) in low:
            specific_aliases = tuple(alias for alias in aliases if _normalize(alias) not in {"senegal", "sénégal"})
            return any(_normalize(alias) in evidence for alias in specific_aliases)
    return True
