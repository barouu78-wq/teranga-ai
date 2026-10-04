# 🇸🇳 Teranga AI

**L’assistant IA pour découvrir, comprendre et explorer le Sénégal.**

Teranga AI combine une conversation courte et naturelle avec des données structurées sur le Sénégal : régions, villes, lieux, culture, histoire, cuisine et informations pratiques.

🌐 **Site :** https://teranga-ai.fr
📦 **Dépôt :** https://github.com/barouu78-wq/teranga-ai

## ✨ Ce que fait Teranga AI

- 🗺️ **Explorer le Sénégal** — 14 régions et des fiches de lieux avec coordonnées et liens cartographiques.
- 📸 **Photos de lieux** — Google Images (Custom Search) en source principale, Wikimedia Commons en secours via un proxy same-origin sécurisé.
- 🍲 **Cuisine sénégalaise** — spécialités et repères par région ou quartier.
- 🏛️ **Culture & histoire** — personnalités, patrimoine, traditions et repères historiques.
- 🤖 **Assistant IA** — réponses en français, anglais et wolof (le pulaar reste compris côté serveur mais n’est plus proposé dans le sélecteur).
- 🎙️ **Voix** — transcription, synthèse vocale et conversation vocale temps réel.
- 🧳 **Planificateur de voyage** — itinéraires et informations pratiques (/trip-planner).
- 🔎 **Recherche web ciblée** — utilisée surtout pour les informations susceptibles de changer : météo, horaires, prix, événements, transports, etc.
- 📈 **SEO** — pages guides dédiées au Sénégal, aux régions, à Gorée, à la météo et aux spécialités.
- 🧪 **Tests + CI** — tests automatisés avec GitHub Actions.

## 🧭 Explorer

La page /explorer présente les lieux disponibles sous forme de cartes : résumé, photos, région, coordonnées et accès direct à une question Teranga.

Quelques entrées couvertes : Gorée, Saint-Louis, Djoudj, Niokolo-Koba, Sine-Saloum, pays Bassari, Touba, Dindéfello, Joal-Fadiouth, Cap Skirring, Dakar, la Petite Côte et la Casamance.

## 🏗️ Architecture

Le projet reste volontairement simple :

    teranga-ai/
    ├── app.py                         # application Flask : configuration et câblage des routes
    ├── wsgi.py                        # point d’entrée Gunicorn
    ├── routes/                        # routes HTTP (chat, voix, images, explorer, SEO…)
    ├── services/                      # logique métier et sécurité (rate limit, CSRF, images…)
    ├── templates/                     # interface web (home.html, partenaires, opportunités)
    ├── data/                          # données structurées du Sénégal
    ├── tests/                         # tests pytest
    ├── .github/workflows/tests.yml    # CI GitHub Actions
    ├── Dockerfile                     # image de production (Coolify)
    ├── render.yaml                    # déploiement Render (alternatif)
    ├── requirements.txt               # dépendances production
    └── requirements-dev.txt           # dépendances de développement

Le découpage de app.py est progressif afin de réduire le risque de régression sur les routes existantes.

## 🚀 Développement local

1. Créer un environnement virtuel.
2. Installer les dépendances :

       pip install -r requirements-dev.txt

3. Copier .env.example vers .env.
4. Renseigner OPENAI_API_KEY.
5. Lancer :

       python app.py

## 🧪 Tests

    pytest -q

La CI exécute automatiquement les tests sur les pushes vers main, les pull requests et peut être lancée manuellement.

## ☁️ Déploiement

La production utilise le Dockerfile (Coolify) avec Gunicorn. render.yaml reste disponible comme alternative.

En production, définir TERANGA_ENV=production : l’application refuse alors de démarrer sans SECRET_KEY d’au moins 32 caractères et n’accepte que les hôtes listés dans TRUSTED_HOSTS.

Avec plusieurs workers ou instances, configurer REDIS_URL pour partager la limitation de débit ; sans Redis, chaque worker compte séparément (mémoire bornée).

Les secrets, notamment OPENAI_API_KEY, restent configurés sur l’hébergeur et ne sont jamais commités.

## 🔐 Configuration

Voir .env.example pour les variables attendues :

- OPENAI_API_KEY (obligatoire)
- TERANGA_ENV, SECRET_KEY, TRUSTED_HOSTS (production)
- ALLOWED_ORIGINS, SITE_URL, TRUST_PROXY
- OPENAI_MODEL
- REDIS_URL
- GOOGLE_API_KEY, GOOGLE_CSE_ID (images Explorer)
- quotas optionnels : TRIP_*, PRACTICAL_*, EXPLORER_IMAGE_*
- ANALYTICS_SCRIPT_URL, ANALYTICS_SITE_ID : mesure d’audience sans cookie (Plausible, Umami), désactivée par défaut

## 🤝 Widget partenaire

Un site partenaire (hôtel, agence, média…) ajoute une ligne :

```html
<script src="https://teranga-ai.fr/widget.js" data-partner="mon-hotel" data-lang="fr" defer></script>
```

Un bouton « Une question sur le Sénégal ? » ouvre Teranga AI sur teranga-ai.fr (petite fenêtre sur ordinateur, nouvel onglet sur mobile). Le widget ne lit ni ne transmet aucune donnée du site partenaire ; `data-partner` arrive en `utm_source` pour la mesure d'audience. Options : `data-lang` (fr, en, wo), `data-position` (right, left), `data-question` (question pré-remplie).

## 🎯 Vision

Teranga AI évolue vers un **guide numérique du Sénégal** : un point d’entrée unique pour explorer un lieu, comprendre son histoire, trouver sa cuisine, voir des photos et poser une question pratique.

Les prochaines évolutions visent notamment à approfondir l’Explorer, la recherche géographique, les itinéraires et les fiches lieux.

## 📣 Partager le projet

Le projet est public et peut être testé directement depuis la démo. Pour contribuer, ouvrir une issue ou une pull request sur GitHub.

<!-- Render redeploy trigger: 2026-09-26 -->
<!-- Clean redeploy trigger: 2026-09-29 -->