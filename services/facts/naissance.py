"""Repères sur la déclaration de naissance au Sénégal (complète le sujet « papiers » de practical_facts.py).

Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les textes ont été relus dans les
extraits renvoyés par le moteur de recherche, d'où les formulations « à vérifier ») :
- Agence nationale de l'État civil (ANEC), foire aux questions, anec.sn/foire-aux-questions/ : déclaration au centre
  d'état civil du lieu de naissance, y compris pour une naissance à domicile ; déclaration normale jusqu'à 45 jours ;
  entre 45 jours et un an, déclaration reçue avec la mention « déclaration tardive » ; après un an, autorisation
  d'inscription tardive de naissance par le président du tribunal d'instance ; articles 51, 87 et 88 du Code de la
  famille cités.
- Recoupements : ANSD, enregistrement des faits d'état civil au Sénégal, 2013 (vie-publique.sn : un an, jugement
  d'un tribunal au-delà) ; notice sur la légalisation des documents sénégalais du ministère des Affaires étrangères des
  Pays-Bas (netherlandsworldwide.nl : au-delà d'un an, autorisation du tribunal) ; cabinets d'avocats sénégalais
  (fbavocat-sn.com, legalfieldsn.com, article 33 du Code de la famille sur les personnes pouvant déclarer).
- Délai : plusieurs sites juridiques et de démarches citent 30 jours, l'ANEC parle de 45 jours : les deux sont rapportés.
Source manquante (donc non ajouté) : coût de l'acte, pièces exactes exigées par chaque centre, procédure pour une
naissance à l'étranger, livret de famille, certificat de nationalité, acte de mariage.
"""

TOPICS = (
    ("naissance",
     r"\bdeclar\w* (\w+ ){0,3}naissances?\b|\bdeclarations? (de |d une |d un |des )?naissances?\b|"
     r"\bnaissances? (non |pas |jamais |mal )?declaree?s?\b|"
     r"\b(enfants?|bebes?|fils|filles?)\b.{0,40}\b(pas|jamais|non)\b.{0,15}\bdeclar(e|ee|es|ees)\b|"
     r"\b(bebes?|enfants?)\b.{0,80}\benregistr\w*.{0,50}\b(etat civil|mairie)\b|"
     r"\benregistr\w* (\w+ ){0,2}naissances?\b|\bregistres? (de l )?(etat civil|des naissances)\b|"
     r"\bjugements? suppletifs?\b|\bdeclarations? tardives?\b|\bautorisation d inscription\b|\banec\b|"
     r"\bagence nationale de l etat civil\b|"
     r"\b(register|registering|declare|declaring)\b.{0,30}\bbirth\b|\bbirth registration\b",
     ("Naissance survenue au Sénégal : la déclaration se fait auprès de l'officier d'état civil du centre d'état civil "
      "(en général la mairie) du lieu de naissance de l'enfant, même si les parents habitent ailleurs, y compris pour "
      "une naissance à domicile (Agence nationale de l'État civil, ANEC). Le délai normal va jusqu'à 45 jours après la "
      "naissance ; certains sites juridiques citent 30 jours : déclarer le plus tôt possible. À défaut des parents, "
      "d'autres personnes peuvent déclarer la naissance (article 33 du Code de la famille cité par des juristes : à "
      "vérifier auprès du centre d'état civil).",
      "Déclaration en retard : entre 45 jours et un an après la naissance, l'officier d'état civil reçoit encore la "
      "déclaration, avec la mention « déclaration tardive » sur l'acte. Après un an, il faut une autorisation "
      "d'inscription tardive de naissance (un jugement) délivrée par le président du tribunal d'instance (articles 51, "
      "87 et 88 du Code de la famille, cités par l'ANEC) : c'est le jugement supplétif. Mieux vaut ne pas attendre : "
      "l'extrait de naissance est demandé pour les autres papiers (voir les repères sur la carte d'identité et le "
      "passeport).",
      "Pièces et coût : la liste exacte varie selon le centre (en général le certificat de la structure de santé où la "
      "mère a accouché ou, pour une naissance à domicile, des témoins, et la pièce d'identité de la personne qui "
      "déclare) ; le coût éventuel de l'acte et des copies n'est pas confirmé : le demander au centre d'état civil, "
      "sans payer d'intermédiaire.",
      "Limite : ces repères concernent une naissance au Sénégal. Pour une naissance à l'étranger, ou pour un enfant "
      "d'une autre nationalité, s'adresser à l'ambassade ou au consulat concerné (procédure non confirmée ici).")),
)

SPECIFIC_FIRST = ("naissance",)
