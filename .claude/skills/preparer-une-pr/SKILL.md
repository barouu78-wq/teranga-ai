---
name: preparer-une-pr
description: Préparer, vérifier et publier une PR sur Teranga AI (contrôles, pièges connus, description en français). À utiliser avant chaque commit, PR ou fusion, et pour traiter les mises à jour Dependabot.
---

# Préparer une PR Teranga AI

## 1. Contrôles (le CI refait exactement les mêmes)

```bash
ruff check --select E9,F63,F7,F82,F401,F811,F841 .
node --check static/home.js static/trip-planner.js
bandit -q -r app.py routes services -ll
OPENAI_API_KEY=test-key python -m pytest -q --cov=app --cov=routes --cov=services --cov-fail-under=85
OPENAI_API_KEY=test-key python -m pytest -q tests/e2e
```

Utiliser `python -m pytest` (le `pytest` seul peut venir d'un autre Python). Après toute modification du
contexte de l'IA : `tests/test_ai_bench*.py` et `tests/test_knowledge_coverage.py`.

## 2. Pièges déjà rencontrés

- **Avant `git add -A`, lire `git status`.** Un fichier temporaire (`.coverage`) a déjà été ajouté par erreur ;
  il est maintenant dans `.gitignore`.
- **Un test échoue seulement dans la suite complète ?** C'est souvent la limite de débit : donner au nouveau test sa
  propre adresse (`environ_base={"REMOTE_ADDR": "203.0.113.x"}`).
- **bandit** : une alerte volontaire se marque `# nosec Bxxx` seul sur la ligne, et la raison dans un commentaire
  **au-dessus** (les mots après `# nosec` sont lus comme des numéros de test).
- **Fichiers servis par le service worker** (`site.css`, `home.js`, `trip-planner.js`…) : changer `VERSION` dans
  `static/sw.js`.
- **Une branche créée avant une autre fusion** peut entrer en conflit : fusionner `origin/main` dans la branche
  (jamais de réécriture d'historique), refaire les contrôles, puis pousser.
- **Numéro de PR** : prendre l'URL renvoyée à la création (`.../pull/NNN`), ne jamais le deviner.
- **Secrets** : ne jamais écrire, demander ni afficher une clé ; ne pas toucher aux fichiers de signature Android.

## 3. Publier

- Description en français : `## Résumé` puis `## Tests` (et `## Sources` si des données sont ajoutées).
- Une PR = un sujet. Fusionner (squash) seulement si `pytest`, `e2e` et les analyses CodeQL sont vertes.
- Ne jamais désactiver, sauter ou assouplir un test pour passer : corriger la cause.

## 4. Mises à jour Dependabot

Lire les notes de version. Pour `gunicorn`, Flask ou tout ce qui tourne en production : lancer le serveur avec les
options de `Procfile` (`gunicorn wsgi:app --workers 2 --threads 4 ...`) et appeler `/health`, `/`, `/lieux`, puis
une rafale de requêtes en parallèle ; les tests du CI ne démarrent pas Gunicorn. Les actions CI se valident par
leurs propres vérifications.
