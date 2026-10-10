"""Repères généraux sur l'agriculture : campagne agricole 2026/2027, distribution des intrants, alerte de l'ANACIM.

Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les textes ont été relus dans les
extraits renvoyés par le moteur de recherche, d'où les formulations « selon » et « à vérifier ») :
- Réunion interministérielle du 30 juin 2026 sur la campagne de production agricole 2026/2027 (34 mesures pour sécuriser
  l'hivernage ; commissions de distribution des semences et engrais supervisées par le ministre de l'Agriculture avec le
  ministre de l'Intérieur ; au moins 30 % des semences et engrais pour les femmes et les jeunes) :
  primature.sn/publications/actualites/reunion-interministerielle-sur-le-deroulement-de-la-campagne-de-production,
  vie-publique.sn/actualites/416/reunion-interministerielle-sur-la-campagne-de-production-agricole-2026-2027-senegal,
  seneplus.com (« le gouvernement arrête 34 mesures pour sécuriser l'hivernage »).
- ANACIM, hivernage 2026 : démarrage « normal à tardif » avec risque de « faux départs agricoles » (senego.com, mai 2026 ;
  ndarinfo.com, « l'Anacim prévoit un démarrage tardif et déficitaire », mise à jour n° 2 des prévisions).
- DER/FJ et projets agricoles : financialafrik.com, 28/12/2021 (nano-crédit et projets agricoles à Kaffrine).
Source manquante (donc non ajouté) : calendrier cultural de chaque culture, prix au producteur de l'arachide et
campagne de commercialisation, crédit agricole, assurance agricole, taux de subvention des intrants, adresses des services
agricoles locaux, accès à la terre (voir le sujet « foncier »), élevage. À consulter : le ministère de l'Agriculture, l'ISRA,
l'ANACIM (anacim.sn).
"""

TOPICS = (
    ("agriculture",
     r"\bagricult\w+|\bagricoles?\b|\bmaraich\w+|\bpaysans?\b|\bsemences?\b|\bengrais\b|\bsemis\b|\bisra\b|"
     r"\bcultures? (de |du |des |d |de l )?(arachide|mil|mais|riz|niebe|sorgho|oignons?|tomates?)\b|"
     r"\bcultiver (du |le |la |les |des |de l |l )?(mil|arachide|mais|riz|niebe|sorgho|oignons?)\b|"
     r"\bfarming\b|\bagricultural\b|\bfertili[sz]ers?\b",
     ("Campagne agricole 2026/2027 : une réunion interministérielle du 30 juin 2026, présidée par le Premier ministre, a "
      "arrêté 34 mesures pour sécuriser l'hivernage (financement de la campagne, acheminement des semences vers les "
      "producteurs avant l'installation définitive des pluies…). La distribution des semences et des engrais passe par "
      "des commissions de distribution supervisées par le ministre de l'Agriculture avec le ministre de l'Intérieur, avec "
      "l'objectif qu'au moins 30 % des semences et engrais aillent aux femmes et aux jeunes. Quantités, prix, conditions "
      "et lieux de distribution ne sont pas confirmés ici : à demander aux services agricoles locaux ou à la mairie.",
      "Pluies : en 2026, l'ANACIM avait annoncé un démarrage de l'hivernage « normal à tardif » selon les zones et alerté sur "
      "le risque de « faux départs agricoles » (semis trop précoces, suivis de longues pauses sans pluie). Avant de semer, "
      "consulter ses prévisions saisonnières et leurs mises à jour, ainsi que les conseils des services agricoles ; le "
      "début de la saison varie d'une zone à l'autre et d'une année à l'autre.",
      "Financement : la DER/FJ (jeunes et femmes) a financé des projets agricoles, par exemple à Kaffrine en 2021 selon la "
      "presse économique ; conditions et montants à vérifier auprès d'elle (voir les repères sur le financement des "
      "jeunes). Autres informations (prix au producteur, crédit, assurance, calendrier de chaque culture) : non "
      "confirmées ici, à demander au ministère de l'Agriculture ou à l'ISRA.")),
)

SPECIFIC_FIRST = ("agriculture",)
