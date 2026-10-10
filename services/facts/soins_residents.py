"""Repères sur les soins publics pour les résidents : structures, gratuités, mutuelles et CMU, réforme de 2026.

Complète « sante » et « protection » de practical_facts.py sans les reprendre (aucun déclencheur sur « CMU » seul :
« C'est quoi la CMU ? » reste une question du sujet « protection »).

Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les textes ont été relus dans les
extraits renvoyés par le moteur de recherche, d'où les formulations « selon » et « à vérifier ») :
- Organisation des soins : publications du ministère de la Santé hébergées sur informationsanitaire.sec.gouv.sn
  (organisation du système de santé, performance des centres de santé publics, plan stratégique sanitaire 2009-2018) et
  rapports de l'ANSD « Situation économique et sociale » 2015, 2016 et 2017-2018 (vie-publique.sn) : trois niveaux
  (central, intermédiaire, périphérique), districts sanitaires avec centre de santé et postes de santé, cases de santé,
  établissements publics de santé (EPS) de niveaux 1 à 3, quatorze régions médicales. Aucun effectif n'est repris (les
  chiffres relevés datent de 2009 à 2018).
- Gratuités : document de bilan de la CMU hébergé sur informationsanitaire.sec.gouv.sn (« La couverture maladie universelle
  au Sénégal : état de mise en œuvre, leçons et perspectives », données 2016) : gratuité des soins des enfants de 0 à 5
  ans, des 60 ans et plus, de la césarienne et de la dialyse.
- Cotisation des mutuelles : présentation gouvernementale (même site : 7 000 F par personne et par an, subventionnés à
  50 %, soit 3 500 F ; indigents pris en charge à 100 %), note de mission de l'AFD d'octobre 2013 (p4h.world), document du
  Catholic Relief Services (crs.org) et fiche « Les cotisations au Sénégal » du CLEISS (cleiss.fr, 2026, 3 500 F pour
  l'adhésion volontaire). Aucun document de l'Agence de la CMU elle-même n'a été retrouvé : montant à vérifier.
- Réforme de 2026 : projet de loi n° 16/2026 portant Code de la sécurité sociale, adopté par l'Assemblée nationale le 18
  août 2026 (rts.sn, senego.com, ceracle.com, pressafrik.com, lesoleil.sn) : assurance maladie universelle en trois régimes
  (salariés, indépendants, assistance médicale, article 262 cité par ceracle.com), extension aux indépendants et à
  l'économie informelle ; « officiellement en vigueur » fin septembre 2026 selon pulse.sn (30/09/2026) ; plus de
  cinquante textes d'application des codes du travail et de la sécurité sociale en préparation (allafrica.com, 01/10/2026).
  Cotisations, démarches et calendrier de mise en œuvre : non confirmés.
- Numéro vert : le site du ministère de la Santé (sante.gouv.sn) affiche, avec le SAMU 1515, un numéro vert 800 00 50 50
  que des articles de 2020 (allodocteurs.fr, mesvaccins.net) présentent comme la ligne d'information Covid-19 ; aucune
  source récente ne confirme son usage actuel.
Source manquante (donc non ajouté) : gratuité et calendrier de la vaccination des enfants (PEV), liste des hôpitaux et
leurs spécialités, tarifs des consultations, structures privées, conditions d'accès à la dialyse.
"""

TOPICS = (
    ("soins_residents",
     r"\bpostes? de sante\b|\bcentres? de sante\b(?! mentale)|\bcases? de sante\b|\bdistricts? sanitaires?\b|"
     r"\bpyramide sanitaire\b|\bregions? medicales?\b|\betablissements? (publics? )?de sante\b|"
     r"\bstructures? (de sante|sanitaires?)\b|\bhopitaux? (public|publics|regional|regionaux|de district)\b|"
     r"\bhopitaux? de niveau\b|\bse faire soigner\b|\bou (se )?soigner\b|"
     r"\bdialyse\b|\bcesarienne\b|\bsoins gratuits\b|\bgratuite (des soins|de la cesarienne|de la dialyse)\b|"
     r"\bassurance maladie universelle\b|\bcode de la securite sociale\b|"
     r"\b(cmu|mutuelles? de sante)\b.{0,50}\b(cotis\w*|adher\w*|inscri\w*|cout\w*|prix|combien|tarif)\b|"
     r"\b(cotis\w*|adher\w*|inscri\w*|cout\w*|combien|tarif)\b.{0,50}\b(cmu|mutuelles? de sante)\b|"
     r"\bministere de la sante\b|\bsante\.gouv\b|\bnumero vert\b.{0,30}\bsante\b|"
     r"\bpublic hospitals?\b|\bpublic health ?care\b",
     ("Soins publics : le système est organisé en pyramide. À la base, dans chaque district sanitaire, un centre de santé "
      "et des postes de santé (et, dans les villages, des cases de santé) ; au niveau intermédiaire, les régions "
      "médicales et les hôpitaux régionaux ; au sommet, les grands hôpitaux. Les hôpitaux publics sont des "
      "établissements publics de santé (EPS) classés en niveaux 1, 2 et 3. En principe, on consulte d'abord près de chez "
      "soi et l'on est orienté vers un échelon supérieur si nécessaire. Urgence grave : SAMU 1515. La structure la plus proche et ses horaires se demandent au district sanitaire, à la mairie ou "
      "sur place (à vérifier).",
      "Gratuités : un document de bilan de la couverture maladie universelle (données 2016) recense quatre initiatives de "
      "gratuité : les soins des enfants de 0 à 5 ans, les soins des personnes de 60 ans et plus (plan Sésame), la "
      "césarienne et la dialyse. Leur application est inégale selon les structures et peut avoir changé : demander à "
      "l'établissement, avant les soins, ce qui est pris en charge et les pièces à présenter.",
      "Mutuelles de santé et CMU : selon une présentation gouvernementale, une note de l'AFD (2013) et la fiche 2026 du "
      "CLEISS, la cotisation annuelle est de 7 000 FCFA par personne, dont la moitié est prise en charge par l'État pour "
      "les personnes qui peuvent cotiser, soit 3 500 FCFA pour l'adhérent ; les personnes indigentes sont prises en "
      "charge gratuitement. Montants, plafonds de remboursement et mutuelles disponibles changent et varient selon le "
      "lieu : à vérifier auprès de l'Agence de la CMU ou de la mutuelle locale.",
      "Réforme en cours : l'Assemblée nationale a adopté le 18 août 2026 un nouveau Code de la sécurité sociale (projet de "
      "loi n° 16/2026), qui pose le principe d'une assurance maladie universelle en trois régimes (salariés, "
      "indépendants, assistance médicale) et élargit la couverture aux indépendants et aux travailleurs de l'économie "
      "informelle (agriculteurs, artisans, commerçants, transporteurs). La presse l'a présenté comme en vigueur fin "
      "septembre 2026, avec plus de cinquante textes d'application des nouveaux codes du travail et de la sécurité "
      "sociale en préparation : cotisations, démarches et calendrier ne sont pas confirmés, ne rien promettre et "
      "renvoyer vers l'Agence de la CMU, la Caisse de sécurité sociale ou le Journal officiel.",
      "Numéros : SAMU 1515 pour une urgence médicale. Le site du ministère de la Santé (sante.gouv.sn) affiche aussi un "
      "numéro vert, le 800 00 50 50, ouvert à l'origine pour l'information sur la Covid-19 en 2020 : vérifier sur le "
      "site qu'il est toujours actif et à quoi il sert avant de le recommander.")),
)

SPECIFIC_FIRST = ("soins_residents",)
