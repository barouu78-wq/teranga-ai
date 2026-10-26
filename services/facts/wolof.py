"""Bases de wolof pour un voyageur ou un débutant : salutations, politesse, oui/non, nombres de 1 à 10.

À FAIRE RELIRE PAR UN LOCUTEUR avant fusion : l'orthographe du wolof (langue surtout orale) varie d'une source à l'autre,
et aucun locuteur n'a pu relire ces expressions.

Règle de sélection : n'est gardée que l'expression retrouvée dans AU MOINS DEUX ressources d'apprentissage indépendantes.
Sources (consultées le 10 octobre 2026 par recherche web ; les pages elles-mêmes n'ont PAS pu être ouvertes depuis
l'environnement de travail, le réseau sortant refusant tous les sites visés : les listes ont été relues dans les
extraits renvoyés par le moteur de recherche) :
- Wikivoyage, guide de conversation wolof (en.wikivoyage.org/wiki/Wolof_phrasebook ; copie Wikitravel) : salutation arabe
  « Salamalekum » / réponse « Malekum Salaam », « Na'nga def ? » / « Mangi fi rekk », « Jere jef », « baal ma »,
  « Be benen yoon », « waaw » ; il précise que le wolof est surtout oral et que les graphies varient beaucoup.
- Janga Wolof (jangawolof.org : pages « Essential Wolof Phrases », « Phrases », « Numbers ») : « Salaam aleekum »,
  « Jërejëf », « Baal ma », « Ba beneen yoon », « Déedéet », nombres de 1 à 10.
- Recoupements : listenandlearn.org (Wolof Language Phrases and Basics for First-Time Learners), wolofschool.com et
  nkenne.com (nombres de 0 à 10, 1 à 100), kasahorow.org (nombres de 0 à 20), Princeton Bridge Year (« Nanga def ? » /
  « Mangi fi », « Jerejeff »), LangMedia du Five Colleges (salutation traditionnelle en wolof, avec une formule arabe de
  paix).
- Variantes relevées : « ñeent » ou « ñent » (4), « juróom » ou « juroom » (5), « Jërëjëf » ou « Jerejef », « Maa ngi fi rekk »
  ou « Mangi fi rekk », « Nanga def » ou « Na nga def ». Un seul site (polyglotclub.com) donne « bépp » pour 1 : écarté.
Source manquante (donc non ajouté) : « s'il vous plaît », « combien ça coûte ? », « où est… ? », « je ne comprends pas »,
nombres au-delà de 10, formules du soir et d'adieu, règles de prononciation, tutoiement et vouvoiement. À consulter : le
dictionnaire wolof-français d'Arame Fal, Rosine Santos et Jean Léonce Doneux (Karthala, 1990) et les publications du CLAD
(Centre de linguistique appliquée de Dakar).
"""

TOPICS = (
    ("wolof",
     r"\b(dire|dit|dis|disent|traduire|traduis|traduction|ecrire|ecrit|say|translate|translation)\b.{0,50}\bwolof\b|"
     r"\bwolof\b.{0,40}\b(pour debutants?|de base|basique|basics?|phrases?|expressions?|vocabulaire|vocabulary|salutations?|"
     r"greetings?|politesse|nombres?|chiffres?|numbers?|apprendre|learn)\b|"
     r"\b(apprendre|apprends|apprenez|learn|learning|parler|speak|vocabulaire|vocabulary|salutations?|greetings?|compter|"
     r"count)\b.{0,30}\bwolof\b|"
     r"\b(phrases?|expressions?|mots?|nombres?|chiffres?) (utiles? |de base )?(en |in )?wolof\b|"
     r"\b(bonjour|bonsoir|merci|salut|au revoir|pardon|excusez moi|excuse me|hello|thank you|thanks|goodbye|sorry|bienvenue|"
     r"welcome)\b.{0,25}\b(en|in) wolof\b|"
     r"\bjerejef\b|\bnanga def\b|\bna nga def\b|\bbaal ma\b|\bsalaam aleekum\b|\bsalamalekum\b|\bmaa ngi fi\b|\bmangi fi\b|"
     r"\bba beneen yoon\b",
     ("Wolof, repères de débutant : le wolof est la langue la plus parlée du Sénégal, mais c'est surtout une langue orale : "
      "l'orthographe varie d'un guide à l'autre. Les expressions ci-dessous sont recoupées dans au moins deux ressources "
      "d'apprentissage (Wikivoyage, Janga Wolof) mais n'ont pas été relues par un locuteur : les présenter comme des "
      "repères, préciser que la graphie et la prononciation peuvent varier, et conseiller de les faire confirmer par un "
      "locuteur.",
      "Salutations et politesse : « Salaam aleekum » (salutation d'origine arabe, « la paix sur vous ») appelle la réponse "
      "« Maalekum salaam ». « Nanga def ? » (aussi écrit « Na nga def ? ») demande « comment vas-tu ? » ; réponse courante : "
      "« Maa ngi fi rekk » (écrit aussi « Mangi fi rekk »), à peu près « je suis juste ici », donc « ça va ». « Jërëjëf » "
      "(écrit aussi « Jerejef ») veut dire « merci ». « Baal ma » veut dire « excusez-moi, pardon ». « Waaw » veut dire "
      "« oui » et « Déedéet » « non ». « Ba beneen yoon » veut dire « à la prochaine ».",
      "Nombres de 1 à 10 : 1 benn, 2 ñaar, 3 ñett, 4 ñeent (écrit aussi ñent), 5 juróom, 6 juróom-benn (5 + 1), 7 "
      "juróom-ñaar, 8 juróom-ñett, 9 juróom-ñeent, 10 fukk. Les nombres de 6 à 9 se construisent avec juróom (cinq). "
      "Au-delà de 10 et pour les prix : non confirmé ici, à demander à un locuteur ou à un dictionnaire.")),
)

SPECIFIC_FIRST = ("wolof",)
