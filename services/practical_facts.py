"""Repères pratiques vérifiés, ajoutés au contexte quand la question porte sur le sujet.

L'IA répond mieux avec le bon fait sous les yeux qu'en le cherchant dans sa mémoire :
numéros d'urgence, parité de l'euro, prises électriques, heure, visa, cartes SIM…
Seulement des repères durables (vérifiés en octobre 2026) ; les prix et horaires du
jour restent à vérifier par la recherche web.
"""

from __future__ import annotations

import re

from services.text import fold_text

# Sources des repères « arnaques » et « mobile_money » (relevées en octobre 2026 par recherche web ; les pages
# officielles elles-mêmes n'ont pas pu être ouvertes : ce sont des articles de presse et des synthèses qui relaient
# les communiqués, d'où les formulations « signalé » et « à vérifier »). Fraudes au mobile money : rapport de
# surveillance des services de paiement adossés à la monnaie électronique de la BCEAO, 1er semestre 2019 (arnaques
# « par hypnose », par code OTP, par erreur de dépôt, paiement marchand, e-commerce), relayé par droitmediasfinance.com ;
# affaires signalées 2023-2026 (osiris.sn, seneweb.com, senego.com, allafrica.com). Faux SMS d'amende : alertes du
# Trésor public (DGCPT, juillet 2026) et de la Police nationale (8 août 2026), relayées par allafrica.com, osiris.sn,
# senego.com, lesoleil.sn. Faux visas : communiqué du ministère de l'Intégration africaine et des Affaires étrangères
# du 16 avril 2026 (lesoleil.sn, seneplus.com, apanews.net, allafrica.com) ; escroqueries au visa : Police nationale,
# avril 2026 (allafrica.com, senego.com). Faux billets : communiqué de la BCEAO d'août 2026 (bceao.int,
# burkina24.com, lanouvelletribune.info) ; affaire de Rosso, mars 2026 (allafrica.com). Faux vendeurs en ligne :
# Police nationale, mars 2026 (allafrica.com). Faux policiers : presse sénégalaise (dakaractu.com, seneweb.com).
# Voyageurs : conseils aux voyageurs du Canada (travel.gc.ca) et des États-Unis (travel.state.gov). Plaintes : rappel
# de la BCEAO en 2018 (APS) sur le service de réclamations des émetteurs de monnaie électronique ; Division spéciale
# de cybersécurité de la Police nationale (osiris.sn) ; ARTP, régulateur des télécoms (osiris.sn). Free Sénégal devenu
# Yas : annonce de novembre 2024 (osiris.sn, apanews.net, afrik.com, lesoleil.sn). Aucun montant, plafond, frais ni
# numéro de téléphone n'est cité : ils changent et se vérifient auprès de l'opérateur ou de l'organisme.

# Sources des repères « papiers », « factures », « protection » et « études » (relevées en octobre 2026 ; ce sont
# des articles de presse et des documents officiels relayés, pas les sites des administrations : d'où les
# formulations « annoncé » et « à vérifier »). Carte d'identité : communiqué de la DAF relayé par APA
# (fr.apanews.net) et loi n° 2016-09 (vie-publique.sn). État civil : guides de démarches, plateforme Sama État
# civil (allafrica.com, 17/02/2026). e-Senegal et casier judiciaire : senego.com, mars 2026. Woyofal : Senelec,
# communiqué du 15/10/2024 relayé par senego.com, et grille tarifaire CRSE du 01/01/2026. CMU : Cour des comptes
# (vie-publique.sn), Agence de la CMU (décret 2015-21). CSS et IPRES : CLEISS et presse 2025-2026 (étude d'une
# fusion demandée en juin 2025, système d'information commun fin 2025). Campusen : calendrier 2026 (senego.com,
# lesoleil.sn), orientation.campusen.sn. Alerte de la Direction des bourses : février 2026 (presse).
# Sources du sujet « premiers_secours » (relevées en octobre 2026 par recherche web ; les sites officiels n'ont pas
# pu être ouverts en direct depuis l'environnement de travail, les textes ont été relus dans les extraits renvoyés
# par la recherche : ne sont gardés que des repères retrouvés dans plusieurs sources, sans dose ni nom de médicament).
# Paludisme : fiche d'information de l'OMS (who.int/news-room/fact-sheets/detail/malaria : symptômes, signes de
# gravité, moustiquaires imprégnées, répulsifs, avis médical avant le départ pour un traitement préventif) ; programme
# national de lutte contre le paludisme du Sénégal (test rapide devant toute fièvre, moustiquaires, « toutes les
# nuits »), relayé par les fiches d'Africa Check et de SenePlus et par l'enquête ANSD 2020-2021 sur les indicateurs du
# paludisme ; Institut Pasteur (Paris, fiche Sénégal) ; recommandations sanitaires aux voyageurs du HCSP (consulter
# sans délai en cas de fièvre, même après le retour), relayées par l'ARS de La Réunion et la presse médicale.
# Enfant : signes généraux de danger de la PCIME de l'OMS (livret PCIME aussi publié sur
# informationsanitaire.sec.gouv.sn), fiche OMS sur la méningite. Déshydratation et diarrhée : fiche OMS sur les
# maladies diarrhéiques ; conseils aux voyageurs du ministère français de l'Europe et des Affaires étrangères (relayés
# par le guide sécurité de France Volontaires) et de la diplomatie belge. Chaleur : NHS et CDC. Eau et aliments :
# « cinq clés pour des aliments plus sûrs » de l'OMS, CDC (Yellow Book), travel.gc.ca. Morsures et piqûres : OMS
# (rage, morsures de serpent), CDC (Yellow Book), Croix-Rouge américaine et MSD Manuals (scorpions, réactions
# allergiques). Brûlures et coupures : Croix-Rouge de Belgique (via l'ULB), ameli.fr et Croix-Rouge française (cités par
# Allodocteurs), CHUV. Numéros : ceux déjà vérifiés dans le sujet « urgences » (SAMU 1515), aucun autre.
# (identifiant, déclencheurs sur la question sans accents, repères)
TOPICS = (
    ("urgences", r"urgen|police|pompier|samu|ambulance|secours|accident|agress|\bvole\b|\bvolee?s?\b|perdu|danger|"
     r"(pays|endroit|quartier|ville|dakar|senegal) (est il |est elle )?sur\b|est (il|elle|ce) sur\b|securi(?!te (sociale|familiale|alimentaire))|\bsafe\b|"
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
    # Sujet sensible : repères généraux sans dose ni diagnostic, chaque repère renvoie vers un professionnel de santé
    # ou vers le SAMU 1515 (voir tests/test_practical_facts.py). Il complète « sante » sans en reprendre le contenu.
    ("premiers_secours",
     r"premiers? secours|secourisme|first aid|"
     r"paludisme|\bpalu\b|malaria|moustiquaires?|repulsif|anti moustiques?|mosquito|repellent|"
     r"fievre(?! jaune)|\bfevers?\b|feverish|convulsion|"
     r"deshydrat|dehydrat|coup de chaleur|insolation|heat ?stroke|sunstroke|heat exhaustion|"
     r"diarrhee|diarrhoea|diarrhea|tourista|gastro enterite|\bgastro\b|vomissement|\bvomir\b|\bvomit|"
     r"mal au ventre|maux de ventre|mal de ventre|"
     r"morsure|mordu(e|s)? par|m a mordu|ete mordu|mordre|chien enrage|animal enrage|\brabies\b|"
     r"(?<!en )(?<!fou de )\brage\b(?! de dents)|serpent|scorpion|"
     r"piqure(?! de rappel)|piqu(e|ee)s? par|fait piquer|bitten|\b(dog|snake|monkey|animal) bit\b|snake ?bite|"
     r"brulure|(?<!riz )\bbrule\b|ebouillant|"
     r"coupure(?! (de |d )?(courant|electricite|eau|internet|reseau|wifi))|je me suis coupe|plaie|entaille|"
     r"saignement|saigne|"
     r"eau (est |c est |est ce )(elle )?(potable|buvable)|est elle potable|non potable|pas potable|eau buvable|"
     r"(trouver|acheter|avoir|boire|besoin) (de )?l eau potable|eau potable (a boire|pour boire|en voyage)|"
     r"eau saine|eau en bouteille|eau du robinet|boire l eau|eau filtree|purifier l eau|tap water|"
     r"drinking water|bottled water|glacons|intoxication alimentaire|toxi infection|food poisoning|"
     r"manger dans la rue|manger sans (risque|danger)|"
     r"(risque|dangereu\w*|risqu\w+) (de |d |pour )?(manger|boire)|(manger|boire) (est il |est ce )?(dangereu\w*|risqu\w+)|"
     r"(enfant|bebe|nourrisson|fils|fille)s? (est |est tres |semble )?malade|"
     r"(child|baby|infant|son|daughter) (is |seems |looks )?(sick|ill)\b|"
     r"malaise|evanou|perd\w* connaissance|inconscient",
     ("Cadre : repères généraux d'autorités sanitaires (OMS, ministères de la Santé), qui ne remplacent pas un "
      "professionnel de santé. Ne poser aucun diagnostic et ne donner aucune dose de médicament : au moindre doute, "
      "voir un médecin ou un poste de santé. Signes graves (perte de connaissance, convulsions, difficulté à respirer, "
      "saignement qui ne s'arrête pas) : SAMU 1515, gratuit même sans crédit ; donner le lieu exact (quartier, repère "
      "connu, nom de l'hôtel), l'âge de la personne et ce qui s'est passé, suivre les consignes de l'opérateur et rester "
      "auprès de la personne. Police 17 et pompiers 18 selon la situation.",
      "Paludisme : transmis par des piqûres de moustiques, surtout la nuit. Signes : fièvre, frissons, maux de tête, "
      "courbatures, nausées ou vomissements, dans les jours ou les semaines qui suivent la piqûre, y compris après le "
      "retour de voyage. Toute fièvre doit faire consulter rapidement un professionnel de santé, qui fait un test : la "
      "maladie peut s'aggraver en moins de 24 h et ne se soigne jamais sans avis médical (pas d'automédication). Les "
      "enfants de moins de 5 ans, les femmes enceintes et les voyageurs sont les plus exposés aux formes graves.",
      "Paludisme grave (SAMU 1515 ou urgences sans attendre) : fatigue extrême, confusion ou somnolence anormale, "
      "convulsions, difficulté à respirer, urines foncées ou sanglantes, jaunisse (yeux ou peau jaunes), saignements "
      "anormaux.",
      "Prévention du paludisme : dormir chaque nuit sous une moustiquaire imprégnée d'insecticide (le programme "
      "national de lutte contre le paludisme en distribue : se renseigner au poste de santé), mettre un répulsif contre "
      "les moustiques (demander au pharmacien lequel convient à l'âge ou à la grossesse), porter des vêtements "
      "couvrants le soir, protéger les fenêtres par des moustiquaires. Voyageur : demander à un médecin ou à un "
      "centre de conseils aux voyageurs, avant le départ, si un traitement préventif est utile ; ne rien prendre sans "
      "prescription. Le risque dépend de la région et de la saison (transmission surtout pendant et après la saison des "
      "pluies).",
      "Fièvre chez l'enfant : ne pas attendre, surtout pour un bébé ou un enfant de moins de 5 ans ; le faire examiner "
      "rapidement dans un poste de santé, un centre de santé ou chez un médecin (test du paludisme, recherche d'autres "
      "causes). Ne pas donner de médicament sans avis d'un médecin ou d'un pharmacien. Signes de danger (SAMU 1515 ou "
      "urgences sans attendre) : l'enfant ne peut pas boire ni téter, vomit tout ce qu'il avale, a des convulsions, est "
      "très somnolent, difficile à réveiller ou inconscient (signes généraux de danger de l'OMS) ; aussi difficulté à "
      "respirer, nuque raide, taches violacées qui ne disparaissent pas quand on appuie dessus (infection grave "
      "possible, comme une méningite).",
      "Chaleur : boire régulièrement de l'eau sûre, rester à l'ombre aux heures chaudes, se reposer. Épuisement par la "
      "chaleur (fatigue, vertiges, maux de tête, nausées, transpiration abondante, crampes) : se mettre au frais, "
      "s'allonger, boire de l'eau, rafraîchir la peau ; sans amélioration en une trentaine de minutes, voir un "
      "professionnel de santé. Coup de chaleur (peau très chaude qui ne transpire plus, confusion, convulsions, perte "
      "de connaissance) : urgence médicale, SAMU 1515.",
      "Déshydratation (surtout chez le bébé, l'enfant et la personne âgée) : soif intense, yeux enfoncés, agitation ou "
      "au contraire grande somnolence, impossibilité de boire. Consulter un professionnel de santé sans attendre ; SAMU "
      "1515 si la personne est très somnolente, confuse ou ne peut plus boire.",
      "Diarrhée : remplacer l'eau perdue en buvant souvent ; l'OMS recommande une solution de "
      "réhydratation orale (SRO), à utiliser exactement selon la notice du produit (demander au pharmacien). Voir un "
      "médecin ou un poste de santé s'il y a du sang dans les selles, de la fièvre, des vomissements répétés, des "
      "signes de déshydratation ou si la diarrhée dure plus de quelques jours, et sans attendre pour un bébé ou un "
      "jeune enfant. Se laver les mains au savon.",
      "Morsure ou griffure d'animal (chien, chat, singe…) : laver tout de suite la plaie à l'eau et au savon pendant au "
      "moins 15 minutes, puis voir rapidement un professionnel de santé pour évaluer le risque de rage (vaccin "
      "éventuel). Morsure de serpent : aller sans attendre à l'établissement de santé "
      "le plus proche (SAMU 1515 si besoin), bouger le moins possible, retirer bagues, montre et vêtements serrés près "
      "de la morsure ; ne pas inciser ni sucer la plaie, pas de remèdes traditionnels.",
      "Piqûre de scorpion : toujours voir rapidement un professionnel de santé, surtout pour un enfant ; SAMU 1515 en "
      "cas de difficulté à respirer, convulsions, raideur musculaire, vertiges ou confusion. Piqûre d'insecte : SAMU "
      "1515 si le visage, les lèvres, la langue ou le cou gonflent, en cas de difficulté à respirer, d'urticaire "
      "étendue ou de malaise (réaction allergique grave).",
      "Brûlure : refroidir tout de suite sous l'eau courante tempérée (ni glacée, ni glaçons) pendant 10 à 20 minutes ; "
      "ne pas percer les cloques et ne rien appliquer (ni beurre, ni dentifrice). Voir un professionnel de santé si la "
      "brûlure a des cloques ; SAMU 1515 si elle est étendue, profonde, au visage, aux mains ou près "
      "de la bouche et du nez, électrique ou chimique, ou si la victime est un jeune enfant ou une personne âgée.",
      "Coupure : comprimer avec un linge propre pour arrêter le saignement, puis laver à l'eau propre et au savon et "
      "protéger par un pansement propre. Voir un professionnel de santé si la plaie est profonde, sale, au visage ou "
      "près d'une articulation, si le saignement ne s'arrête pas malgré la pression, si la vaccination contre le "
      "tétanos n'est pas à jour ou si des signes d'infection apparaissent (douleur qui augmente, rougeur, pus, fièvre) ; "
      "SAMU 1515 en cas de saignement abondant ou de perte de connaissance.",
      "Eau et aliments : boire de l'eau en bouteille scellée ou de l'eau bouillie (au moins 1 minute à gros bouillons) ; "
      "une eau d'apparence claire n'est pas forcément sûre. Éviter les glaçons dont l'origine est incertaine ; manger "
      "des aliments bien cuits et servis chauds, éplucher ou bien laver à l'eau sûre les fruits et légumes, éviter "
      "viandes, poissons et œufs peu cuits, se laver les mains avant de manger. Si des troubles apparaissent après un "
      "repas, voir un professionnel de santé.",
      "Voyageur : avant le départ, vérifier que l'assurance couvre les soins et le rapatriement sanitaire ; en cas "
      "d'hospitalisation ou de problème grave, prévenir son ambassade ou son consulat (urgence médicale : SAMU 1515).")),
    ("argent", r"\beuros?\b|fcfa|\bcfa\b|\bfrancs? cfa\b|\bxof\b|taux de change|\bchange\b|convert|dollars?\b|\bpayer\b|paiement|\bpay\b|payment|\bwave\b|orange money|"
     r"mobile money|distributeur|\batm\b|carte bancaire|bank card|envoyer de l argent|transfert|send money|remit",
     ("Monnaie : franc CFA BCEAO (XOF), à parité fixe avec l'euro : 1 € = 655,957 FCFA (donc 100 € = 65 595,70 FCFA). "
      "Pour le dollar ou la livre, le taux varie : utiliser le taux du jour.",
      "Paiements : Wave et Orange Money (paiement mobile) sont partout, y compris chez les petits commerçants et "
      "certains taxis ; distributeurs nombreux en ville, rares en brousse ; garder des petites coupures.",
      "Envoyer de l'argent vers le Sénégal : services de transfert (Wave, Orange Money, Western Union, Remitly, "
      "Wise…) avec réception sur un compte mobile money ou en espèces ; comparer les frais et le taux appliqué.")),
    ("arnaques", r"\barnaq\w*|\bescroc\w*|\bscams?\b|\bscammers?\b|\bswindl\w*|\bfraudsters?\b|"
     r"\bfaux (taxis?|guides?|billets?|visas?|policiers?|gendarmes?|agents?|commissaires?|douaniers?|recruteurs?|"
     r"recrutements?|sms|messages?|appels?|numeros?|proprietaires?|bailleurs?|vendeurs?|sites?|gains?)\b|"
     r"\bfausses? (monnaie|annonces?|offres?|amendes?|factures?|promesses?)\b|"
     r"\bfake (taxis?|guides?|police|visas?|money|notes?|bills?|banknotes?|recruit\w*|job offers?)\b|\bcounterfeit\w*|"
     r"\busurpation (d identite|de numero|de compte|de profil)|\busurp\w* (mon |ma |mes |son |sa |un |une |le |la |l )?"
     r"(identite|numero|compte|profil)\b|\bphishing\b|\bhameconn\w*|\bsim swap\b|\bspoof\w*|"
     r"\b(compte|whatsapp|telephone)\b.{0,25}\b(pirat\w*|hack\w*)|\bpirat\w* (de |du )?(mon |ton |son |un |ce )?(compte|whatsapp)\b|"
     r"\bse faire (avoir|rouler|plumer)\b|\bpieges? (a|pour) touristes?\b|\btourist traps?\b|\bsurfactur\w*|"
     r"\bpayer pour (avoir |obtenir )?(un |le |son |mon )?(visa|emploi|travail|poste|recrutement)\b|"
     r"\b(facilitateurs?|intermediaires?|demarcheurs?|rabatteurs?)\b.{0,40}\b(visa|emploi|travail|voyage|contrat)\b|"
     r"\bpromet\w* (un |le |du |de l )?(visa|emploi|travail|contrat)\b|"
     r"\b(louer|location|logement|appartement|studio|annonce)\b.{0,50}\b(a distance|sans (la |le )?visit\w*)|"
     r"\b(acomptes?|avances?|cautions?|reservation)\b.{0,40}\bavant (de |la |d )?(la )?(visit\w*|voir)\b|"
     r"\b(nouveau|autre) numero\b.{0,80}\b(argent|urgence|urgent|depanner|virement|envoyer|transfer\w*)|"
     r"\bsms\b.{0,30}\bamendes?\b|\bamendes?\b.{0,30}\bsms\b|"
     r"\b(retraits?|debits?|prelevements?|transferts?|transactions?|liens?|sites?|messages?|appels?) (frauduleu\w*|suspects?|louches?)|"
     r"\bfraud\w* (a |au |aux |par |sur |via |en )?(la |le |l )?(mobile|wave|orange|sms|carte|virement|paiement|transfert|visa|billets?|bancaires?)\b|"
     r"\bcode (secret|otp|pin|de verification)\b.{0,40}\b(demand\w*|donn\w*|communiq\w*|partag\w*|transmett\w*|envoy\w*|recu)\b|"
     r"\b(demand\w*|donn\w*|communiq\w*|partag\w*|transmett\w*)\b.{0,40}\bcode (secret|otp|pin|de verification)\b",
     ("Téléphone et mobile money (cas fréquemment signalés par la police et la presse) : un faux « agent » de l'opérateur "
      "appelle pour un « problème de compte », une « mise à jour » ou un « gain », ou affirme avoir envoyé de l'argent "
      "« par erreur », puis demande un code secret, un code reçu par SMS ou de taper un code dicté. Règle : ne jamais "
      "donner son code secret ni un code reçu par SMS, ne taper aucun code dicté par un inconnu, raccrocher et rappeler "
      "l'opérateur par un numéro officiel déjà connu.",
      "Faux SMS et faux liens : en juillet et août 2026, le Trésor public et la Police nationale ont alerté sur de faux "
      "SMS d'« amende » avec un lien de paiement ; le Trésor indique que les services de l'État n'envoient pas de SMS "
      "avec un lien cliquable pour payer une amende. Ne pas cliquer, ne pas répondre, ne donner aucune donnée bancaire ; "
      "vérifier sur un site officiel tapé soi-même.",
      "Faux visas et faux recrutements : en avril 2026, le ministère des Affaires étrangères a signalé un faux site "
      "vendant des « visas » du Sénégal et rappelé que les visas relèvent des missions diplomatiques et consulaires "
      "(le ministère indique qu'aucune procédure officielle payante en ligne n'est en vigueur : à vérifier auprès de "
      "l'ambassade) ; la Police nationale met en garde "
      "contre les « facilitateurs » qui promettent un visa ou un voyage contre de fortes sommes (affaires à Saint-Louis "
      "et à Kaolack en 2026). Ne rien verser à un intermédiaire pour un visa, un emploi ou un voyage organisé : vérifier "
      "l'employeur et passer par l'ambassade ou le consulat du pays concerné.",
      "Faux policiers et faux gendarmes : de faux gendarmes (faux contrôles dans des quartiers de Dakar), un faux "
      "policier venu à domicile et un faux enquêteur au téléphone ont été signalés par la presse sénégalaise. Demander "
      "la carte professionnelle et le nom, ne remettre ni téléphone, ni code, ni argent, proposer de se rendre au "
      "commissariat ; en cas de menace, appeler le 17.",
      "Faux billets : la BCEAO (communiqué d'août 2026) demande d'authentifier tout billet reçu avec les gestes décrits "
      "sur bceao.int, rubrique « Billets et pièces », et met en garde contre les méthodes de vérification qui circulent "
      "sur les réseaux sociaux (elles peuvent faire accepter des faux ou refuser de vrais billets). Un billet douteux ne "
      "se remet pas en circulation : le signaler à la police ou à la gendarmerie (à Rosso, en mars 2026, une commerçante "
      "a alerté la police et la BCEAO a confirmé le faux).",
      "Achats et locations à distance : des faux vendeurs copient les visuels de grandes enseignes, publient des "
      "annonces à prix très bas sur Facebook, Instagram ou TikTok, font payer par Wave ou Orange Money puis bloquent "
      "l'acheteur (réseau démantelé par la police en mars 2026). Prix anormalement bas = alerte ; payer à la livraison "
      "ou à un vendeur identifiable ; garder captures d'écran et références de paiement. Logement : ne rien payer, même "
      "un « acompte de réservation », avant une visite (par vous ou une personne de confiance), exiger un reçu écrit et "
      "vérifier l'identité du bailleur ou du mandataire. Terrain : voir aussi les repères sur le titre foncier.",
      "Faux proche, numéro usurpé, carte SIM : « mon téléphone est cassé, voici mon nouveau numéro » suivi d'une "
      "demande d'argent urgente est un schéma connu : rappeler le proche sur son ancien numéro ou lui poser une question "
      "que lui seul connaît avant tout envoi. Une ligne qui cesse soudain de fonctionner peut signaler un échange "
      "frauduleux de carte SIM (un cas a été signalé à Guédiawaye en 2025) : prévenir aussitôt l'opérateur.",
      "Voyageurs : les conseils aux voyageurs (Canada, États-Unis) signalent surtout les vols à la tire et à l'arraché "
      "dans les lieux fréquentés (marchés, gares routières, embarcadère de Gorée, Corniche) et les escroqueries par "
      "internet (offres d'argent, d'emploi ou de travail, histoires sentimentales) : ne jamais envoyer d'argent à "
      "quelqu'un rencontré en ligne. Sur place, convenir du prix avant de monter en taxi ou d'accepter un service (guide, "
      "porteur), garder passeport et objets de valeur hors de vue.",
      "Si l'on est victime : prévenir tout de suite l'opérateur (Wave, Orange Money, Yas…) pour demander le blocage, "
      "garder les preuves (captures d'écran, numéros, références de transaction), puis porter plainte au commissariat, à "
      "la brigade de gendarmerie ou à la Division spéciale de cybersécurité de la Police nationale (plainte contre X "
      "possible). Le remboursement n'est pas garanti : se renseigner auprès de l'opérateur.")),
    ("mobile_money", r"\borange money\b|\bmobile money\b|\bfree money\b|\byas money\b|\bmixx by yas\b|\bexpresso money\b|"
     r"\bmobile wallet\b|\be wallet\b|\bmonnaie electronique\b|\bporte monnaie (electronique|mobile)\b|\bwave\b|"
     r"\b(argent|virement|fcfa)\b.{0,40}\b(mauvais numero|par erreur|mauvais destinataire|mauvaise personne)\b|"
     r"\b(mauvais numero|par erreur|mauvais destinataire|mauvaise personne)\b.{0,40}\b(argent|virement|fcfa)\b|"
     r"\berreur (de |d )?(transfert|envoi|numero|destinataire)\b.{0,40}\b(argent|wave|orange|mobile)\b|"
     r"\bannuler (un |mon |le |ce )?(transfert d argent|virement|envoi d argent|paiement mobile)\b",
     ("À quoi ça sert : Wave, Orange Money et Free Money sont des services de monnaie électronique (un portefeuille sur "
      "le téléphone) pour envoyer et recevoir de l'argent, payer des commerçants et des factures (dont l'électricité "
      "Woyofal), recharger du crédit ou un forfait, déposer ou retirer des espèces chez un agent. Free Sénégal est "
      "devenu Yas (annonce de novembre 2024) : vérifier le nom actuel du service dans l'application. Frais, plafonds et "
      "conditions varient selon l'opérateur et changent : ils se vérifient dans l'application ou auprès de l'opérateur.",
      "Code secret : il est personnel. Ne jamais le dire (ni à un « agent de l'opérateur », ni à un vendeur, ni à un "
      "proche), ne jamais le saisir devant quelqu'un ni laisser un tiers « faire les manipulations » sur son téléphone ; "
      "même règle pour le code reçu par SMS. La BCEAO a recensé des arnaques par code OTP, par « erreur de dépôt » et "
      "« par hypnose » (un inconnu engage la conversation pour obtenir le code secret). Code connu d'un tiers ou doute : "
      "prévenir l'opérateur et changer le code.",
      "Envoi par erreur : vérifier le numéro (et le nom si l'application l'affiche) avant de valider. Si l'erreur est "
      "faite, agir tout de suite : contacter le service client de l'opérateur (application ou agence) avec la référence "
      "de la transaction, le numéro saisi, le montant et l'heure, et demander une réclamation écrite ; si le destinataire "
      "est joignable et de bonne foi, il peut renvoyer la somme. Possibilité d'annulation et délais : à vérifier auprès "
      "de l'opérateur, rien n'est garanti. Inversement, à quelqu'un qui dit avoir envoyé de l'argent « par erreur » et le "
      "réclame, ne rien renvoyer ni donner de code (arnaque décrite par la BCEAO) : demander à l'opérateur de gérer le "
      "retour.",
      "Fraude ou compte vidé : prévenir immédiatement l'opérateur (service client, agence) pour demander le blocage du "
      "compte ; conserver captures, numéros appelants et références ; porter plainte à la police, à la gendarmerie ou à "
      "la Division spéciale de cybersécurité (plainte contre X possible). Téléphone perdu ou volé : demander aussi le "
      "blocage de la ligne et du compte.",
      "Où se plaindre : d'abord le service client ou le service de réclamations de l'opérateur (la BCEAO rappelait en "
      "2018 que les émetteurs de monnaie électronique doivent offrir un service de plaintes et réclamations), puis, sans "
      "réponse satisfaisante, un courrier à la BCEAO, régulateur de la monnaie électronique. L'ARTP, régulateur des "
      "télécoms, reçoit les réclamations sur le service téléphonique et internet. Coordonnées et délais changent : à "
      "vérifier sur les sites des opérateurs, de la BCEAO et de l'ARTP.")),
    ("sim",r"\bsim\b|\besim\b|carte sim|operateur|internet|\bdata\b|forfait|wifi|telephone portable|phone plan",
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
     r"voiture|\blocations?\b|car rental|transport|se deplacer|get around|aller a|comment aller|how to get",
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
    ("papiers", r"carte (nationale )?d identite|\bcni\b|carte biometrique|passeport (senegalais|biometrique)|"
     r"(renouvel\w*|refaire|obtenir|perdu|perdre|duplicata|demande de) (\w+ ){0,2}passeport|senegalese (passport|id)|"
     r"acte de naissance|extrait de naissance|copie litterale|jugement suppletif|etat civil|casier judiciaire|"
     r"certificat de nationalite|\be senegal\b|\bnin\b|livret de famille|automatisation des fichiers",
     ("Carte d'identité biométrique CEDEAO : valable 10 ans (loi n° 2016-09). Le renouvellement des cartes délivrées en "
      "2016 a été annoncé à partir du 25 septembre 2026, dans les centres d'enrôlement au Sénégal et à l'étranger. "
      "Pièces annoncées : l'ancienne carte (avec copie) et un extrait de naissance avec sa copie littérale ; retrait "
      "avec le récépissé de dépôt et l'ancienne carte. Pour une première demande ou un cas particulier, demander la "
      "liste à jour au centre d'enrôlement ou à la Direction de l'automatisation des fichiers (DAF).",
      "Passeport : demande en personne (empreintes). Au Sénégal, dépôt auprès des services de police habilités ; à "
      "l'étranger, à l'ambassade ou au consulat du Sénégal, où le délai est souvent plus long car le dossier est traité "
      "à Dakar. Une carte d'identité biométrique valide est en général demandée ; en cas de perte ou de vol, déclarer "
      "d'abord à la police. Frais et délais changent : à vérifier auprès du commissariat ou du consulat.",
      "État civil : l'extrait de naissance se demande au centre d'état civil (en général la mairie) du lieu où la "
      "naissance a été déclarée. La copie littérale reproduit l'acte tel qu'inscrit au registre (utile pour vérifier "
      "l'orthographe des noms et les dates) ; la copie intégrale ou l'extrait avec filiation demande les noms des "
      "parents. Naissance jamais déclarée ou déclarée trop tard : il faut un jugement d'autorisation d'inscription "
      "(jugement supplétif) du tribunal.",
      "En ligne : la plateforme e-Senegal (lancée en mars 2026) regroupe des démarches, avec le NIN de la carte "
      "biométrique pour s'identifier ; le casier judiciaire en ligne n'est disponible que dans certaines juridictions "
      "pilotes. « Sama État civil » (ANEC), lancée le 16 février 2026 en phase pilote dans cinq communes (Ouakam, "
      "Cambérène, Golf Sud, Diakhao, Mbacké), permet de demander des actes à distance : vérifier si votre commune est "
      "couverte.",
      "Casier judiciaire (bulletin n° 3) : demande au greffe du tribunal ; pièces et frais varient, à demander au "
      "greffe. Un seul guichet officiel par démarche : ne pas payer d'intermédiaire pour « accélérer » un dossier, la "
      "fraude à l'état civil existe.")),
    ("factures", r"woyofal|senelec|compteur (electrique|prepaye|d electricite)|facture (d )?(electricite|courant)|"
     r"recharg\w* (mon |le |un |ma )?(compteur|electricite)|acheter (de )?l electricite|delestage",
     ("Woyofal (Senelec) : électricité prépayée. Chaque achat donne un code de 20 chiffres à saisir sur le compteur. "
      "Depuis le 15 octobre 2024, un achat peut donner trois codes de 20 chiffres à saisir l'un après l'autre ; les kWh "
      "s'affichent après le troisième.",
      "Où acheter : boutiques Woyofal, Wave, Orange Money et d'autres services de paiement mobile (liste annoncée en "
      "2022 : chercher l'option Senelec ou Woyofal dans le menu de son application). Senelec suspend parfois la vente "
      "de crédit la nuit pour maintenance : acheter avant. Une nouvelle grille tarifaire approuvée par la CRSE s'applique "
      "depuis le 1er janvier 2026 : le nombre de kWh par franc peut avoir changé.",
      "Numéro du service client : le vérifier sur senelec.sn ou en agence (ne pas se fier à un annuaire non officiel).")),
    ("protection", r"\bcmu\b|couverture maladie|assurance maladie|mutuelle de sante|bourse de securite familiale|\bbsf\b|"
     r"plan sesame|gratuite des soins|\bipres\b|securite sociale|pension de retraite|cotisation retraite|"
     r"allocations familiales|health insurance",
     ("Santé : la couverture maladie universelle (CMU), lancée en 2013 et coordonnée par l'Agence de la CMU (créée en "
      "2015), s'appuie sur des mutuelles de santé communautaires pour les travailleurs informels et ruraux (cotisation "
      "subventionnée par l'État, environ 50 % selon les documents officiels : à vérifier) et sur des gratuités : soins "
      "des enfants de 0 à 5 ans (depuis 2014) et plan Sésame pour les personnes de plus de 60 ans. L'application est "
      "inégale selon les structures : demander à l'établissement ce qui est pris en charge.",
      "Bourse de sécurité familiale (BSF) : transfert d'argent pour les ménages les plus pauvres ; se renseigner auprès "
      "de la mairie ou des services sociaux de l'État.",
      "Salariés : la Caisse de sécurité sociale (CSS) gère les prestations familiales et les accidents du travail ; "
      "l'IPRES gère les retraites. L'employeur doit déclarer et cotiser. Les deux institutions partagent un système "
      "d'information (fin 2025) et une fusion est à l'étude : vérifier la situation actuelle sur leurs sites officiels.")),
    ("etudes", r"campusen|apres le bac|nouveaux bacheliers|orientation post bac|\bcoud\b|\bbfem\b|"
     r"bourse (d etudes|etudiante|sociale|d excellence)|inscri\w* (a |en |dans )?(l )?universite",
     ("Après le bac : l'orientation vers les universités publiques et les ISEP passe par la plateforme officielle "
      "Campusen (orientation.campusen.sn) : créer un compte personnel, classer ses vœux (l'ordre compte pour "
      "l'affectation), puis valider le dossier avant la date limite. Les dates changent chaque année (en 2026 : du 17 "
      "août au 13 septembre). Les démarches se font directement en ligne, sans intermédiaire : ne jamais payer pour "
      "« accélérer » un dossier.",
      "Bourses : les bourses d'État (bourse entière, demi-bourse, aide aux non-boursiers) sont gérées par la Direction "
      "des bourses ; les montants cités dans la presse varient, à confirmer auprès de la Direction des bourses ou du "
      "COUD. Études à l'étranger : portail boursesetrangeres.campusen.sn, pour les Sénégalais déjà inscrits dans un "
      "établissement à l'étranger. Attention aux faux programmes de bourses (alerte de la Direction des bourses en "
      "février 2026).")),
    ("langue", r"quelles? langues?|langue officielle|languages?\b|speak|parle t on|on parle|parle t il",
     ("Langues : le français est la langue officielle ; le wolof est la langue la plus parlée ; on parle aussi pulaar, "
      "sérère, diola, mandingue, soninké… L'anglais est peu répandu hors des lieux touristiques.",)),
)

_COMPILED = tuple((name, re.compile(pattern), facts) for name, pattern, facts in TOPICS)


_fold = fold_text


_ENTRY_WORDS = re.compile(
    r"\bvisas?\b|entrer|entry|touriste|tourist|voyag\w*|venir|aller|partir|arriver|visiter|sejour\w*|"
    r"avant de|pour le senegal|to senegal|travel\w*"
)
# Un voyageur étranger qui perd « son passeport français » n'a pas besoin de la procédure sénégalaise.
_FOREIGN_TRAVELLER = re.compile(
    r"\b(francais\w*|americain\w*|belge|canadien\w*|britannique|suisse|allemand\w*|italien\w*|espagnol\w*|"
    r"french|american|british|german|canadian|touriste\w*|tourist\w*|foreigner)\b"
)
# « Arnaque » peut aussi être le titre d'un film ou d'une série : sans mot d'argent, de téléphone ou de visa, la
# question ne parle pas de fraude.
_FICTION_WORDS = re.compile(
    r"\b(films?|series?|romans?|episodes?|acteurs?|actrices?|chansons?|clips?|documentaires?|netflix|bande dessinee)\b"
)
_SCAM_CONTEXT = re.compile(
    r"\bwave\b|orange money|mobile money|\bsms\b|code secret|\botp\b|virement|\bvisa\b|faux (billets?|policiers?)|"
    r"whatsapp|\bsim\b|operateur"
)
# « Wave » seul peut être une vague de surf (« la wave est bonne au spot ») : on garde le sujet dès qu'un mot
# d'argent ou de mobile money apparaît aussi.
_SURF_WORDS = re.compile(r"\b(surf\w*|vagues?|houle|kite\w*|windsurf\w*|ocean|swell)\b")
_MOBILE_MONEY_WORDS = re.compile(
    r"orange money|mobile money|free money|yas money|expresso money|monnaie electronique|e wallet|mobile wallet|"
    r"porte monnaie|\bargent\b|transferts?|virement|\bcompte\b|\bcode\b|\bpin\b|payer|paiement|\bpay\b|envoy\w*|"
    r"\benvoi\b|retrait|depot|solde|fcfa|appli\w*"
)
# Sujets précis : ils passent avant les sujets généraux (« perdu », « payer », « aéroport »…) quand la limite coupe.
_SPECIFIC_FIRST = ("premiers_secours", "arnaques", "mobile_money", "papiers", "factures", "protection", "etudes")


def matching_topics(question: str, limit: int = 3) -> list[str]:
    folded = _fold(question)
    names = [name for name, pattern, _ in _COMPILED if pattern.search(folded)]
    if "arnaques" in names and _FICTION_WORDS.search(folded) and not _SCAM_CONTEXT.search(folded):
        names.remove("arnaques")
    if "mobile_money" in names and _SURF_WORDS.search(folded) and not _MOBILE_MONEY_WORDS.search(folded):
        names.remove("mobile_money")
    # « Renouveler mon passeport sénégalais » parle de papiers, pas du visa d'entrée d'un touriste.
    if "papiers" in names and "visa" in names and not _ENTRY_WORDS.search(folded):
        names.remove("visa")
    if "papiers" in names and _FOREIGN_TRAVELLER.search(folded) and "senegalais" not in folded:
        names.remove("papiers")
    names.sort(key=lambda name: name not in _SPECIFIC_FIRST)  # tri stable : l'ordre du tableau est gardé ensuite
    return names[:limit]


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
