"""Repères pratiques vérifiés, ajoutés au contexte quand la question porte sur le sujet.

L'IA répond mieux avec le bon fait sous les yeux qu'en le cherchant dans sa mémoire :
numéros d'urgence, parité de l'euro, prises électriques, heure, visa, cartes SIM…
Seulement des repères durables (vérifiés en octobre 2026) ; les prix et horaires du
jour restent à vérifier par la recherche web.
"""

from __future__ import annotations

import re

from services.text import fold_text

# (identifiant, déclencheurs sur la question sans accents, repères)
TOPICS = (
    ("urgences", r"urgen|police|pompier|samu|ambulance|secours|accident|agress|\bvole\b|\bvolee?s?\b|perdu|danger|"
     r"(pays|endroit|quartier|ville|dakar|senegal) (est il |est elle )?sur\b|est (il|elle|ce) sur\b|securi|\bsafe\b|"
     r"safety|emergenc|fievre|malade|blesse|hopital|hospital|medecin|doctor",
     ("Numéros d'urgence gratuits depuis tous les téléphones, même sans crédit : Police 17, Sapeurs-pompiers 18, "
      "SAMU (urgence médicale) 1515. Gendarmerie : numéro vert 800 00 20 20. SOS Médecins Dakar : 33 889 15 15.",
      "Donner d'abord le lieu exact (quartier, repère, nom de l'hôtel). Page hors connexion : teranga-ai.fr/urgences.",
      "Sécurité : pays globalement calme et accueillant ; attention aux pickpockets dans les foules (marchés, gares "
      "routières) ; pour les zones à éviter, renvoyer aux conseils aux voyageurs officiels (diplomatie.gouv.fr ou "
      "l'équivalent du pays du voyageur).")),
    ("sante", r"vaccin|fievre jaune|paludisme|palu\b|malaria|moustique|pharmac|medicament|eau du robinet|"
     r"boire l eau|tap water|\bsante\b|health|de garde",
     ("Fièvre jaune : vaccin recommandé ; certificat exigé si l'on arrive d'un pays où la maladie circule.",
      "Paludisme : présent dans tout le pays, surtout en saison des pluies ; protection anti-moustiques et avis "
      "d'un médecin avant le départ pour un traitement préventif.",
      "Eau : préférer l'eau en bouteille ou filtrée pour un voyageur.",
      "Pharmacie de garde : liste affichée sur la porte des pharmacies ; demander aussi à l'hôtel. Urgence médicale : "
      "SAMU 1515.")),
    ("argent", r"\beuros?\b|fcfa|\bcfa\b|\bfrancs? cfa\b|\bxof\b|taux de change|\bchange\b|convert|dollars?\b|\bpayer\b|paiement|\bpay\b|payment|\bwave\b|orange money|"
     r"mobile money|distributeur|\batm\b|carte bancaire|bank card|envoyer de l argent|transfert|send money|remit",
     ("Monnaie : franc CFA BCEAO (XOF), à parité fixe avec l'euro : 1 € = 655,957 FCFA (donc 100 € = 65 595,70 FCFA). "
      "Pour le dollar ou la livre, le taux varie : utiliser le taux du jour.",
      "Paiements : Wave et Orange Money (paiement mobile) sont partout, y compris chez les petits commerçants et "
      "certains taxis ; distributeurs nombreux en ville, rares en brousse ; garder des petites coupures.",
      "Envoyer de l'argent vers le Sénégal : services de transfert (Wave, Orange Money, Western Union, Remitly, "
      "Wise…) avec réception sur un compte mobile money ou en espèces ; comparer les frais et le taux appliqué.")),
    ("sim", r"\bsim\b|\besim\b|carte sim|operateur|internet|\bdata\b|forfait|wifi|telephone portable|phone plan",
     ("Opérateurs : Orange, Free et Expresso. Carte SIM en boutique, en kiosque ou à l'aéroport, avec un passeport "
      "(enregistrement obligatoire). Forfaits internet rechargeables par code ou mobile money. Indicatif : +221.",)),
    ("electricite", r"\bprises?\b|electri|voltage|adaptateur|\badapter\b|\bplugs?\b|\bcourant electrique\b",
     ("Électricité : 230 V, 50 Hz ; prises de type C, D, E et K (les prises européennes fonctionnent en général). "
      "Coupures possibles : une batterie externe est utile.",)),
    ("heure", r"\bheures?\b|decalage|fuseau|time zone|timezone|time difference",
     ("Heure : UTC+0 toute l'année, sans changement d'heure. Par rapport à Paris : 1 h de moins en hiver, 2 h de "
      "moins en été.",)),
    ("visa", r"\bvisas?\b|passeport|passport|formalit|entrer au senegal|\bentry\b|douane|customs",
     ("Entrée : les ressortissants de l'Union européenne, du Royaume-Uni, des États-Unis, du Canada et de nombreux "
      "autres pays n'ont en général pas besoin de visa pour un court séjour (moins de 90 jours) ; passeport valide "
      "6 mois conseillé. Toujours faire vérifier auprès de l'ambassade du Sénégal : les règles peuvent changer.",)),
    ("saison", r"saison|quand partir|meilleure periode|meilleur moment|best time|when to go|climat|climate|"
     r"hivernage|pluie|pleut|rainy|\brain\b|chaleur|heat",
     ("Saison sèche environ de novembre à mai (la plus confortable, fraîche le soir sur la côte) ; saison des pluies "
      "environ de juillet à octobre (plus tôt et plus longue en Casamance), pistes parfois difficiles. L'intérieur "
      "(Tambacounda, Kédougou, Matam) est très chaud de mars à juin. Prévisions officielles : ANACIM.",)),
    ("entreprise", r"entreprise|societe|creer (une |mon |ma |son |sa )?(activite|business|startup|boite)|immatricul|"
     r"ninea|rccm|apix|statut juridique|business|startup|\bgie\b|\bsarl\b|suarl",
     ("Créer une activité : entreprise individuelle, GIE (groupement), SARL ou SUARL. L'immatriculation donne un "
      "NINEA (identifiant fiscal) et un RCCM ; le guichet unique de l'APIX centralise les formalités à Dakar. "
      "Accompagnement possible : DER/FJ, FONGIP (garantie), chambres de commerce. Vérifier les conditions actuelles.",)),
    ("transport", r"\btaxis?\b|sept places|7 places|\bter\b|\bbrt\b|\bbus\b|dem dikk|aibd|aeroport|airport|ferry|chaloupe|bateau|"
     r"voiture|location|car rental|transport|se deplacer|get around|aller a|comment aller|how to get",
     ("AIBD (aéroport Blaise Diagne) : à Diass, environ 45 km du centre de Dakar par l'autoroute à péage.",
      "Taxis sans compteur : fixer le prix avant de monter ; applications Yango ou Heetch avec prix affiché.",
      "Dakar : BRT (bus rapide) centre ↔ Guédiawaye ; TER Dakar ↔ Diamniadio (vérifier si le prolongement vers "
      "l'aéroport est en service) ; bus Dakar Dem Dikk.",
      "Entre les villes : sept-places depuis la gare routière des Baux Maraîchers (Pikine), bus, ou voiture avec "
      "chauffeur. Casamance : avion vers Ziguinchor ou Cap Skirring, bateau de nuit Dakar–Ziguinchor (environ 15 h), "
      "ou route par la Gambie (pont de Farafenni).",
      "Gorée : chaloupe depuis la gare maritime de Dakar, environ 20 minutes.")),
    ("foncier", r"terrain|parcelle|titre foncier|acheter (une |un )?(maison|appartement|terrain)|construire (une |ma |sa |notre )?maison|"
     r"immobilier|notaire|cadastre|bail|deliberation|land\b|plot of land|real estate",
     ("Acheter un terrain : le titre foncier (TF) est la forme la plus sûre ; un bail ou une délibération (affectation "
      "d'une terre du domaine national) ne donnent pas la même sécurité. Vérifier le titre et l'absence d'hypothèque "
      "auprès de la Conservation de la propriété foncière (DGID), passer par un notaire, visiter le terrain et le "
      "faire borner par un géomètre.",
      "Diaspora : ne jamais payer un intermédiaire sans documents vérifiés ; méfiance face aux ventes doubles et aux "
      "procurations douteuses ; garder chaque paiement traçable (virement, reçu signé).")),
    ("vente", r"vendre|vente|(trouver|avoir|attirer) (des |plus de )?clients|whatsapp|boutique en ligne|e commerce|commerce en ligne|marge|fixer (mon |le )?prix|"
     r"livraison|sell|customers|online shop",
     ("Vendre sur WhatsApp : compte WhatsApp Business (catalogue, message d'accueil, réponses rapides), photos nettes "
      "avec le prix, statuts quotidiens, liste de diffusion des clients ; paiement par Wave ou Orange Money marchand ; "
      "livraison par un livreur de confiance avec prix annoncé à l'avance.",
      "Fixer un prix : coût d'achat ou de fabrication + emballage + transport + temps passé, puis une marge ; comparer "
      "avec les prix du marché et garder une petite réserve pour les remises.")),
    ("langue", r"quelles? langues?|langue officielle|languages?\b|speak|parle t on|on parle|parle t il",
     ("Langues : le français est la langue officielle ; le wolof est la langue la plus parlée ; on parle aussi pulaar, "
      "sérère, diola, mandingue, soninké… L'anglais est peu répandu hors des lieux touristiques.",)),
)

_COMPILED = tuple((name, re.compile(pattern), facts) for name, pattern, facts in TOPICS)


_fold = fold_text


def matching_topics(question: str, limit: int = 3) -> list[str]:
    folded = _fold(question)
    return [name for name, pattern, _ in _COMPILED if pattern.search(folded)][:limit]


def practical_context(question: str, limit: int = 3) -> str:
    """Bloc « REPÈRES PRATIQUES VÉRIFIÉS » pour la question, ou "" si aucun sujet ne correspond."""
    names = set(matching_topics(question, limit))
    if not names:
        return ""
    lines = ["REPÈRES PRATIQUES VÉRIFIÉS (durables ; prix et horaires du jour à vérifier) :"]
    for name, _, facts in _COMPILED:
        if name in names:
            lines.extend(f"- {fact}" for fact in facts)
    return "\n".join(lines)
