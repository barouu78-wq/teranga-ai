"""Map lookup helpers for Teranga AI."""

from urllib.parse import quote


MAP_PLACES = (
    ("aibd", "Aéroport Blaise Diagne Diass Sénégal", "Aéroport AIBD"),
    ("aéroport", "Aéroport Blaise Diagne Diass Sénégal", "Aéroport AIBD"),
    ("maison des esclaves", "Maison des Esclaves Gorée Sénégal", "Maison des Esclaves"),
    ("île de gorée", "Île de Gorée Sénégal", "Île de Gorée"),
    ("ile de goree", "Île de Gorée Sénégal", "Île de Gorée"),
    ("gorée", "Île de Gorée Sénégal", "Île de Gorée"),
    ("goree", "Île de Gorée Sénégal", "Île de Gorée"),
    ("lac rose", "Lac Retba Sénégal", "Lac Rose"),
    ("lac retba", "Lac Retba Sénégal", "Lac Rose"),
    ("cap skirring", "Cap Skirring Sénégal", "Cap Skirring"),
    ("saint-louis", "Saint-Louis Sénégal", "Saint-Louis"),
    ("saint louis", "Saint-Louis Sénégal", "Saint-Louis"),
    ("monument de la renaissance", "Monument de la Renaissance africaine Dakar", "Monument de la Renaissance"),
    ("joal", "Joal-Fadiouth Sénégal", "Joal-Fadiouth"),
    ("fadiouth", "Joal-Fadiouth Sénégal", "Joal-Fadiouth"),
    ("touba", "Grande Mosquée de Touba Sénégal", "Touba"),
    ("ziguinchor", "Ziguinchor Sénégal", "Ziguinchor"),
    ("saly", "Saly Portudal Sénégal", "Saly"),
    ("thiès", "Thiès Sénégal", "Thiès"),
    ("thies", "Thiès Sénégal", "Thiès"),
    ("kaolack", "Kaolack Sénégal", "Kaolack"),
    ("mbour", "M'Bour Sénégal", "M'Bour"),
    ("somone", "Somone Sénégal", "Somone"),
    ("popenguine", "Popenguine Sénégal", "Popenguine"),
    ("toubab dialaw", "Toubab Dialaw Sénégal", "Toubab Dialaw"),
    ("fatick", "Fatick Sénégal", "Fatick"),
    ("louga", "Louga Sénégal", "Louga"),
    ("matam", "Matam Sénégal", "Matam"),
    ("tambacounda", "Tambacounda Sénégal", "Tambacounda"),
    ("kédougou", "Kédougou Sénégal", "Kédougou"),
    ("kedougou", "Kédougou Sénégal", "Kédougou"),
    ("kolda", "Kolda Sénégal", "Kolda"),
    ("sédhiou", "Sédhiou Sénégal", "Sédhiou"),
    ("sedhiou", "Sédhiou Sénégal", "Sédhiou"),
    ("diamniadio", "Diamniadio Sénégal", "Diamniadio"),
    ("pointe sarène", "Pointe Sarène Sénégal", "Pointe Sarène"),
    ("pointe sarene", "Pointe Sarène Sénégal", "Pointe Sarène"),
    ("dakar", "Dakar Sénégal", "Dakar"),
)


def lookup_map(message):
    lowered = str(message or "").lower()
    for key, query, label in MAP_PLACES:
        if key in lowered:
            encoded_query = quote(query)
            return {
                "label": label,
                "url": "https://www.google.com/maps/search/?api=1&query=" + encoded_query,
                "embed": "https://maps.google.com/maps?q=" + encoded_query + "&hl=fr&z=14&output=embed",
            }
    return None
