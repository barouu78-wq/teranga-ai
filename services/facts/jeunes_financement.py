"""Repères sur les programmes publics nationaux pour les jeunes : DER/FJ, ANPEJ, 3FPT. Aucun montant, aucune condition d'âge
non sourcée ; chaque dispositif renvoie à l'organisme. Complète services/youth_opportunities.py (liste de liens officiels).

Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les textes ont été relus dans les
extraits renvoyés par le moteur de recherche, d'où les formulations « selon » et « à vérifier ») :
- DER/FJ (Délégation générale à l'Entrepreneuriat rapide des Femmes et des Jeunes) : guichet de financement des femmes et
  des jeunes au Sénégal et dans la diaspora, trois piliers (formalisation, formation, financement) : allafrica.com,
  09/10/2024 (fr.allafrica.com/stories/202410090390.html) ; nano-crédit : financialafrik.com (28/12/2021 et 02/02/2024) ;
  antennes dans les départements annoncées en juillet 2026 : allafrica.com (fr.allafrica.com/stories/202607180003.html) ;
  tournées d'information 2025 sur le nano-crédit et le programme BE YES : lesoleil.sn. Les plafonds du nano-crédit cités
  par la presse diffèrent d'une année à l'autre : aucun montant n'est repris.
- ANPEJ (Agence nationale pour la promotion de l'emploi des jeunes) : accueil, information, orientation, appui à la
  formation et à l'insertion (documents du PNUD, osiris.sn) ; système d'information intégré lancé en 2018 (senego.com) ; page
  officielle anpej.sn déjà citée dans services/youth_opportunities.py. Inscription et offres : non confirmées ici.
- 3FPT (Fonds de financement de la formation professionnelle et technique) : campagne d'enrôlement en ligne du 1er au 5
  octobre 2026 pour 5 000 bons de formation initiale 2026-2027, Sénégalais de 15 à 40 ans, CAP, BEP, BT, BTS, licence et titres
  professionnels, masters exclus, inscription gratuite (communiqué relayé par l'APS : fr.allafrica.com/stories/202609290269.html,
  guindima.sn) ; une prise en charge de 90 % du coût est avancée par certains médias (enqueteplus.com, 02/10/2026,
  lesafriques.com) mais non retrouvée dans le communiqué : signalée comme non confirmée. Appel de 3 000 bons à 100 % (PFPE
  phase 2) du 24 avril au 1er mai 2026, clos (samabac.sn).
Source manquante (donc non ajouté) : conditions d'âge et pièces de la DER/FJ, procédure d'inscription à l'ANPEJ, Service civique
national et programme « Xëyu Ndaw ñi » (programme d'urgence de 2021, jeunesse.gouv.sn : seulement cité, pas détaillé), PRODAC,
FONGIP, ADEPME, stages et concours. À consulter : der.sn, anpej.sn, le site du 3FPT, le ministère de la Jeunesse.
"""

TOPICS = (
    ("jeunes_financement",
     r"\bder ?/? ?fj\b|\bentrepreneuriat rapide\b|\bnano ?credits?\b|\bbe yes\b|"
     r"\banpej\b|\bagence nationale pour la promotion de l emploi des jeunes\b|"
     r"\b3fpt\b|\bfonds de financement de la formation professionnelle\b|\bbons? de formation\b|"
     r"\bfinancements? (pour |des |de |aux )?(les )?(jeunes|femmes entrepreneures?)\b|"
     r"\b(aides?|prets?|credits?|subventions?|financements?) (pour |aux |a |des )?(les )?jeunes "
     r"(entrepreneurs?|porteurs|agriculteurs?|diplomes|createurs)\b|"
     r"\bemploi des jeunes\b|\bchomage des jeunes\b|\binsertion des jeunes\b|"
     r"\bprogrammes? (d |pour les |de l )?(emploi|insertion) (des )?jeunes\b|\bprogrammes? publics? (pour|aux|des) jeunes\b|"
     r"\byouth (employment|funding|financing)\b",
     ("DER/FJ : la Délégation générale à l'Entrepreneuriat rapide des Femmes et des Jeunes est le guichet public de "
      "financement des femmes et des jeunes porteurs de projets, au Sénégal et dans la diaspora, avec trois piliers cités par "
      "la presse : formalisation, formation et financement. Son produit le plus connu est le nano-crédit (petits prêts) ; "
      "les plafonds, les conditions d'âge et les pièces demandées ont varié d'un article à l'autre et ne sont pas "
      "confirmés ici : les vérifier sur der.sn ou à l'antenne la plus proche (la DER/FJ a annoncé en juillet 2026 des "
      "antennes dans les départements). BE YES est un programme d'accompagnement de la DER/FJ présenté lors de ses "
      "tournées d'information de 2025.",
      "ANPEJ : l'Agence nationale pour la promotion de l'emploi des jeunes accueille, informe et oriente les jeunes à la "
      "recherche d'un emploi et appuie la formation et l'insertion ; elle a lancé en 2018 un système d'information "
      "intégré sur l'emploi. Inscription, offres et conditions : non confirmées ici, à vérifier sur anpej.sn ou dans une "
      "agence.",
      "3FPT : le Fonds de financement de la formation professionnelle et technique finance des bons de formation. "
      "Campagne 2026-2027 : l'inscription en ligne pour 5 000 nouveaux bons de formation initiale a eu lieu du 1er au 5 "
      "octobre 2026 (campagne terminée), pour des Sénégalais de 15 à 40 ans, pour des formations de type CAP, BEP, BT, "
      "BTS, licence et titres professionnels (masters exclus), l'inscription étant gratuite d'après le communiqué relayé par "
      "l'APS. Certains médias parlent d'une prise en charge de 90 % du coût de la formation : non confirmé, à vérifier. "
      "La prochaine ouverture, les filières et les conditions se vérifient sur le site du 3FPT et ses annonces officielles.",
      "Prudence : ne verser aucun « frais de dossier » à un intermédiaire ni à un inconnu rencontré sur les réseaux sociaux "
      "pour obtenir un financement, un bon de formation ou un emploi ; passer uniquement par les sites et guichets "
      "officiels de l'organisme et vérifier le dossier directement auprès de lui (voir aussi les repères sur les "
      "arnaques et les faux recrutements).")),
)

SPECIFIC_FIRST = ("jeunes_financement",)
