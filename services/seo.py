from flask import Response
import json
from html import escape
from urllib.parse import quote

from services.site_layout import HEAD_ASSETS, asset_url, body_tag, site_footer, site_header
import os

SITE_URL = os.getenv("SITE_URL", "https://teranga-ai.fr").rstrip("/")

SEO_PAGES = {
    "senegal": {
        "title": "Guide Sénégal : Dakar, Gorée, 14 régions | Teranga AI",
        "description": "Guide pratique du Sénégal : Dakar, Gorée, météo, où manger, AIBD. Assistant gratuit en français, anglais et wolof.",
        "h1": "Guide du Sénégal",
        "intro": "Teranga AI aide à s'orienter au Sénégal : une question, une réponse courte. Horaires et tarifs se vérifient le jour J.",
        "sections": [
            ("Que demander", "Météo Dakar, ferry Gorée, trajet AIBD, ceebu jen, quartiers pour manger, les 14 régions."),
            ("Repères", "14 régions. Dakar pour l'arrivée. Saint-Louis, Lac Rose, Petite Côte, Touba, Casamance au sud."),
            ("Langues", "Français, anglais et wolof."),
        ],
        "faq": [
            ("Teranga AI est-il gratuit ?", "Oui. Aucune inscription n'est obligatoire."),
            ("Ça marche dans quelle langue ?", "Français, anglais et wolof."),
        ],
        "related": [("meteo-dakar", "Météo Dakar"), ("visiter-goree", "Gorée"), ("regions-senegal", "14 régions")],
    },
    "meteo-dakar": {
        "title": "Météo Dakar aujourd'hui : chaleur, vent, ciel | Teranga AI",
        "description": "Météo Dakar du jour. Demandez à Teranga AI les conditions avant Gorée, Ngor ou l'aéroport AIBD.",
        "h1": "Météo Dakar",
        "intro": "Le temps à Dakar change vite. Demandez la météo à Dakar aujourd'hui pour une réponse courte.",
        "sections": [
            ("Questions utiles", "Météo Dakar aujourd'hui, demain à Ngor, vérifier avant le ferry Gorée."),
            ("Saisons", "Saison sèche plutôt novembre-mai, pluies souvent de juin à octobre. Ce sont des repères, pas une prévision."),
            ("Ensuite", "Ajoutez un lieu : plage, île, AIBD. Teranga peut enchaîner avec une carte."),
        ],
        "faq": [
            ("La météo est-elle en direct ?", "L'assistant peut chercher les conditions récentes. Précisez aujourd'hui ou demain."),
            ("Et hors Dakar ?", "Oui : Saint-Louis, Saly, Ziguinchor, Cap Skirring."),
        ],
        "related": [("visiter-goree", "Gorée"), ("restaurants-dakar", "Où manger"), ("senegal", "Guide")],
    },
    "visiter-goree": {
        "title": "Visiter Gorée : Maison des Esclaves, ferry, photos | Teranga AI",
        "description": "Île de Gorée : histoire, Maison des Esclaves, ferry depuis Dakar. Photos et carte avec Teranga AI.",
        "h1": "Visiter l'île de Gorée",
        "intro": "Gorée fait face à Dakar. On y vient pour l'histoire et la Maison des Esclaves. Demandez une réponse courte, photos et carte.",
        "sections": [
            ("S'y rendre", "Ferry depuis le port de Dakar. Horaires et tarifs : à vérifier le jour du départ."),
            ("Quoi voir", "Maison des Esclaves, ruelles, musées. Comptez 2 à 4 heures."),
            ("Question type", "Parle-moi de Gorée et montre l'île."),
        ],
        "faq": [
            ("Une demi-journée suffit-elle ?", "Oui, beaucoup de visites tiennent en une matinée."),
            ("Faut-il réserver le ferry ?", "Souvent non. Vérifiez l'affluence le jour J."),
        ],
        "related": [("meteo-dakar", "Météo"), ("restaurants-dakar", "Manger à Dakar"), ("senegal", "Guide")],
    },
    "restaurants-dakar": {
        "title": "Où manger à Dakar : Plateau, Médina, Almadies, Ngor | Teranga AI",
        "description": "Où manger à Dakar par quartier : Plateau, Médina, Almadies, Ngor, Ouakam. Ceebu jen, yassa, marchés.",
        "h1": "Où manger à Dakar",
        "intro": "On mange à Dakar par quartier, pas par meilleur resto unique. Demandez un quartier. Teranga oriente sans inventer une enseigne fermée.",
        "sections": [
            ("Quartiers", "Plateau : centre. Médina : cuisine du quotidien. Almadies et Ngor : mer. Ouakam : mix résidentiel."),
            ("Plats", "Ceebu jen, yassa, mafé, dibi. Précisez Casamance ou Saint-Louis pour une spécialité régionale."),
            ("Marchés", "Demandez près de... plutôt qu'un classement."),
        ],
        "faq": [
            ("Y a-t-il des notes Google ?", "Non. L'assistant situe le quartier et le type de plat."),
            ("Hors Dakar ?", "Saint-Louis, Saly, Ziguinchor, Cap Skirring."),
        ],
        "related": [("specialites-senegal", "Spécialités"), ("visiter-goree", "Gorée"), ("meteo-dakar", "Météo")],
    },
    "specialites-senegal": {
        "title": "Spécialités du Sénégal : ceebu jen, yassa, mafé | Teranga AI",
        "description": "Cuisine sénégalaise : ceebu jen, yassa, mafé, plats du Nord et de Casamance. Où les goûter.",
        "h1": "Spécialités du Sénégal",
        "intro": "La cuisine change selon la mer, le fleuve et la Casamance. Teranga cite 3 ou 4 plats, pas une liste infinie.",
        "sections": [
            ("Plats connus", "Ceebu jen, yassa, mafé, dibi."),
            ("Régions", "Nord : mil et fleuve. Centre : arachide. Casamance : riz, fruits, poisson fumé."),
            ("Où chercher", "Un quartier à Dakar, ou une ville : Saint-Louis, Kaolack, Ziguinchor."),
        ],
        "faq": [
            ("Quel plat est le plus cite ?", "Le ceebu jen, souvent le midi."),
            ("Y a-t-il des photos ?", "Pour certains sujets, oui, via Wikimedia."),
        ],
        "related": [("restaurants-dakar", "Où manger"), ("regions-senegal", "Régions"), ("senegal", "Guide")],
    },
    "france-senegal": {
        "title": "Sénégal et France : voyage, diaspora, démarches | Teranga AI",
        "description": "Teranga AI accompagne les personnes au Sénégal et en France : voyage, Dakar, AIBD, démarches, culture, langues et vie de la diaspora.",
        "h1": "Sénégal ↔ France",
        "intro": "Un assistant pensé pour les personnes qui vivent au Sénégal, voyagent entre le Sénégal et la France, ou gardent un lien avec le pays.",
        "sections": [
            ("Pour le Sénégal", "Dakar, AIBD, transport, météo, régions, gastronomie, culture et informations pratiques."),
            ("Pour la France", "Questions de voyage, préparation du séjour, repères culturels, langues et informations utiles pour la diaspora sénégalaise."),
            ("Langues", "Français, anglais et wolof, selon la demande."),
        ],
        "faq": [
            ("Teranga AI fonctionne-t-il depuis la France ?", "Oui. Le service est accessible sur le web depuis la France comme depuis le Sénégal."),
            ("Peut-on préparer un voyage au Sénégal ?", "Oui. Demandez les formalités, le transport, les lieux, la météo ou les repères utiles ; les informations changeantes sont à vérifier."),
        ],
        "related": [("senegal", "Guide du Sénégal"), ("regions-senegal", "14 régions"), ("meteo-dakar", "Météo Dakar")],
    },
    "diaspora-senegalaise": {
        "title": "Diaspora sénégalaise : France ↔ Sénégal | Teranga AI",
        "description": "Assistant pour la diaspora sénégalaise en France et ailleurs : démarches, voyage, régions, culture, langues et vie pratique au Sénégal.",
        "h1": "Diaspora sénégalaise",
        "intro": "Teranga AI aide à garder un lien pratique avec le Sénégal : préparer un voyage, comprendre une démarche, retrouver une région ou découvrir une spécialité.",
        "sections": [
            ("Depuis la France", "Préparez un séjour au Sénégal, recherchez des repères sur Dakar et les régions, ou posez une question sur la culture et les langues."),
            ("Au Sénégal", "Transport, météo, gastronomie, lieux, cartes et informations pratiques selon le contexte."),
            ("Une réponse adaptée", "Précisez votre ville, votre région ou votre situation pour obtenir une réponse plus pertinente."),
        ],
        "faq": [
            ("L'assistant est-il réservé aux voyageurs ?", "Non. Il s'adresse aussi aux résidents, à la diaspora et aux commerçants."),
            ("Peut-on parler wolof ?", "Oui, Teranga AI propose le wolof en plus du français et de l'anglais. Le pulaar est en cours d'amélioration et n'est pas encore proposé dans l'interface."),
        ],
        "related": [("france-senegal", "France ↔ Sénégal"), ("senegal", "Guide du Sénégal"), ("specialites-senegal", "Spécialités")],
    },
    "a-propos": {
        "title": "À propos de Teranga AI : assistant numérique du Sénégal",
        "description": "Découvrez Teranga AI, assistant numérique consacré au Sénégal : informations pratiques, voyage, culture, langues et vie quotidienne.",
        "h1": "À propos de Teranga AI",
        "intro": "Teranga AI est un assistant numérique pensé autour du Sénégal et accessible depuis le Sénégal, la France et la diaspora.",
        "sections": [
            ("Un assistant pour le Sénégal", "Teranga AI aide à trouver des repères sur Dakar, les régions, les transports, la météo, la culture, la gastronomie et les langues."),
            ("Pour plusieurs publics", "Voyageurs, résidents, diaspora et commerçants peuvent poser leurs questions en français, anglais ou wolof."),
            ("Partenariats et soutien", "Teranga AI peut travailler avec des entreprises, médias, acteurs du tourisme, écoles et écosystèmes tech. Un soutien peut prendre la forme d’un pilote, d’un partenariat, d’une mise en relation ou d’un financement du développement."),
            ("Informations à vérifier", "Pour les horaires, tarifs, formalités et autres informations susceptibles de changer, Teranga AI peut rechercher des sources récentes et invite à vérifier les informations officielles.")
        ],
        "faq": [
            ("Teranga AI est-il accessible depuis le Sénégal ?", "Oui, le service est accessible sur le web depuis le Sénégal."),
            ("Quelles langues sont disponibles ?", "Français, anglais et wolof. Le pulaar est en cours d'amélioration.")
        ],
        "related": [("senegal", "Guide du Sénégal"), ("france-senegal", "France ↔ Sénégal"), ("diaspora-senegalaise", "Diaspora sénégalaise")]
    },
    "presse": {
        "title": "Presse et médias : Teranga AI au Sénégal",
        "description": "Informations presse sur Teranga AI : présentation, usages, langues et ressources pour les médias sénégalais.",
        "h1": "Presse et médias",
        "intro": "Cette page rassemble les informations essentielles pour présenter Teranga AI dans un article, une émission ou une publication numérique.",
        "sections": [
            ("Pour les partenaires", "Les médias, entreprises et organisations peuvent demander une présentation du projet, proposer un pilote ou contribuer à sa visibilité. Le kit média présente les usages et ressources disponibles."),
            ("Présentation courte", "Teranga AI est un assistant numérique consacré au Sénégal. Il répond aux questions pratiques sur les villes, régions, voyage, transport, culture, gastronomie, météo et langues."),
            ("Présentation longue", "Pensé pour les personnes au Sénégal et pour la diaspora, Teranga AI permet de poser une question en français, anglais ou wolof. Pour les informations changeantes, l'assistant peut rechercher des sources récentes."),
            ("Contact presse", "Pour une demande média, utilisez les coordonnées de contact publiées par Teranga AI sur son site. Ne reprenez pas une information sensible sans la vérifier."),
        ],
        "faq": [
            ("Teranga AI est-il un média ?", "Non. Teranga AI est un service d'assistance numérique ; les informations journalistiques doivent être attribuées à leurs sources."),
            ("Peut-on utiliser Teranga AI pour préparer un reportage ?", "Oui, comme outil de recherche et de préparation, avec vérification des informations auprès des sources originales."),
        ],
        "related": [("a-propos", "À propos"), ("senegal", "Guide du Sénégal"), ("france-senegal", "France ↔ Sénégal")],
    },
    "media-kit": {
        "title": "Kit média Teranga AI : logo, présentation et ressources",
        "description": "Kit média Teranga AI pour journalistes, créateurs et partenaires : présentation, identité et ressources de communication.",
        "h1": "Kit média Teranga AI",
        "intro": "Une fiche simple pour présenter Teranga AI de manière cohérente sur un site, un média, une newsletter ou les réseaux sociaux.",
        "sections": [
            ("Partenariat", "Le kit peut servir de base à une présentation auprès d’un média, d’un partenaire, d’un incubateur ou d’un financeur intéressé par l’IA et les usages numériques au Sénégal."),
            ("Nom", "Teranga AI"),
            ("Description courte", "Assistant numérique du Sénégal, accessible depuis le Sénégal et la diaspora, en français, anglais et wolof."),
            ("Usages", "Voyage, Dakar, AIBD, transport, météo, régions, culture, gastronomie, langues et informations pratiques."),
            ("Lien officiel", SITE_URL + "/"),
        ],
        "faq": [
            ("Peut-on reprendre la description courte ?", "Oui, en conservant le nom Teranga AI et en renvoyant vers le site officiel."),
            ("Les réponses de Teranga AI remplacent-elles les sources officielles ?", "Non. Les informations administratives, juridiques, tarifaires ou très récentes doivent être vérifiées auprès des sources compétentes."),
        ],
        "related": [("a-propos", "À propos"), ("presse", "Presse"), ("senegal", "Guide du Sénégal")],
    },
    "regions-senegal": {
        "title": "14 régions du Sénégal : villes et carte | Teranga AI",
        "description": "Les 14 régions du Sénégal : Dakar, Thiès, Saint-Louis, Ziguinchor, Tambacounda. Villes et Casamance.",
        "h1": "Les 14 régions du Sénégal",
        "intro": "Teranga situe une région, une ville et un trajet, avec photo ou carte si le lieu est connu.",
        "sections": [
            ("Liste", "Dakar, Thiès, Diourbel, Fatick, Kaolack, Kaffrine, Tambacounda, Kédougou, Kolda, Sédhiou, Ziguinchor, Saint-Louis, Louga, Matam."),
            ("Zones", "Ouest : Dakar-Thiès. Nord : Saint-Louis, Louga, Matam. Sud / Casamance : Ziguinchor, Sédhiou, Kolda."),
            ("À demander", "Présente la Casamance. Où est Saint-Louis. Comment aller à Ziguinchor."),
        ],
        "faq": [
            ("Combien de régions ?", "14 régions administratives."),
            ("La Casamance est-elle une région ?", "C'est le Sud, sur Ziguinchor, Sédhiou et Kolda."),
        ],
        "related": [("senegal", "Guide"), ("specialites-senegal", "Cuisine"), ("visiter-goree", "Gorée")],
    },

    "dakar": {
        "title": "Dakar : quartiers, transport, que voir | Teranga AI",
        "description": "Guide de Dakar : AIBD, quartiers, transport, météo, Gorée, restaurants et repères pratiques pour habitants et voyageurs.",
        "h1": "Dakar",
        "intro": "Teranga AI vous aide à préparer ou comprendre Dakar : arrivée à AIBD, déplacements, quartiers, météo, gastronomie et sorties.",
        "sections": [
            ("Arriver à Dakar", "Demandez un itinéraire depuis AIBD, un repère sur les transports ou les informations utiles pour votre arrivée. Les horaires et tarifs doivent être vérifiés le jour du trajet."),
            ("Quartiers et sorties", "Plateau, Médina, Almadies, Ngor, Ouakam et d'autres quartiers peuvent être abordés selon votre besoin : manger, dormir, se déplacer ou découvrir la ville."),
            ("Dakar et Gorée", "Pour une visite de Gorée, demandez les repères sur le ferry, la météo et les points d'intérêt. Les horaires de traversée sont à vérifier avant le départ."),
            ("Météo et vie pratique", "Demandez la météo du jour, une tenue adaptée, un trajet ou une information pratique. Pour les données qui changent, Teranga AI recherche des informations récentes lorsque nécessaire.")
        ],
        "faq": [
            ("Comment aller de AIBD à Dakar ?", "Demandez votre destination ou votre quartier et Teranga AI peut rechercher les options de transport récentes."),
            ("Quels quartiers de Dakar peut-on explorer ?", "Plateau, Médina, Almadies, Ngor, Ouakam et d'autres quartiers peuvent être décrits selon votre activité."),
            ("Peut-on préparer une journée à Dakar ?", "Oui. Indiquez votre point de départ, le temps disponible et vos centres d'intérêt.")
        ],
        "related": [("meteo-dakar", "Météo Dakar"), ("visiter-goree", "Visiter Gorée"), ("restaurants-dakar", "Restaurants Dakar"), ("senegal", "Guide du Sénégal")]
    },
    "pour-les-entreprises": {
        "title": "Teranga AI pour les entreprises au Sénégal et en France",
        "description": "Teranga AI pour hôtels, restaurants, commerces, agences, tourisme et entreprises : assistant Sénégal, visibilité digitale et parcours clients.",
        "h1": "Teranga AI pour les entreprises",
        "intro": "Un assistant numérique consacré au Sénégal, pensé pour créer un point d’entrée simple entre vos clients et les informations utiles.",
        "sections": [
            ("Hôtels, restaurants et tourisme", "Aidez vos clients à trouver des repères sur Dakar, les transports, la météo, les quartiers, les spécialités et les lieux à visiter."),
            ("Commerçants et services", "Utilisez Teranga AI comme point de découverte pour les questions fréquentes : horaires à vérifier, itinéraires, langues, produits, services et informations pratiques."),
            ("Entreprises et partenaires", "Nous pouvons étudier un pilote, une intégration, une campagne de visibilité ou un partenariat éditorial avec des acteurs au Sénégal et en France."),
            ("Un bouton Teranga AI sur votre site", "Ajoutez une ligne à votre site : <code>&lt;script src=\"https://teranga-ai.fr/widget.js\" data-partner=\"votre-nom\" data-lang=\"fr\" defer&gt;&lt;/script&gt;</code>. Un bouton « Une question sur le Sénégal ? » ouvre Teranga AI pour vos visiteurs, sans lire ni transmettre aucune donnée de votre site. Options : data-lang (fr, en, wo), data-position (right, left), data-question (question pré-remplie)."),
            ("Une présence qui se partage", "Le site, les pages thématiques, les réseaux sociaux, les médias et les annuaires peuvent relayer Teranga AI. L’objectif est de construire une présence cohérente, sans spam ni fausses affiliations.")
        ],
        "faq": [
            ("Peut-on travailler avec Teranga AI ?", "Oui. Les entreprises, médias, acteurs du tourisme et organisations peuvent proposer un pilote ou un partenariat."),
            ("Le service vise-t-il uniquement Dakar ?", "Non. Le contenu et les pages couvrent le Sénégal, avec un axe particulier sur Dakar et les besoins de la diaspora."),
            ("Peut-on proposer Teranga AI à des clients ?", "Oui, comme outil d’information et d’orientation, en gardant une vérification des informations sensibles ou changeantes.")
        ],
        "related": [("partenaires", "Partenaires"), ("presse", "Presse"), ("media-kit", "Kit média"), ("france-senegal", "France ↔ Sénégal")]
    },
    "partenaires": {
        "title": "Partenaires Teranga AI : Sénégal, France et diaspora",
        "description": "Partenariats Teranga AI avec médias, tourisme, entreprises, associations, écoles et acteurs tech au Sénégal et en France.",
        "h1": "Partenaires",
        "intro": "Teranga AI cherche des partenaires qui veulent améliorer l’accès aux informations pratiques sur le Sénégal et développer des usages numériques utiles.",
        "sections": [
            ("Médias et créateurs", "Articles, interviews, newsletters, émissions, vidéos et contenus pédagogiques peuvent présenter le service avec un lien vers le site officiel."),
            ("Tourisme et hôtellerie", "Hôtels, agences, guides, restaurants et acteurs du tourisme peuvent explorer des parcours d’information pour leurs visiteurs."),
            ("Entreprises et écosystèmes tech", "Incubateurs, écoles, entreprises numériques et réseaux professionnels peuvent proposer des démonstrations, pilotes ou collaborations."),
            ("Sénégal ↔ France", "Les acteurs de la diaspora et les réseaux franco-sénégalais peuvent contribuer à faire connaître un assistant accessible depuis les deux pays.")
        ],
        "faq": [
            ("Comment proposer un partenariat ?", "Présentez votre organisation, votre audience, votre idée et le type de collaboration envisagé."),
            ("Teranga AI accepte-t-il les mises en avant payantes ?", "Les modalités commerciales doivent être définies au cas par cas et présentées clairement aux utilisateurs."),
            ("Peut-on utiliser le logo et le kit média ?", "Oui pour présenter Teranga AI, en conservant une description exacte et un lien vers le site officiel.")
        ],
        "related": [("pour-les-entreprises", "Pour les entreprises"), ("presse", "Presse"), ("media-kit", "Kit média"), ("a-propos", "À propos")]
    },
    "assistant-senegal": {
        "title": "Assistant Sénégal : voyage, Dakar, infos pratiques | Teranga AI",
        "description": "Assistant Sénégal en ligne : questions sur Dakar, voyage, transport, météo, culture, cuisine, régions et vie pratique, en français, anglais et wolof.",
        "h1": "Assistant Sénégal",
        "intro": "Teranga AI est un assistant numérique consacré au Sénégal. Posez une question sur Dakar, un trajet, une région, la météo, la culture ou la vie pratique.",
        "sections": [
            ("Voyage et déplacements", "Préparez un séjour au Sénégal, demandez des repères sur AIBD, Dakar, Gorée, les transports, les quartiers et les régions."),
            ("Vie pratique", "Posez une question sur la météo, les spécialités, les langues, les services ou une situation du quotidien. Pour les informations changeantes, les sources récentes doivent être vérifiées."),
            ("Pour le Sénégal et la diaspora", "Le service est accessible depuis le Sénégal, la France et ailleurs. Vous pouvez préciser votre ville, votre région ou votre contexte pour obtenir une réponse plus ciblée."),
        ],
        "faq": [
            ("Quelles langues peut-on utiliser ?", "Teranga AI propose le français, l'anglais et le wolof."),
            ("Peut-on préparer un voyage au Sénégal ?", "Oui. Demandez des informations sur les lieux, transports, météo, culture et repères pratiques, puis vérifiez les informations susceptibles de changer."),
        ],
        "related": [("senegal", "Guide du Sénégal"), ("france-senegal", "Sénégal ↔ France"), ("meteo-dakar", "Météo Dakar"), ("regions-senegal", "14 régions")],
    },

    "ia-senegal": {
        "title": "IA au Sénégal : intelligence artificielle et usages | Teranga AI",
        "description": "Découvrez comment utiliser l'intelligence artificielle au Sénégal pour apprendre, travailler, créer, traduire et gagner du temps avec Teranga AI.",
        "h1": "IA au Sénégal",
        "intro": "Teranga AI rend l'IA plus simple à découvrir et à utiliser pour les personnes au Sénégal, en France et dans la diaspora.",
        "sections": [
            ("Pour apprendre et travailler", "Rédaction, résumé, traduction, recherche d'idées, analyse de documents, programmation et préparation de projets."),
            ("Pour les usages locaux", "Questions sur Dakar, les régions, les transports, le voyage, la culture, la gastronomie et la vie pratique."),
            ("Plusieurs modèles", "Teranga AI réunit plusieurs modèles d'IA dans une même expérience. Les capacités et informations disponibles peuvent évoluer.")
        ],
        "faq": [
            ("Comment utiliser l'IA au Sénégal ?", "Vous pouvez utiliser Teranga AI en ligne pour poser des questions, rédiger, traduire, analyser et préparer des projets."),
            ("L'IA peut-elle aider pour des questions sur le Sénégal ?", "Oui. Teranga AI est conçu autour de nombreux usages liés au Sénégal ; les informations sensibles ou changeantes doivent être vérifiées.")
        ],
        "related": [("assistant-senegal", "Assistant Sénégal"), ("dakar", "Dakar"), ("france-senegal", "Sénégal ↔ France")]
    },
    "assistant-ia-dakar": {
        "title": "Assistant IA Dakar : transport, sorties, vie pratique",
        "description": "Assistant IA pour Dakar : transport, AIBD, Gorée, météo, sorties, quartiers, restaurants et questions pratiques.",
        "h1": "Assistant IA Dakar",
        "intro": "Posez une question sur Dakar et obtenez une réponse adaptée à votre situation, votre quartier, votre budget ou votre programme.",
        "sections": [
            ("Transport et arrivée", "Demandez comment organiser un trajet depuis AIBD, entre quartiers ou vers Gorée. Les horaires et tarifs se vérifient le jour du déplacement."),
            ("Sorties et tourisme", "Préparez une journée, un week-end ou une visite selon vos centres d'intérêt : culture, plage, gastronomie, histoire ou famille."),
            ("Vie quotidienne", "Demandez une explication, une traduction, une idée de programme ou une aide à la rédaction en lien avec votre quotidien à Dakar.")
        ],
        "faq": [
            ("Que peut-on demander à l'assistant IA de Dakar ?", "Transport, météo, tourisme, sorties, gastronomie, traduction, rédaction et informations pratiques."),
            ("Peut-il préparer une journée à Dakar ?", "Oui. Indiquez votre point de départ, le temps disponible, votre budget et vos centres d'intérêt.")
        ],
        "related": [("dakar", "Dakar"), ("meteo-dakar", "Météo Dakar"), ("restaurants-dakar", "Restaurants Dakar"), ("visiter-goree", "Visiter Gorée")]
    },
    "transport-dakar": {
        "title": "Transport à Dakar : taxis, bus, TER, BRT | Teranga AI",
        "description": "Guide pratique du transport à Dakar : trajets, taxis, bus et déplacements depuis AIBD. Vérifiez les horaires et tarifs actuels.",
        "h1": "Transport à Dakar",
        "intro": "Préparez vos déplacements à Dakar avec Teranga AI. Donnez votre point de départ, votre destination et l'heure souhaitée.",
        "sections": [
            ("Dans Dakar", "Selon le trajet, plusieurs solutions peuvent être pertinentes : taxi, transport collectif ou véhicule avec chauffeur. Les disponibilités et tarifs doivent être vérifiés."),
            ("Depuis AIBD", "L'aéroport Blaise Diagne se trouve à Diass, à l'extérieur de Dakar. Indiquez votre quartier ou destination pour préparer le trajet."),
            ("Vers Gorée", "Pour Gorée, le trajet implique le ferry depuis Dakar. Vérifiez les horaires et conditions de traversée avant de partir.")
        ],
        "faq": [
            ("Comment préparer un trajet à Dakar ?", "Indiquez votre départ, votre destination, l'heure et vos contraintes de budget ou de confort."),
            ("Les prix sont-ils fixes ?", "Non. Les prix et disponibilités peuvent changer ; vérifiez les informations actuelles avant le déplacement.")
        ],
        "related": [("aibd-dakar", "AIBD → Dakar"), ("dakar", "Dakar"), ("meteo-dakar", "Météo Dakar"), ("visiter-goree", "Gorée")]
    },
    "aibd-dakar": {
        "title": "AIBD vers Dakar : comment rejoindre la capitale | Teranga AI",
        "description": "Comment aller de l'aéroport AIBD à Dakar : préparez votre trajet selon votre quartier, votre heure d'arrivée et vos contraintes.",
        "h1": "AIBD → Dakar",
        "intro": "L'aéroport international Blaise Diagne (AIBD) est situé à Diass. Teranga AI peut vous aider à préparer la suite de votre trajet vers Dakar.",
        "sections": [
            ("Avant le départ", "Préparez votre destination exacte à Dakar, votre heure d'arrivée et le nombre de voyageurs. Cela permet de comparer les options pertinentes."),
            ("Arrivée à l'aéroport", "Les services et horaires peuvent évoluer. Vérifiez les informations auprès des opérateurs et sources officielles avant votre trajet."),
            ("Besoin d'un itinéraire", "Demandez à Teranga AI une proposition adaptée à votre quartier, votre budget et votre heure d'arrivée.")
        ],
        "faq": [
            ("AIBD est-il à Dakar ?", "Non. L'aéroport Blaise Diagne est situé à Diass, dans la région de Thiès, à l'extérieur de Dakar."),
            ("Peut-on préparer son trajet avec Teranga AI ?", "Oui. Indiquez votre heure d'arrivée et votre destination finale pour obtenir des repères à vérifier avant le départ.")
        ],
        "related": [("transport-dakar", "Transport Dakar"), ("dakar", "Dakar"), ("meteo-dakar", "Météo Dakar")]
    },
    "visiter-dakar": {
        "title": "Visiter Dakar : que voir et que faire | Teranga AI",
        "description": "Visiter Dakar : quartiers, culture, plages, gastronomie, Gorée et idées de sorties pour organiser votre séjour.",
        "h1": "Visiter Dakar",
        "intro": "Dakar se découvre par ses quartiers, son littoral, sa culture, sa gastronomie et ses lieux historiques.",
        "sections": [
            ("Culture et histoire", "Explorez les lieux culturels et historiques de Dakar et préparez une excursion à Gorée selon votre temps disponible."),
            ("Quartiers et littoral", "Plateau, Médina, Ngor, Almadies et Ouakam offrent des ambiances différentes. Choisissez selon votre activité et votre budget."),
            ("Une journée sur mesure", "Demandez à Teranga AI de construire un programme selon votre heure de départ, votre budget, votre moyen de transport et vos centres d'intérêt.")
        ],
        "faq": [
            ("Que faire à Dakar en une journée ?", "Indiquez vos centres d'intérêt et votre budget ; Teranga AI peut proposer un programme à vérifier selon les horaires du jour."),
            ("Peut-on visiter Gorée depuis Dakar ?", "Oui. Gorée se visite depuis Dakar en ferry ; vérifiez les horaires de traversée avant votre départ.")
        ],
        "related": [("dakar", "Dakar"), ("visiter-goree", "Visiter Gorée"), ("restaurants-dakar", "Restaurants Dakar"), ("transport-dakar", "Transport Dakar")]
    },

    "voyage-senegal": {
        "title": "Voyage au Sénégal : guide, itinéraires et conseils | Teranga AI",
        "description": "Préparez un voyage au Sénégal : Dakar, Gorée, Petite Côte, Casamance, transport, budget, météo et itinéraires.",
        "h1": "Voyage au Sénégal",
        "intro": "Préparez votre séjour selon vos dates, votre budget, votre point d'arrivée et vos envies.",
        "sections": [
            ("Avant de partir", "Préparez votre arrivée, vos déplacements, votre hébergement, votre budget et les lieux à découvrir."),
            ("Où aller", "Dakar et Gorée, la Petite Côte, Saint-Louis, le Sine-Saloum, le Sénégal oriental et la Casamance offrent des expériences différentes."),
            ("Construire son itinéraire", "Indiquez la durée, les villes souhaitées, votre budget et votre moyen de transport pour obtenir un programme adapté.")
        ],
        "faq": [
            ("Peut-on préparer un voyage complet ?", "Oui. Teranga AI peut structurer un itinéraire et distinguer les informations indicatives des données à vérifier."),
            ("Les prix et horaires sont-ils garantis ?", "Non. Les tarifs, horaires, disponibilités et conditions doivent être vérifiés avec des sources récentes.")
        ],
        "related": [("senegal", "Guide du Sénégal"), ("dakar", "Dakar"), ("visiter-goree", "Gorée"), ("regions-senegal", "14 régions")]
    },
    "transport-senegal": {
        "title": "Transport Sénégal : Dakar, AIBD et trajets | Teranga AI",
        "description": "Guide du transport au Sénégal : Dakar, AIBD, taxis, bus et trajets entre les villes.",
        "h1": "Transport au Sénégal",
        "intro": "Préparez vos déplacements en indiquant votre départ, votre destination, votre horaire et vos contraintes.",
        "sections": [
            ("À Dakar", "Taxis, transports collectifs et véhicules avec chauffeur peuvent répondre à des besoins différents. Les prix et disponibilités sont à vérifier."),
            ("Depuis AIBD", "L'aéroport Blaise Diagne est à Diass, dans la région de Thiès. Indiquez votre destination finale pour comparer les options."),
            ("Entre les régions", "Dakar, Thiès, Saint-Louis, Touba, Kaolack, Ziguinchor et les autres villes peuvent être reliées par différentes solutions selon le trajet.")
        ],
        "faq": [
            ("Peut-on demander un trajet précis ?", "Oui. Donnez le départ, la destination, la date, l'heure et votre budget si vous en avez un."),
            ("Les horaires actuels sont-ils disponibles ?", "Pour les informations susceptibles de changer, l'assistant peut rechercher des sources récentes lorsqu'elles sont disponibles.")
        ],
        "related": [("transport-dakar", "Transport Dakar"), ("aibd-dakar", "AIBD → Dakar"), ("dakar", "Dakar"), ("regions-senegal", "Régions")]
    },
    "vie-pratique-senegal": {
        "title": "Vie pratique Sénégal : démarches et services | Teranga AI",
        "description": "Assistant pour la vie pratique au Sénégal : démarches, budget, logement, transport, services et quotidien.",
        "h1": "Vie pratique au Sénégal",
        "intro": "Posez une question sur le quotidien au Sénégal : budget, déplacements, démarches, services, logement ou organisation.",
        "sections": [
            ("Pour les résidents", "Organisez une démarche, comprenez une information, comparez des options ou préparez une liste de tâches."),
            ("Pour les visiteurs et la diaspora", "Préparez votre séjour, vos dépenses, vos déplacements et vos démarches en précisant votre ville et votre situation."),
            ("Informations à vérifier", "Les règles, tarifs, horaires et procédures peuvent changer. Teranga AI distingue les repères généraux des informations qui nécessitent une vérification récente.")
        ],
        "faq": [
            ("Peut-on poser des questions sur toutes les régions ?", "Oui. Les connaissances et pages de Teranga AI couvrent les 14 régions du Sénégal."),
            ("Peut-on demander une traduction ?", "Oui, notamment entre le français, l'anglais et le wolof selon la demande.")
        ],
        "related": [("senegal", "Guide du Sénégal"), ("regions-senegal", "14 régions"), ("france-senegal", "Sénégal ↔ France"), ("diaspora-senegalaise", "Diaspora")]
    },
    "emploi-senegal": {
        "title": "Emploi au Sénégal : travail, CV et candidature | Teranga AI",
        "description": "Aide pour l'emploi au Sénégal : CV, candidature, entretien, recherche d'opportunités et préparation professionnelle.",
        "h1": "Emploi au Sénégal",
        "intro": "Préparez votre recherche d'emploi, améliorez votre CV et organisez vos prochaines étapes.",
        "sections": [
            ("Préparer sa candidature", "Travaillez votre CV, votre lettre de motivation, votre présentation et vos réponses d'entretien."),
            ("Chercher des opportunités", "Définissez votre métier, votre niveau, votre ville et votre secteur pour cibler les recherches pertinentes."),
            ("Pour les jeunes", "Construisez un plan d'action : compétences, candidatures, réseau, formations et projets.")
        ],
        "faq": [
            ("Peut-on améliorer un CV ?", "Oui. Vous pouvez demander une reformulation, une structure plus claire ou une adaptation à une offre."),
            ("Les offres sont-elles vérifiées ?", "Les offres trouvées en ligne doivent être vérifiées sur leur source officielle avant toute candidature.")
        ],
        "related": [("ia-senegal", "IA au Sénégal"), ("assistant-senegal", "Assistant Sénégal"), ("formation-senegal", "Formation")]
    },
    "formation-senegal": {
        "title": "Formation Sénégal : études et compétences | Teranga AI",
        "description": "Formation au Sénégal : compétences numériques, études, métiers, reconversion et apprentissage.",
        "h1": "Formation au Sénégal",
        "intro": "Identifiez les compétences à développer et préparez votre parcours d'apprentissage selon votre objectif.",
        "sections": [
            ("Choisir une formation", "Précisez votre niveau, votre domaine, votre ville, votre budget et le temps disponible."),
            ("Compétences numériques", "IA, programmation, analyse de données, outils numériques et communication peuvent être travaillés progressivement."),
            ("Passer à l'action", "Construisez un programme avec des objectifs, des exercices, un projet concret et des étapes de suivi.")
        ],
        "faq": [
            ("Peut-on préparer un parcours personnalisé ?", "Oui. Indiquez votre niveau, votre objectif et le temps disponible."),
            ("Les programmes sont-ils vérifiés ?", "Les informations actuelles doivent être vérifiées auprès de l'établissement ou de la source officielle.")
        ],
        "related": [("ia-senegal", "IA au Sénégal"), ("assistant-senegal", "Assistant Sénégal"), ("emploi-senegal", "Emploi")]
    },
    "entreprendre-senegal": {
        "title": "Entreprendre au Sénégal : projet et business | Teranga AI",
        "description": "Créer et développer un projet au Sénégal : idée business, budget, offre, clients, partenaires et plan d'action.",
        "h1": "Entreprendre au Sénégal",
        "intro": "Transformez une idée en projet structuré avec un plan simple, des hypothèses claires et des prochaines étapes.",
        "sections": [
            ("De l'idée au projet", "Clarifiez le problème, les clients, la solution, le modèle économique et les premières actions."),
            ("Développer une activité", "Travaillez l'offre, le prix, la marge, la communication, la vente, les paiements et la livraison."),
            ("Trouver des partenaires", "Préparez une présentation courte et identifiez les entreprises, associations, écoles, médias ou acteurs publics pertinents.")
        ],
        "faq": [
            ("Teranga AI peut-il aider à créer un projet ?", "Oui. Vous pouvez partir d'une idée et construire un plan étape par étape."),
            ("Peut-il aider les jeunes entrepreneurs ?", "Oui. Teranga AI peut aider à structurer projets, compétences, opportunités et partenariats.")
        ],
        "related": [("pour-les-entreprises", "Pour les entreprises"), ("partenaires", "Partenaires"), ("emploi-senegal", "Emploi"), ("formation-senegal", "Formation")]
    },

}


# Repères concrets et durables ajoutés aux pages les plus recherchées. Pas de
# prix ni d'horaires précis (ils changent) : seulement ce qui reste vrai d'une
# saison à l'autre, avec un renvoi vers la vérification le jour J.
SEO_PAGE_GUIDES = {
    "voyage-senegal": [
        ("Quand partir", "La saison sèche, de novembre à mai, est la plus confortable : peu de pluie et des soirées "
         "fraîches sur la côte. La saison des pluies (environ de juillet à octobre, plus tôt et plus longue en Casamance) "
         "rend certaines pistes difficiles mais la nature est verte. Les grandes fêtes religieuses changent l'affluence : "
         'voir le <a href="/calendrier-fetes-senegal">calendrier des fêtes</a>.'),
        ("Formalités et santé", "Les ressortissants de l'Union européenne n'ont en général pas besoin de visa pour un "
         "court séjour : vérifiez les conditions à jour auprès de l'ambassade avant de partir. Le vaccin contre la fièvre "
         "jaune est recommandé (exigé si vous arrivez d'un pays où elle circule). Demandez conseil à un médecin pour le "
         'paludisme. Gardez les <a href="/urgences">numéros d\'urgence</a> : police 17, pompiers 18, SAMU 1515.'),
        ("Argent et téléphone", "La monnaie est le franc CFA (XOF), à parité fixe avec l'euro : 1 € = 655,957 FCFA. "
         "Les paiements mobiles (Wave, Orange Money) sont partout ; gardez aussi des petites coupures pour les taxis et "
         "les marchés. Une carte SIM locale s'achète facilement avec un passeport. Heure : UTC+0 toute l'année."),
        ("Itinéraire d'une semaine", "Dakar et Gorée (2 jours), le Lac Rose puis le désert de Lompoul (1 à 2 jours), "
         "Saint-Louis et le parc du Djoudj selon la saison (2 jours), retour par la côte. Sur 10 à 14 jours, ajoutez le "
         "delta du Saloum et la Petite Côte. La Casamance demande un vol ou le bateau de nuit depuis Dakar. "
         'Le <a href="/trip-planner">planificateur de voyage</a> construit un programme jour par jour.'),
        ("Savoir-vivre", "On salue toujours avant de demander quelque chose (« Salaam aleekum »). Tenue couverte dans "
         "les lieux religieux, notamment à Touba. Demandez avant de photographier quelqu'un. Au marché, le prix se "
         "négocie avec le sourire."),
    ],
    "transport-senegal": [
        ("Depuis l'aéroport AIBD", "L'aéroport international Blaise Diagne est à Diass, à environ 45 km du centre de "
         "Dakar, relié par l'autoroute à péage. Options : taxi (prix fixé avant de monter), navettes, voiture avec "
         "chauffeur réservée à l'avance. Le TER relie Dakar à Diamniadio ; son prolongement vers l'aéroport est prévu : "
         'vérifiez s\'il est en service. Détails sur la page <a href="/aibd-dakar">AIBD → Dakar</a>.'),
        ("Se déplacer à Dakar", "Les taxis n'ont pas de compteur : on fixe le prix avant de partir. Les applications "
         "comme Yango ou Heetch affichent un prix à l'avance. Le BRT (bus rapide sur voie réservée) relie le centre à "
         "Guédiawaye, le TER dessert la banlieue jusqu'à Diamniadio, et les bus Dakar Dem Dikk couvrent la ville. "
         "Évitez les heures de pointe sur la corniche et l'autoroute."),
        ("Entre les villes", "Les « sept-places » (taxis-brousse) partent quand ils sont pleins, depuis la gare routière "
         "des Baux Maraîchers à Pikine pour Dakar ; ils sont rapides mais serrés. Les bus et cars sont moins chers et plus "
         "lents. La location de voiture avec chauffeur est la solution la plus simple pour un circuit."),
        ("Vers la Casamance", "Trois options : l'avion vers Ziguinchor ou Cap Skirring, le bateau de nuit "
         "Dakar–Ziguinchor (environ 15 heures, cabines à réserver), ou la route par la Gambie via le pont de Farafenni, "
         "avec passage de frontière."),
        ("Gorée et les îles", "La chaloupe pour Gorée part de la gare maritime de Dakar (environ 20 minutes de "
         "traversée). Les pirogues desservent Ngor depuis la plage, et les îles du Saloum depuis Ndangane, Djiffer ou "
         "Toubacouta : gilet de sauvetage obligatoire, demandez-le."),
    ],
    "meteo-dakar": [
        ("Le climat de Dakar", "Grâce à l'océan et à l'alizé, Dakar est la ville la plus fraîche du pays. De décembre "
         "à avril, les matinées et soirées sont fraîches, avec parfois de la brume de poussière (harmattan). De juillet "
         "à octobre, il fait chaud et humide, avec des averses orageuses souvent courtes mais fortes."),
        ("Mer et plages", "La houle est plus forte sur la côte nord et ouest (Yoff, Ngor, Almadies) que vers la Petite "
         "Côte. Baignez-vous seulement sur les plages surveillées et écoutez les consignes locales : les courants peuvent "
         "être dangereux."),
        ("Prévisions officielles", 'Pour les alertes et prévisions, la référence est l\'ANACIM, l\'agence nationale de '
         'la météorologie (<a href="https://www.anacim.sn" target="_blank" rel="noopener noreferrer">anacim.sn</a>). '
         "Demandez à Teranga AI la météo d'un lieu précis : la réponse s'appuie sur des prévisions du jour."),
    ],
    "emploi-senegal": [
        ("Où chercher", "Les sites d'offres d'emploi sénégalais, les pages carrières des entreprises, LinkedIn et les "
         "groupes professionnels sont les canaux les plus utilisés. Le réseau compte beaucoup : anciens camarades, "
         "associations professionnelles, forums emploi des universités et des écoles."),
        ("Organismes à connaître", "L'Agence nationale pour la promotion de l'emploi des jeunes (ANPEJ), l'Office national de formation "
         "professionnelle (ONFP) et la Délégation générale à l'entrepreneuriat rapide des femmes et des jeunes (DER/FJ) accompagnent les jeunes et les "
         "porteurs de projets. Leurs programmes changent : vérifiez les services actuels sur leur site officiel."),
        ("Un CV qui fonctionne", "Une page, un titre clair (le poste visé), vos compétences concrètes, des résultats "
         "chiffrés, vos langues (français, anglais, wolof…) et un numéro WhatsApp joignable. Adaptez-le à chaque offre : "
         "Teranga AI peut le reformuler à partir de l'annonce."),
        ("Se méfier des arnaques", "Une vraie offre ne demande jamais de payer pour obtenir un entretien, un contrat "
         "ou un visa de travail. Vérifiez l'entreprise (site, adresse, numéro) avant d'envoyer vos pièces d'identité."),
    ],
    "formation-senegal": [
        ("Les grandes voies", "Universités publiques (dont l'Université virtuelle du Sénégal, à distance), écoles et "
         "instituts privés, formation professionnelle et technique, et les instituts supérieurs d'enseignement "
         "professionnel (ISEP) tournés vers les métiers. Le bon choix dépend du métier visé, du budget et de la ville."),
        ("Avant de s'inscrire", "Vérifiez que le diplôme est reconnu par l'État, demandez le taux d'insertion des "
         "anciens élèves, le programme détaillé et les stages proposés. Méfiez-vous des promesses d'emploi garanti."),
        ("Se former en ligne", "Beaucoup de compétences numériques s'apprennent gratuitement : bureautique, "
         "programmation, analyse de données, marketing digital, IA. Un projet concret (site, application, étude) "
         "montré à un employeur vaut souvent plus qu'un certificat seul."),
        ("Financer sa formation", "Bourses de l'État, bourses d'écoles et de fondations, formation en alternance ou "
         "financée par l'employeur. Les appels à candidatures ont des dates limites : notez-les dès leur publication."),
    ],
    "entreprendre-senegal": [
        ("Choisir une forme juridique", "Entreprise individuelle pour démarrer seul, GIE pour un groupe qui veut "
         "produire ou vendre ensemble, SARL ou SUARL pour une société. L'immatriculation donne un NINEA (identifiant "
         "fiscal) et un RCCM ; le guichet unique de l'APIX centralise les formalités à Dakar."),
        ("Tester avant d'investir", "Vendez d'abord à une dizaine de clients réels, même à petite échelle (WhatsApp, "
         "marché, bouche-à-oreille), avant d'acheter du matériel ou de louer un local. Notez chaque vente et chaque "
         "dépense dès le premier jour."),
        ("Se faire payer", "Wave et Orange Money sont les moyens de paiement les plus courants ; un numéro marchand "
         "rassure les clients et sépare l'argent de l'activité de l'argent personnel."),
        ("Se faire accompagner", "Incubateurs, chambres de commerce, programmes de la DER/FJ et du FONGIP (garantie "
         "de crédit) : vérifiez les conditions actuelles sur leurs sites officiels. Teranga AI peut vous aider à "
         "préparer le dossier, le budget et le pitch."),
    ],
    "vie-pratique-senegal": [
        ("Payer au quotidien", "Le franc CFA (XOF) a une parité fixe avec l'euro (1 € = 655,957 FCFA). Wave et Orange "
         "Money servent à payer, envoyer et retirer de l'argent ; les distributeurs sont nombreux en ville, plus rares en "
         "brousse."),
        ("Téléphone et internet", "Les principaux opérateurs sont Orange, Free et Expresso. Une carte SIM s'achète avec "
         "une pièce d'identité ; les forfaits internet se rechargent par code ou par mobile money."),
        ("Santé et urgences", 'Les numéros 17 (police), 18 (pompiers) et 1515 (SAMU) sont gratuits. La page '
         '<a href="/urgences">Urgences</a> reste lisible hors connexion. Pour une pharmacie de garde, demandez localement : '
         "la liste est affichée sur la porte des pharmacies."),
        ("Démarches", "Les règles et tarifs administratifs changent : vérifiez toujours sur le site du service public ou "
         "auprès de l'administration concernée. Teranga AI peut vous aider à préparer la liste des pièces et vos questions."),
    ],
}


# Fiches de la base de connaissances ajoutées aux pages thématiques : contenu
# réel et maillage interne vers /lieux (ou plats pour les pages cuisine).
_TOP_SITES = ["goree", "saint-louis", "djoudj", "niokolo-koba", "saloum", "bassari", "lac-rose", "touba"]
_DAKAR_SITES = ["dakar-renaissance", "musee-civilisations", "ile-de-ngor", "marche-sandaga", "soumbedioune",
                "pointe-des-almadies", "mosquee-divinite", "iles-de-la-madeleine"]
SEO_PAGE_PLACES = {
    "senegal": _TOP_SITES, "regions-senegal": _TOP_SITES, "assistant-senegal": _TOP_SITES, "ia-senegal": _TOP_SITES,
    "france-senegal": _TOP_SITES[:6], "diaspora-senegalaise": _TOP_SITES[:6],
    "dakar": _DAKAR_SITES, "visiter-dakar": _DAKAR_SITES, "assistant-ia-dakar": _DAKAR_SITES[:6],
    "meteo-dakar": _DAKAR_SITES[:4], "transport-dakar": ["goree", "lac-rose", "dakar-renaissance", "ile-de-ngor"],
    "aibd-dakar": ["goree", "lac-rose", "reserve-de-bandia", "saly"],
    "visiter-goree": ["goree", "dakar-renaissance", "musee-civilisations", "iles-de-la-madeleine"],
}
SEO_PAGE_DISHES = {"specialites-senegal", "restaurants-dakar"}


def _seo_extra_html(slug, places=None, dishes=None):
    by_id = {str(p.get("id")): p for p in places or [] if isinstance(p, dict)}
    chosen = [by_id[i] for i in SEO_PAGE_PLACES.get(slug, []) if i in by_id]
    parts = []
    if chosen:
        cards = "".join(
            '<a class="card" href="/lieux/%s"><strong>%s</strong><br><small>%s</small></a>'
            % (quote(str(p["id"])), escape(str(p.get("name", ""))), escape(str(p.get("summary", ""))))
            for p in chosen
        )
        parts.append('<section><h2>Lieux à découvrir</h2><div class="grid">%s</div></section>' % cards)
        if slug == "visiter-goree" and chosen[0].get("history"):
            parts.insert(0, "<section><h2>Histoire de l'île de Gorée</h2><p>%s</p></section>" % escape(str(chosen[0]["history"])))
            if chosen[0].get("access"):
                parts.insert(1, "<section><h2>Comment aller à Gorée</h2><p>%s</p></section>" % escape(str(chosen[0]["access"])))
    if slug in SEO_PAGE_DISHES and dishes:
        items = "".join(
            "<h3>%s</h3><p>%s</p>" % (escape(str(d.get("name", ""))), escape(str(d.get("text", ""))))
            for d in dishes if isinstance(d, dict) and d.get("name")
        )
        parts.append('<section class="faq"><h2>Plats et boissons à goûter</h2>%s</section>' % items)
    return "".join(parts)


def render_seo_page(slug, site_url, places=None, dishes=None):
    page = SEO_PAGES.get(slug)
    if not page:
        return None
    sections = "".join(
        "<section><h2>%s</h2><p>%s</p></section>" % (heading, text)
        for heading, text in list(page["sections"]) + SEO_PAGE_GUIDES.get(slug, [])
    )
    faq_html = ""
    faq_ld = []
    if page.get("faq"):
        items = "".join("<div class='faq'><h3>%s</h3><p>%s</p></div>" % (q, a) for q, a in page["faq"])
        faq_html = "<section><h2>Questions fréquentes</h2>%s</section>" % items
        faq_ld = [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in page["faq"]
        ]
    related = "".join('<a href="/%s">%s</a>' % (s, label) for s, label in page.get("related", []))
    related_html = ""
    if related:
        related_html = 'Voir aussi : %s<a href="/explorer">Explorer</a><a href="/lieux">Lieux</a>' % related
    if slug in {"senegal", "regions-senegal"}:
        source_link = (
            '<p class="source">Source : <a href="https://www.tourisme.gouv.sn/donnees-generales-sur-le-senegal.html" '
            'target="_blank" rel="noopener noreferrer">Ministère du Tourisme du Sénégal</a>.</p>'
        )
    else:
        source_link = (
            '<p class="source">Repères : <a href="https://www.au-senegal.com/" '
            'target="_blank" rel="noopener noreferrer">Au Sénégal</a>.</p>'
        )
    url = "%s/%s" % (site_url, slug)
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "name": page["title"],
                "description": page["description"],
                "url": url,
                "isPartOf": {"@type": "WebSite", "name": "Teranga AI", "url": site_url + "/"},
                "inLanguage": "fr",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": site_url + "/"},
                    {"@type": "ListItem", "position": 2, "name": page["h1"], "item": url},
                ],
            },
        ],
    }
    if faq_ld:
        ld["@graph"].append({"@type": "FAQPage", "mainEntity": faq_ld})
    ld_json = json.dumps(ld, ensure_ascii=True).replace("<", "\\u003c")
    html = """<!doctype html>
<html lang=\"fr\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"robots\" content=\"index,follow\">
<meta name=\"description\" content=\"%(description)s\">
<link rel=\"canonical\" href=\"%(url)s\">
<meta property=\"og:site_name\" content=\"Teranga AI\">
<meta property=\"og:title\" content=\"%(title)s\">
<meta property=\"og:description\" content=\"%(description)s\">
<meta property=\"og:type\" content=\"article\">
<meta property=\"og:locale\" content=\"fr_SN\">
<meta property=\"og:url\" content=\"%(url)s\">
<meta property=\"og:image\" content=\"%(site)s/og.png\">
<meta name=\"twitter:card\" content=\"summary_large_image\">
<meta name=\"twitter:title\" content=\"%(title)s\">
<meta name=\"twitter:description\" content=\"%(description)s\">
<meta name=\"twitter:image\" content=\"%(site)s/og.png\">
<title>%(title)s</title>
<script type=\"application/ld+json\">%(ld)s</script>
%(head)s
</head>
<body>%(header)s<main>
<div class=\"related\">%(related)s<button id=\"share-page\" class=\"share-page\" type=\"button\">Partager</button></div><script src=\"%(share_js)s\" defer></script>
<article>
<div class=\"kicker\">Sénégal · Teranga AI</div>
<h1>%(h1)s</h1>
<p class=\"intro\">%(intro)s</p>
%(sections)s
%(faq)s
<div class=\"ctaBox\"><strong>Une question précise ?</strong><p>Réponse courte, photo et carte quand le lieu est connu.</p><a class=\"cta primary\" href=\"/\">Ouvrir Teranga AI</a></div>
%(source)s
</article>
</main>%(footer)s</body></html>""" % {
        "description": page["description"],
        "url": url,
        "title": page["title"],
        "site": site_url,
        "ld": ld_json,
        "related": related_html,
        "share_js": asset_url("share-page.js"),
        "h1": page["h1"],
        "intro": page["intro"],
        "sections": sections + _seo_extra_html(slug, places, dishes),
        "faq": faq_html,
        "source": source_link,
        "head": HEAD_ASSETS,
        "header": site_header(),
        "footer": site_footer(),
    }
    return Response(html, mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})


REGION_SEO_NAMES = ["Dakar","Diourbel","Fatick","Kaffrine","Kaolack","Kédougou","Kolda","Louga","Matam","Saint-Louis","Sédhiou","Tambacounda","Thiès","Ziguinchor"]

def region_slug(name):
    import unicodedata
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return "-".join(value.split())

REGION_CONTENT = {
    "Dakar": ("capitale et région côtière", "Dakar, Plateau, Gorée, Ngor, Almadies", "voyage, culture, transport, gastronomie et sorties"),
    "Diourbel": ("région du centre du Sénégal", "Diourbel, Touba et Mbacké", "culture, patrimoine, déplacements et découverte du centre"),
    "Fatick": ("région entre Sine et Saloum", "Fatick, Foundiougne et les îles du Saloum", "Sine-Saloum, nature, villages, patrimoine et itinéraires"),
    "Kaffrine": ("région du centre", "Kaffrine et les localités du bassin arachidier", "routes, vie locale, culture et découverte du centre"),
    "Kaolack": ("carrefour commercial du centre-ouest", "Kaolack et le Saloum", "marchés, transport, culture et itinéraires"),
    "Kédougou": ("région du sud-est", "Kédougou, pays Bassari et reliefs du Sénégal oriental", "nature, randonnée, patrimoine et voyage"),
    "Kolda": ("région de Haute-Casamance", "Kolda et les territoires de Haute-Casamance", "culture, nature, gastronomie et déplacements"),
    "Louga": ("région du nord-ouest", "Louga et le Ferlo", "culture, routes, découverte du nord et étapes"),
    "Matam": ("région du nord-est le long du fleuve Sénégal", "Matam et la vallée du fleuve", "culture, fleuve, déplacements et patrimoine"),
    "Saint-Louis": ("région historique du nord", "Saint-Louis, langue de Barbarie et vallée du fleuve", "patrimoine, culture, nature et voyage"),
    "Sédhiou": ("région de Casamance", "Sédhiou et la moyenne Casamance", "culture, nature, fleuve et découverte de la Casamance"),
    "Tambacounda": ("région du Sénégal oriental", "Tambacounda et les portes du Sénégal oriental", "nature, routes, parcs et itinéraires"),
    "Thiès": ("région de l'ouest autour de la Petite Côte", "Thiès, Tivaouane, Mbour et la Petite Côte", "plages, transport, patrimoine et tourisme"),
    "Ziguinchor": ("région de Basse-Casamance", "Ziguinchor, Oussouye, Cap Skirring et la Casamance", "plages, culture, nature, gastronomie et voyage"),
}

def _region_dossier_html(region_name, knowledge_regions):
    """Identité, géographie, économie, culture et cuisine de la région (base de connaissances)."""
    region = next((r for r in knowledge_regions or [] if isinstance(r, dict) and r.get("name") == region_name), None)
    if not region:
        return ""
    dossier = region.get("regional_dossier") or {}
    parts = []
    intro = " ".join(str(x) for x in (dossier.get("identity"), dossier.get("geography")) if x)
    if intro:
        capital = dossier.get("capital_regionale")
        extra = f" Capitale régionale : {escape(str(capital))}." if capital else ""
        departments = region.get("departments") or []
        if departments:
            extra += " Départements : " + escape(", ".join(map(str, departments))) + "."
        parts.append(f"<section><h2>La région en bref</h2><p>{escape(intro)}{extra}</p></section>")
    rows = []
    for label, values in (("Économie", dossier.get("economy")), ("Culture", dossier.get("culture")),
                          ("Thèmes de voyage", region.get("themes")), ("À ne pas manquer", region.get("highlights"))):
        if values:
            rows.append(f"<li><strong>{label} :</strong> {escape(', '.join(map(str, values)))}.</li>")
    if rows:
        parts.append(f"<section><h2>Économie, culture et incontournables</h2><ul>{''.join(rows)}</ul></section>")
    foods = region.get("foods") or dossier.get("foods") or []
    if foods:
        parts.append(
            f"<section><h2>Que manger dans la région {escape(region_name)} ?</h2>"
            f"<p>Spécialités à goûter : {escape(', '.join(map(str, foods)))}. Demandez à Teranga AI où les trouver et comment elles se préparent.</p></section>"
        )
    return "".join(parts)


def render_region_page(region_name, site_url, knowledge_places=None, knowledge_regions=None):
    if region_name not in REGION_SEO_NAMES:
        return None
    slug = region_slug(region_name)
    url = f"{site_url}/regions/{slug}"
    descriptor, places, topics = REGION_CONTENT.get(
        region_name,
        ("région du Sénégal", region_name, "voyage et informations pratiques"),
    )
    title = f"Région {region_name} au Sénégal : guide pratique | Teranga AI"
    description = f"Guide de la région de {region_name} au Sénégal : {places}. Repères pour {topics}."
    if len(description) > 160:
        description = description[:157].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": title, "description": description, "url": url, "inLanguage": "fr"},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Accueil", "item": site_url + "/"},
                {"@type": "ListItem", "position": 2, "name": "14 régions du Sénégal", "item": site_url + "/regions-senegal"},
                {"@type": "ListItem", "position": 3, "name": region_name, "item": url}
            ]}
        ]
    }
    # Fiches de la base de connaissances : maillage interne vers /lieux/<id>.
    region_places = [p for p in knowledge_places or [] if p.get("id") and p.get("region") == region_name]
    places_section = ""
    if region_places:
        cards = "".join(
            f'<a class="card" href="/lieux/{quote(str(p["id"]))}"><strong>{escape(str(p.get("name", "")))}</strong>'
            f'<br><small>{escape(str(p.get("summary", "")))}</small></a>'
            for p in region_places
        )
        places_section = f'<section><h2>Lieux à visiter dans la région {escape(region_name)}</h2><div class="grid">{cards}</div></section>'
        ld["@graph"].append({
            "@type": "ItemList",
            "name": f"Lieux à visiter : {region_name}",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": f"{site_url}/lieux/{quote(str(p['id']))}", "name": p.get("name", "")}
                for i, p in enumerate(region_places)
            ],
        })
    dossier_section = _region_dossier_html(region_name, knowledge_regions)
    ld_json = json.dumps(ld, ensure_ascii=True).replace("<", "\\u003c")
    related = "".join(
        f'<a href="/regions/{region_slug(name)}">{name}</a>'
        for name in REGION_SEO_NAMES if name != region_name
    )
    html = f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow"><meta name="description" content="{description}">
<link rel="canonical" href="{url}"><meta property="og:site_name" content="Teranga AI"><meta property="og:title" content="{title}">
<meta property="og:description" content="{description}"><meta property="og:type" content="article"><meta property="og:url" content="{url}">
<meta property="og:image" content="{site_url}/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{description}"><meta name="twitter:image" content="{site_url}/og.png">
<title>{title}</title><script type="application/ld+json">{ld_json}</script>
{HEAD_ASSETS}
</head>{body_tag(region_name)}{site_header('/regions-senegal')}<main><p class="related"><a href="/regions-senegal">← Les 14 régions du Sénégal</a></p><article><small>TERANGA AI · GUIDE RÉGIONAL</small>
<h1>Région {region_name}</h1><p class="muted">{region_name} est une {descriptor}. Repères de lieux : {places}.</p>
<section><h2>Que découvrir ?</h2><p>Cette page sert de point de départ pour {topics}. Demandez à Teranga AI un itinéraire adapté à vos dates, votre budget et votre moyen de transport.</p></section>
{dossier_section}{places_section}<section><h2>Informations pratiques</h2><p>Transport, météo, horaires, prix et conditions peuvent changer. Pour ces données, indiquez une date et vérifiez les sources récentes avant de prendre une décision.</p></section>
<section><h2>Préparer votre étape</h2><p>Précisez votre ville de départ, votre destination, la durée du séjour et vos centres d'intérêt pour obtenir une proposition plus utile.</p></section>
<div class="actions"><a class="cta" href="/trip-planner?region={slug}">Planifier un voyage</a><a class="cta" href="/explorer?region={slug}">Explorer les lieux</a></div>
<section><h2>Autres régions</h2><div class="related">{related}</div></section>
</article></main>{site_footer()}</body></html>'''
    return Response(html, mimetype="text/html", headers={"Cache-Control":"public, max-age=3600"})
