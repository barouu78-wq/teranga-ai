"""Repères « frontieres » : passer une frontière terrestre vers un pays voisin (Gambie, Mauritanie, Mali, Guinée,
Guinée-Bissau).

Sources : aucun fait nouveau. La route par la Gambie (pont de Farafenni), le bateau de nuit Dakar–Ziguinchor et
les vols vers Ziguinchor et Cap Skirring reprennent le sujet « transport » de services/practical_facts.py et la
fiche Ziguinchor de data/senegal_knowledge.json ; les opérateurs (Orange, Yas, Expresso) reprennent le sujet
« sim » et les sources du sujet « arnaques ». Le 17/10/2026, les pages officielles (diplomatie.gouv.fr, bceao.int,
ecowas.int, gouv.sn) n'ont pas pu être ouvertes depuis l'environnement de travail : rien n'est donc dit des
monnaies, des postes frontières ni des pièces exigées par chaque pays voisin. Ces repères disent seulement quoi
vérifier et où, jusqu'à ce que des pages officielles soient lues et citées ici.
"""

# Pays et villes de l'autre côté de la frontière, sans le fleuve et la rivière Gambie (Niokolo-Koba), l'empire ou
# la fédération du Mali (histoire), le golfe de Guinée, la Guinée équatoriale ni la pintade (« guinea fowl »).
# Le Cap-Vert est laissé de côté : on n'y va pas par la route, et Dakar est sur la presqu'île du Cap-Vert.
_PAYS = (
    r"(?<!fleuve )(?<!riviere )\bgambie\b|\b(?:the )?gambia\b(?! river)|\bmauritanie\b|\bmauritania\b|"
    r"(?<!empire du )(?<!federation du )(?<!royaume du )\bmali\b|\bguinee bissau\b|\bguinea bissau\b|\bbissau\b|"
    r"(?<!golfe de )(?<!nouvelle )\bguinee\b(?! equatoriale)|(?<!new )(?<!equatorial )\bguinea\b(?! (?:pigs?|fowls?))|"
    r"\bbanjul\b|\bserrekunda\b|\bnouakchott\b|\bnouadhibou\b|\bbamako\b|\bconakry\b|\brosso\b|\bfarafenni\b|"
    r"\bpont de (?:la )?senegambie\b"
)
# Un pays voisin cité sans voyage (« la capitale de la Mauritanie », « les Peuls du Mali ») ne déclenche rien.
_PASSAGE = (
    r"\b(?:aller|vais|allons|allez|vont|partir|pars|partons|voyag\w*|passer|traverser|traversee|rejoindre|se rendre|"
    r"trajet|route|voiture|location|bus|sept places|7 places|taxi|camion|moto|transport|frontalier\w*|visas?|"
    r"passeports?|carte d identite|papiers|entrer|entree|sortir|douane|changer|change|monnaie|argent|devises?|"
    r"sim|puce|roaming|itinerance|reseau|mobile money|orange money|wave|sejour|vacances|visiter|visite|viens|venir|"
    r"dem|tukki|go|going|travel\w*|trip|drive|driving|cross|crossing|border|visit\w*|money|currency)\b"
)
# « Médecins sans frontières » ou « Reporters sans frontières » ne parlent pas de passer une frontière.
_FRONTIERE = r"(?<!sans )\bfrontieres?\b|\bborder crossing\b|\bcross(?:ing)? the border\b"

TOPICS = (
    ("frontieres", rf"{_FRONTIERE}|^(?=.*(?:{_PAYS}))(?=.*{_PASSAGE})",
     ("Passer une frontière terrestre : les papiers demandés dépendent de la nationalité et peuvent changer. Avant de "
      "partir, vérifier auprès de l'ambassade ou du consulat du pays voisin et, pour un étranger, dans les conseils "
      "aux voyageurs de son pays ; passer uniquement par un poste frontière officiel.",
      "Casamance par la route : la route par la Gambie (pont de Farafenni) traverse un autre pays, il faut des "
      "papiers valables pour la Gambie. Sans frontière : bateau de nuit Dakar–Ziguinchor (environ 15 h) ou avion "
      "vers Ziguinchor ou Cap Skirring.",
      "Argent : le franc CFA du Sénégal n'a pas forcément cours de l'autre côté de la frontière. Vérifier avant de "
      "partir la monnaie du pays voisin, et changer dans une banque ou un bureau de change agréé, jamais auprès d'un "
      "inconnu.",
      "Téléphone : hors du Sénégal, une SIM sénégalaise passe en itinérance (roaming) ; vérifier l'activation et le "
      "prix auprès de l'opérateur (Orange, Yas, Expresso) avant de partir. Même chose pour le mobile money.",
      "Sécurité : avant d'aller dans un pays voisin ou une zone frontalière, lire les conseils aux voyageurs "
      "officiels à jour (par exemple diplomatie.gouv.fr, travel.gc.ca, travel.state.gov) : la situation peut "
      "changer vite et certaines zones peuvent être déconseillées.",
      "En voiture : vérifier avant de partir les papiers du véhicule et l'assurance acceptés dans le pays traversé "
      "(auprès de l'assureur et de la douane). Une voiture de location ne peut pas toujours sortir du Sénégal : "
      "demander l'accord écrit du loueur.")),
)
SPECIFIC_FIRST = ("frontieres",)
