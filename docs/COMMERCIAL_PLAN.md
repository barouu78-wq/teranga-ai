# Plan commercial — Teranga AI

## Objectif
Développer une présence identifiable de Teranga AI au Sénégal, en France et auprès de la diaspora sénégalaise.

## 1. Présence propriétaire
- Site officiel : https://teranga-ai.fr/
- Pages d'entrée : /assistant-senegal, /dakar, /senegal, /france-senegal, /diaspora-senegalaise
- Pages commerciales : /pour-les-entreprises, /partenaires (en ligne et présentes dans le sitemap)
- Presse : /presse
- Kit média : /media-kit
- Sitemap et pages SEO : indexables par les moteurs de recherche ; pages internationales en anglais, espagnol, allemand et italien.
- Outils démontrables : /explorer (lieux et photos), /trip-planner (itinéraires et infos pratiques), conversation vocale, /opportunities et /partners (Teranga Projet pour les jeunes porteurs de projets).

## 2. Sénégal — distribution
Priorité aux canaux légitimes et pertinents :
- SenPages : créer une fiche/service et utiliser une description cohérente.
- Go Africa Online : créer la présence professionnelle.
- Médias reconnus : proposer des sujets utiles, démonstrations et interviews, sans envoi massif.
- Écosystèmes tech, tourisme, hôtellerie, restauration, écoles et associations.
- Créateurs de contenu Sénégal : proposer une démonstration ou un test, pas une publication artificielle.

## 3. France — distribution
- Réseaux et associations de la diaspora sénégalaise.
- Médias et newsletters franco-sénégalais.
- Réseaux entrepreneuriaux et numériques.
- Créateurs spécialisés Sénégal, voyage Afrique et diaspora.
- Référencement sur les plateformes pertinentes, avec une fiche distincte seulement lorsque les règles de la plateforme l'autorisent.

## 4. Messages commerciaux
### Présentation 1 phrase
Teranga AI est un assistant numérique consacré au Sénégal, accessible depuis le Sénégal et la France, en français, anglais et wolof (le pulaar est en cours d'amélioration).

### Message partenaire
Bonjour,
Nous développons Teranga AI, un assistant numérique consacré au Sénégal. Il aide à répondre aux questions pratiques sur Dakar, les régions, le voyage, les transports, la météo, la culture et la vie quotidienne.
Nous cherchons des partenaires au Sénégal et en France : médias, tourisme, entreprises, écoles, créateurs et réseaux de la diaspora.
Nous pouvons proposer une démonstration ou un petit pilote.
Site : https://teranga-ai.fr/

### Message média
Bonjour,
Je vous contacte au sujet de Teranga AI, un assistant numérique consacré au Sénégal. Le service permet de poser des questions sur le pays en français, anglais et wolof, à l'écrit comme à la voix.
Nous pouvons fournir une démonstration, une interview ou un sujet autour de l'IA appliquée aux usages pratiques du Sénégal.
Site : https://teranga-ai.fr/
Kit média : https://teranga-ai.fr/media-kit

## 5. Règles
- Pas de spam.
- Pas de faux avis.
- Pas de faux partenaires.
- Pas de faux chiffres d'utilisateurs.
- Pas d'affiliation officielle annoncée sans accord écrit.
- Un lien officiel Teranga AI doit être utilisé.
- Adapter le message à chaque média, entreprise ou communauté.

## 6. Mesure
Outil : mesure d'audience sans cookie (Plausible ou Umami), activable par la variable d'environnement `ANALYTICS_SCRIPT_URL` (voir README). Sans elle, aucun suivi n'est chargé.

Suivre chaque mois :
- visites du site ;
- provenance Sénégal / France / autres ;
- pages d'entrée ;
- clics vers l'assistant ;
- demandes partenaires ;
- mentions médias ;
- backlinks réellement publiés ;
- conversions issues des campagnes.

## 7. Prochaines étapes
1. Activer la mesure d'audience en production et établir une première base mensuelle.
2. Construire une liste de prospection qualifiée Sénégal + France à partir du modèle `docs/prospection_modele.csv` (canal, audience et sa source, contact public, proposition, date, statut, prochaine action). N'y inscrire que des contacts publics réellement vérifiés.
3. Démonstration de 5 minutes prête : `docs/DEMO.md` (chat, voix en wolof, planificateur, fiches lieux, partage, widget).
4. Proposer un pilote à 2 ou 3 acteurs du tourisme (hôtel, agence, restaurant) avec des indicateurs définis à l'avance.

## 8. Feuille de route produit
- Court terme : stabilité et sécurité en production (Redis partagé, `TERANGA_ENV=production`, quotas), mesure d'audience.
- Intelligence : base de connaissances portée à 56 lieux sourcés (Kaolack, Mbacké, Fathala, Kafountine, Mlomp, musée Théodore-Monod, Manufactures de Thiès ajoutés) ; repères d’orthographe officielle et formules sûres pour le wolof ; à faire : relecture du wolof de l’interface par un locuteur natif ; remettre le pulaar dans l'interface quand sa qualité est validée.
- Produit : fiches indexables par lieu (/lieux, fait) ; partage des réponses par lien signé (/partage, fait) ; itinéraires enrichis avec les lieux vérifiés de la base et liens vers leurs fiches (fait).
- Partenaires : widget à une ligne (`/widget.js`, fait) à proposer lors des pilotes ; chaque partenaire est mesuré via `utm_source`.
