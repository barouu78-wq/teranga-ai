# Fiche Google Play — Teranga AI

Textes prêts à copier dans la Play Console (**Présence sur le Play Store → Fiche principale**),
puis réponses aux questionnaires obligatoires. Les limites de caractères de Google sont vérifiées
par `tests/test_play_listing.py`.

## 1. Fiche principale

**Nom de l'application** (30 max) :

```
Teranga AI – Guide du Sénégal
```

### Français (langue par défaut : fr-FR)

**Description courte** (80 max) :

```
Ton guide du Sénégal : histoire des lieux, météo, itinéraires, marchés, wolof.
```

**Description complète** (4000 max) :

```
Teranga AI est ton guide de poche pour le Sénégal. Pose tes questions en français, en anglais ou en wolof et reçois des réponses claires, adaptées au pays.

🧭 UN GUIDE LOCAL QUI RACONTE
Gorée, Saint-Louis, Touba, le Lac Rose, le Monument de la Renaissance africaine, les Îles de la Madeleine… Teranga AI te raconte l'histoire de chaque lieu, ce qu'il faut y voir, le meilleur moment pour y aller et les bons usages à respecter. Plus de 80 lieux ont leur fiche détaillée.

🛍️ NÉGOCIER AU MARCHÉ
Sandaga, Kermel, HLM, Soumbédioune : où aller selon ce que tu cherches, comment négocier avec respect, et les phrases utiles en wolof (« Ñaata la ? », « Wàññi ko tuuti »…). Tu peux même t'entraîner : Teranga joue le vendeur.

🌦️ MÉTÉO EN DIRECT
Prévisions réelles pour Dakar, Ziguinchor, Saint-Louis, Kédougou et toutes les régions, pour aujourd'hui et les jours suivants.

🗺️ PLANIFICATEUR DE VOYAGE
Indique tes dates, tes envies et ton budget : Teranga construit ton itinéraire jour par jour, avec carte et budget indicatif. Tu peux le modifier et le partager.

📸 PHOTOS ET CARTES
Photos des lieux, cartes et fiches pratiques pour préparer chaque sortie.

🚀 POUR LES PROJETS AUSSI
Tu veux lancer une activité au Sénégal ? Teranga te propose un plan d'action, des étapes et des pistes d'opportunités.

✨ PENSÉ POUR TOI
• Français, anglais et wolof
• Mode clair le jour, mode nuit le soir, touches festives pour la Tabaski, la Korité, le Magal et le 4 avril
• Guides déjà consultés lisibles hors connexion
• Sans compte ni inscription

ℹ️ À SAVOIR
Teranga AI utilise l'intelligence artificielle : vérifie toujours les informations importantes (prix, horaires, formalités, santé) auprès des sources officielles. Tu peux signaler une réponse inappropriée directement depuis l'application.
```

### Anglais (ajouter la langue en-US ou en-GB)

**Short description** (80 max):

```
Your Senegal guide: history of places, weather, trips, markets and Wolof tips.
```

**Full description** (4000 max):

```
Teranga AI is your pocket guide to Senegal. Ask in English, French or Wolof and get clear answers tailored to the country.

🧭 A LOCAL GUIDE THAT TELLS STORIES
Gorée, Saint-Louis, Touba, Lake Retba (Lac Rose), the African Renaissance Monument, the Madeleine Islands… Teranga AI tells you the history of each place, what to see, the best time to go and the customs to respect. More than 80 places have a detailed guide.

🛍️ BARGAINING AT THE MARKET
Sandaga, Kermel, HLM, Soumbédioune: where to go for what you need, how to bargain respectfully, and useful Wolof phrases. You can even practise — Teranga plays the seller.

🌦️ LIVE WEATHER
Real forecasts for Dakar, Ziguinchor, Saint-Louis, Kédougou and every region, for today and the coming days.

🗺️ TRIP PLANNER
Enter your dates, interests and budget: Teranga builds a day-by-day itinerary with a map and an indicative budget. Edit it and share it.

📸 PHOTOS AND MAPS
Photos of places, maps and practical guides to prepare every outing.

✨ MADE FOR YOU
• English, French and Wolof
• Light theme by day, night theme in the evening
• Guides you already opened work offline
• No account, no sign-up

ℹ️ GOOD TO KNOW
Teranga AI uses artificial intelligence: always check important information (prices, schedules, formalities, health) with official sources. You can report an inappropriate answer directly in the app.
```

### Éléments graphiques (dossier `docs/google-play/`)

| Élément | Fichier | Format exigé |
|---|---|---|
| Icône | `static/icon-512.png` (aussi servi sur teranga-ai.fr/icon-512.png) | 512 × 512 PNG |
| Image de présentation | `image-de-presentation-1024x500.png` | 1024 × 500 |
| Captures téléphone (2 à 8) | `capture-1-accueil.png` … `capture-4-fiche-lieu.png` | 780 × 1560, rapport 2:1 max |

### Coordonnées

- **Catégorie** : Voyages et infos locales
- **E-mail** : l'adresse de contact choisie (la même que `CONTACT_EMAIL` sur Render)
- **Site Web** : https://teranga-ai.fr
- **Règles de confidentialité** : https://teranga-ai.fr/confidentialite

## 2. Contenu de l'application (Règles et programmes → Contenu de l'appli)

**Accès à l'application** : « Toutes les fonctionnalités sont disponibles sans accès spécial » (aucun compte).

**Annonces** : Non, l'application ne contient pas d'annonces.

**Public cible et contenu** : **18 ans et plus** uniquement. À la question « l'application pourrait-elle
attirer les enfants ? » : **Non**. (Cocher des tranches d'âge enfants imposerait le programme Familles.)

**Applis d'actualités / gouvernementales / santé / finances** : Non pour toutes.

**Classification du contenu (questionnaire IARC)** :
- Catégorie : **Référence, actualités ou éducation**
- Violence, sexe, langage grossier, drogues, jeux d'argent : **Non** partout
- Les utilisateurs peuvent-ils communiquer ou échanger du contenu entre eux ? **Non** (le partage d'une
  réponse se fait par un simple lien)
- Contenu généré par IA : **Oui** — l'application génère du texte avec l'IA, et un bouton « Signaler »
  permet de signaler une réponse
- Partage de la position de l'utilisateur : **Non**
- Achats numériques : **Non**

## 3. Sécurité des données (formulaire « Data safety »)

Réponses fidèles au fonctionnement réel du site (voir aussi la page /confidentialite).

- **L'application collecte-t-elle ou partage-t-elle des données ?** Oui (collecte).
- **Chiffrement en transit** : Oui (HTTPS partout).
- **Suppression des données** : pas de compte ; l'historique est stocké sur l'appareil et s'efface avec
  le bouton « Nouveau » ou en vidant les données de l'application. Pour une demande : e-mail de contact.

| Type de données | Collecté | Partagé | Éphémère | Obligatoire | Finalités |
|---|---|---|---|---|---|
| Activité dans l'appli → **Autres contenus générés par l'utilisateur** (questions posées) | Oui | Non* | Oui | Oui | Fonctionnalités de l'appli |
| Audio → **Enregistrements vocaux** (si la voix est utilisée) | Oui | Non* | Oui | Non (optionnel) | Fonctionnalités de l'appli |
| Identifiants de l'appareil ou autres → **identifiant aléatoire** (cookie technique) | Oui | Non | Non | Oui | Prévention des fraudes, sécurité |
| Infos et performances de l'appli → **Journaux de plantage / diagnostics** (journaux serveur) | Oui | Non | Non | Oui | Analyses, sécurité |

\* Envoyer les questions et la voix à OpenAI pour produire la réponse est un traitement par un
**prestataire de services** : Google ne le compte pas comme un « partage ».

**Ne pas déclarer** : position (la météo utilise le nom du lieu demandé, jamais la position du téléphone),
contacts, photos de l'utilisateur, informations financières, identifiants publicitaires.

Si la mesure d'audience est activée (`ANALYTICS_SCRIPT_URL`), ajouter
**Activité dans l'appli → Interactions avec l'appli** (finalité : Analyses), collectée sans profilage.

## 4. Lien de vérification Android

Une fois l'empreinte SHA-256 connue (fichier `assetlinks.json` du paquet PWABuilder, puis aussi
l'empreinte « Clé de signature d'application » de la Play Console → Intégrité de l'application),
ajouter sur Render :

- `ANDROID_APP_PACKAGE` = le Package ID (ex. `fr.terangaai.app`)
- `ANDROID_CERT_SHA256` = les empreintes séparées par une virgule

Vérifier ensuite : https://teranga-ai.fr/.well-known/assetlinks.json
