# 🇸🇳 Teranga AI

**L’assistant IA pour découvrir, comprendre et explorer le Sénégal.**

Teranga AI combine une conversation courte et naturelle avec des données structurées sur le Sénégal : régions, villes, lieux, culture, histoire, cuisine et informations pratiques.

🌐 **Démo :** https://teranga-ai-1.onrender.com
📦 **Dépôt :** https://github.com/barouu78-wq/teranga-ai

## ✨ Ce que fait Teranga AI

- 🗺️ **Explorer le Sénégal** — 14 régions et des fiches de lieux avec coordonnées et liens cartographiques.
- 📸 **Photos de lieux** — recherche d’images Wikimedia Commons avec proxy same-origin pour fiabiliser l’affichage.
- 🍲 **Cuisine sénégalaise** — spécialités et repères par région ou quartier.
- 🏛️ **Culture & histoire** — personnalités, patrimoine, traditions et repères historiques.
- 🤖 **Assistant IA** — réponses en français, anglais, wolof et pulaar.
- 🔎 **Recherche web ciblée** — utilisée surtout pour les informations susceptibles de changer : météo, horaires, prix, événements, transports, etc.
- 📈 **SEO** — pages guides dédiées au Sénégal, aux régions, à Gorée, à la météo et aux spécialités.
- 🧪 **Tests + CI** — tests automatisés avec GitHub Actions.

## 🧭 Explorer

La page /explorer présente les lieux disponibles sous forme de cartes : résumé, photos, région, coordonnées et accès direct à une question Teranga.

Quelques entrées couvertes : Gorée, Saint-Louis, Djoudj, Niokolo-Koba, Sine-Saloum, pays Bassari, Touba, Dindéfello, Joal-Fadiouth, Cap Skirring, Dakar, la Petite Côte et la Casamance.

## 🏗️ Architecture

Le projet reste volontairement simple :

    teranga-ai/
    ├── app.py                         # application Flask + orchestration
    ├── services/
    │   ├── seo.py                     # pages et contenu SEO
    │   └── images.py                  # recherche et cache des images Wikimedia
    ├── templates/
    │   └── home.html                  # interface web principale
    ├── data/
    │   └── senegal_knowledge.json     # données structurées du Sénégal
    ├── tests/
    │   └── test_app.py                # tests applicatifs
    ├── .github/workflows/tests.yml    # CI GitHub Actions
    ├── render.yaml                    # déploiement Render
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

## ☁️ Déploiement Render

Le fichier render.yaml décrit le service web et utilise Gunicorn.

Les secrets, notamment OPENAI_API_KEY, restent configurés dans Render et ne sont jamais commités.

## 🔐 Configuration

Voir .env.example pour les variables attendues :

- OPENAI_API_KEY
- OPENAI_MODEL
- SECRET_KEY
- TRUST_PROXY
- ALLOWED_ORIGINS

## 🎯 Vision

Teranga AI évolue vers un **guide numérique du Sénégal** : un point d’entrée unique pour explorer un lieu, comprendre son histoire, trouver sa cuisine, voir des photos et poser une question pratique.

Les prochaines évolutions visent notamment à approfondir l’Explorer, la recherche géographique, les itinéraires et les fiches lieux.

## 📣 Partager le projet

Le projet est public et peut être testé directement depuis la démo. Pour contribuer, ouvrir une issue ou une pull request sur GitHub.
