"""Repères généraux sur la pêche artisanale : cadre légal, permis, immatriculation, cogestion, repos biologique.

Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les textes ont été relus dans les
extraits renvoyés par le moteur de recherche, d'où les formulations « selon » et « à vérifier ») :
- Code de la pêche maritime, loi n° 2015-18 du 13 juillet 2015 (texte sur vie-publique.sn, notice FAOLEX) : permis de
  pêche artisanale commerciale, à pied ou en embarcation, qui remplace la déclaration préalable ; immatriculation de
  toutes les embarcations opérant dans les eaux sous juridiction sénégalaise, y compris celles d'étrangers établis
  régulièrement.
- Permis de pêche artisanale en trois catégories (A pêche à pied, B pirogues de 0 à 13 m, C pirogues de plus de 13 m),
  valable une année civile, subordonné à l'immatriculation de la pirogue, à des équipements de sécurité minimum et à des
  engins conformes : arrêté ministériel de 2015 (n° 5308, qui remplace celui de 2005) et texte antérieur sur FAOLEX
  (faolex.fao.org, notices SEN155157 et SEN155026) ; la Primature (primature.sn, rubrique pêche) fait état de permis
  délivrés et de pirogues enregistrées. Les redevances relevées dans une étude universitaire ancienne sont dépassées et
  ne sont pas reprises.
- Conseils locaux de pêche artisanale (CLPA) institutionnalisés comme organes de cogestion locale, permis instauré pour
  mettre fin au libre accès à la ressource : FAO, document CA2335FR (fao.org/3/CA2335FR/ca2335fr.pdf).
- Immatriculation non finalisée : rapport relayé par ndarinfo.com (« Un rapport recommande la finalisation des
  procédures d'immatriculation des pirogues ») ; arrêté de gel de 2012 (n° 006397) : situation actuelle non confirmée.
- Repos biologique : ANSD, Situation économique et sociale 2012 (un mois pour le poulpe en pêche artisanale, vie-publique.sn) ;
  ndarinfo.com (repos biologique du poulpe, plusieurs années non précisées) ; arrêté n° 7441 du 10 novembre 2003 (leap.unep.org).
Source manquante (donc non ajouté) : montant des redevances, pièces à fournir et guichet de délivrance du permis,
dates du repos biologique en vigueur, règles de sécurité en mer, commercialisation (mareyage), pêche continentale.
À consulter : la Direction des pêches maritimes (DPM), le Journal officiel.
"""

TOPICS = (
    ("peche_artisanale",
     r"\bpeche artisanale\b|\bpermis de peche\b(?! sportive| de loisir| touristique| recreative)|"
     r"\bpermis (a|b|c) de peche\b|\blicences? de peche\b(?! sportive| de loisir| touristique)|"
     r"\bcode de la peche\b|\brepos biologique\b|\bclpa\b|\bconseils? locaux? de peche\b|\bmareyeu\w+|\bmareyage\b|"
     r"\bimmatricul\w* (d |de |des |les |la |une |ma |mes )?pirogues?\b|\bpirogues? (de peche|artisanale|immatricul\w+)\b|"
     r"\bdevenir pecheur\b|\bmetier de pecheur\b|\bvivre de la peche\b|\bdirection des peches\b|"
     r"\bsmall scale fishing\b|\bartisanal fishing\b",
     ("Cadre : la pêche artisanale est régie par le Code de la pêche maritime (loi n° 2015-18 du 13 juillet 2015), qui a "
      "institué un permis de pêche artisanale commerciale (à pied ou en embarcation) en remplacement de la simple "
      "déclaration préalable, pour mettre fin au libre accès à la ressource (FAO).",
      "Permis : trois catégories selon les textes consultés : A pour la pêche à pied, B pour les pirogues de 0 à 13 mètres, "
      "C pour les pirogues de plus de 13 mètres. Le permis est valable une année civile et se renouvelle chaque année ; il "
      "suppose l'immatriculation de la pirogue, des équipements de sécurité minimum et des engins conformes. Redevances, "
      "pièces à fournir et guichet de délivrance : non confirmés (les montants anciens cités par des études sont "
      "dépassés) : les demander à la Direction des pêches maritimes (DPM).",
      "Immatriculation : la loi de 2015 étend l'immatriculation à toutes les embarcations de pêche opérant dans les eaux "
      "sous juridiction sénégalaise, y compris celles d'étrangers établis régulièrement au Sénégal. Des rapports ont "
      "recommandé de finaliser les procédures d'immatriculation des pirogues : la situation actuelle est à vérifier "
      "auprès de la DPM.",
      "Gestion locale : les conseils locaux de pêche artisanale (CLPA) sont des organes de cogestion locale de la ressource, "
      "institutionnalisés pour associer les pêcheurs aux décisions (FAO) ; leur fonctionnement actuel dans chaque port "
      "n'est pas confirmé.",
      "Repos biologique : des périodes de fermeture de la pêche de certaines espèces, comme le poulpe, sont fixées par arrêté "
      "ministériel et varient d'une année à l'autre (un mois pour le poulpe en pêche artisanale en 2012, d'après l'ANSD). "
      "Les dates en vigueur ne sont pas confirmées ici : les demander à la DPM ou chercher l'arrêté au Journal officiel.")),
)

SPECIFIC_FIRST = ("peche_artisanale",)
