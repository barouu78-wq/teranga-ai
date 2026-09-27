"""Photo query helpers that keep precise Senegal place searches precise."""
from __future__ import annotations
import re

PLACE_ALIASES = {
    "goree": ("Gorée", "Île de Gorée", "Goree Island", "Dakar"),
    "lac rose": ("Lac Rose", "Lac Retba", "Lake Retba", "Sénégal"),
    "saint-louis": ("Saint-Louis", "Saint Louis", "Sénégal"),
    "joal-fadiouth": ("Joal-Fadiouth", "Fadiouth", "Joal", "Sénégal"),
    "cap skirring": ("Cap Skirring", "Casamance", "Sénégal"),
    "toubab dialaw": ("Toubab Dialaw", "Sénégal"),
    "saloum": ("Sine-Saloum", "Saloum", "Sénégal"),
    "niokolo-koba": ("Niokolo-Koba", "Sénégal"),
    "djoudj": ("Djoudj", "Parc national des oiseaux du Djoudj", "Sénégal"),
}

def normalize_place_query(query: str) -> str:
    value = re.sub(r"\s+", " ", str(query or "").strip())
    low = value.lower().replace("ô", "o")
    for key, aliases in PLACE_ALIASES.items():
        if key in low or any(alias.lower() in low for alias in aliases):
            return " ".join(aliases[:3])
    return value + " Sénégal" if "senegal" not in low and "sénégal" not in low else value

def relevant_image_evidence(query: str, title: str, description: str = "") -> bool:
    low = query.lower()
    evidence = f"{title} {description}".lower()
    for key, aliases in PLACE_ALIASES.items():
        if key in low:
            return any(alias.lower() in evidence for alias in aliases)
    return True
