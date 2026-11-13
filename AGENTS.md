# Teranga AI — guide pour les agents de code (Codex, Claude Code…)

Assistant IA du Sénégal (voyage, vie pratique, diaspora, commerçants) : https://teranga-ai.fr.
Flask + Gunicorn, hébergé sur Render (déploiement automatique à chaque fusion sur `main`),
Redis (Render Key Value) pour les limites, le cache et les compteurs. Application Android (TWA,
package `fr.teranga_ai`) qui affiche le même site.

Le propriétaire parle **français** : textes du site, messages de commit, descriptions de PR et
commentaires de code en français.

## Avant chaque PR (le CI fait la même chose)

```bash
pip install -r requirements-dev.txt        # pytest, couverture, Ruff, Bandit
python scripts/check_dev_env.py            # dit quels contrôles peuvent réellement tourner ici
ruff check --select E9,F63,F7,F82,F401,F811,F841 .
bandit -q -r app.py routes services -ll   # failles courantes ; une alerte volontaire se justifie par « # nosec Bxxx - raison »
pytest -q --cov=app --cov=routes --cov=services --cov-fail-under=85   # ~1000 tests, < 1 min, aucun appel réseau réel
node --check static/home.js static/trip-planner.js
# Tests e2e (clics réels dans Chromium) : une fois, puis à chaque PR
pip install -r requirements-e2e.txt && python -m playwright install --with-deps chromium
E2E_REQUIRED=1 pytest -q tests/e2e -rs
```

Une PR ne se fusionne que si **pytest et e2e sont verts**. Ne jamais désactiver, sauter ou
assouplir un test pour passer : corriger la cause. Si un changement voulu modifie un
comportement testé, mettre le test à jour **et** l'expliquer dans la PR.

**Réussi ≠ ignoré ≠ non exécuté.** Sans Playwright, `pytest tests/e2e` marque les tests « skipped » :
ils n'ont pas réussi. `E2E_REQUIRED=1` transforme un navigateur manquant en échec, et `-rs` affiche la
raison de chaque test ignoré. Un rapport distingue toujours *exécuté et réussi*, *exécuté et échoué*,
*ignoré* (avec la raison) et *non exécuté* (avec l'outil manquant) ; il n'annonce jamais « vert » pour
un contrôle qui n'a pas tourné.

## Carte du code

| Où | Quoi |
|---|---|
| `app.py` | Configuration, sécurité, limites (`GUARDED_LIMITS`), assemblage du contexte du chat (`parse_chat_payload`) |
| `routes/` | Routes Flask : `chat.py` (flux NDJSON), `places.py` (/lieux), `seo.py`, `monetization.py` (/go, /offres-partenaires, /stats-partenaires), `emergency.py` (/urgences), `events.py` (/calendrier-fetes-senegal)… |
| `services/senegal_knowledge.py` | Choix des lieux, régions et plats ajoutés au contexte de l'IA |
| `services/practical_facts.py` | Repères pratiques **vérifiés** (urgences, argent, visa, SIM, foncier…) injectés selon la question |
| `services/events.py` | Calendrier des fêtes (dates lunaires marquées « estimée ») |
| `services/trip_planner.py` + `static/trip-planner.js` | Planificateur de voyage (flux avec signes de vie toutes les 10 s) |
| `services/adsense.py` | Annonce Google en fin de page de guide et `/ads.txt`, éteintes par défaut (`docs/PUBLICITE.md`) |
| `services/backup_ai.py` | Claude (Anthropic) : secours, ou IA principale si `AI_PRINCIPALE=claude` |
| `templates/home.html` + `static/home.js` | Accueil et chat (design v2) |
| `static/site.css` | Feuille des pages secondaires (mêmes jetons de couleur que l'accueil) |
| `static/sw.js` | Service worker (hors connexion) : changer `VERSION` quand les fichiers préchargés changent |
| `data/senegal_knowledge.json` | Base de connaissances : 98 lieux, 19 plats, 14 régions |
| `data/partners.json` | Adresses partenaires (toujours affichées « Partenaire ») |
| `docs/` | Guides pour le propriétaire (monétisation, partenaires, Google Play, IA de secours, hébergement : `INFRASTRUCTURE.md`) |

## Skills du projet (`.claude/skills/`)

| Skill | Quand l'utiliser |
|---|---|
| `preparer-une-pr` | avant chaque commit, PR ou fusion ; mises à jour Dependabot |
| `ajouter-des-reperes` | nouveau sujet de repères pratiques vérifiés |
| `ajouter-un-lieu` | nouveau lieu sourcé dans la base |
| `banc-ia` | après toute modification du contexte de l'IA |
| `audit-seo` | après toute modification de page (`python scripts/audit_seo.py`) |
| `publier-android` | Google Play : test interne, test fermé, lien `assetlinks.json` |
| `carte-du-code` | carte du code (graphify, local, sans IA) avant de toucher un endroit mal connu ; jamais `graphify install` |
| `faire-une-video` | vidéo courte (Reels, TikTok, présentation) avec les vrais écrans du site (`scripts/video/`) |
| `video-reponse` | vidéo « question → vraie réponse de Teranga » (style Nuit dorée) avec une réponse prête capturée (`scripts/video/reponses.py`) |
| `kit-de-la-semaine` | chaque lundi, ou « quoi poster ? » : brouillons marketing → textes prêts à copier, par jour et par réseau, faits et liens vérifiés |
| `conseil-hebdo` | chaque lundi, ou « où en est le projet » : réunion de l'entreprise d'agents (`docs/EQUIPE-AGENTS.md`) |
| `deboguer-methodiquement` | test rouge, bug, alerte : trouver la cause avant de corriger |
| `tester-d-abord` | nouvelle fonction ou correction : le test d'abord, vu rouge, puis vert |
| `verifier-avant-d-annoncer` | avant de dire « fini », « vert » ou « en ligne » : la preuve fraîche |
| `recevoir-une-relecture` | relecture ou commentaire sur une PR : vérifier chaque remarque avant d'agir |
| `hallmark` | nouvelle page, ou « /hallmark audit <page> » : design qui n'a pas l'air généré (règles « Floor », audit) |
| `ponytail` | toute tâche de code : le plus petit changement complet, réponse lisible en une fois |
| `ponytail-review` | relire une PR ou un changement, chaque remarque expliquée simplement |
| `ponytail-audit` | audit de tout le dépôt (bugs, failles, charge, code inutile), sans rien changer |
| `ponytail-debt` | liste des raccourcis notés `shortcut:` dans le code |
| `find-skills` | « y a-t-il un skill pour… » : chercher et proposer un skill existant (skills.sh) ; rien ne s'installe sans lecture et accord du propriétaire |

`deboguer-methodiquement`, `tester-d-abord`, `verifier-avant-d-annoncer` et `recevoir-une-relecture` sont adaptés de
Superpowers (licence MIT, `.claude/skills/LICENCE-superpowers.txt`). `hallmark` (texte seulement, sans scripts ni
génération d'images) et les quatre `ponytail` sont repris de GitHub sous licence MIT (`.claude/skills/LICENCE-hallmark.txt`,
`.claude/skills/LICENCE-ponytail.txt`), et `find-skills` de vercel-labs/skills (MIT, `.claude/skills/LICENCE-vercel-skills.txt`, texte
seulement) ; les règles de ce fichier priment sur les leurs.

## Règles à respecter

- **Exactitude avant tout.** Aucun fait inventé dans le code, la base ou les pages : pas de prix,
  d'horaires, de statistiques ni d'avis fictifs. Un repère qui peut changer est formulé comme
  « à vérifier ». Toute nouvelle donnée doit être sourcée (source dans le fichier ou la PR).
- **Intelligence testée.** Après toute modification du contexte de l'IA (base, `practical_facts`,
  `events`, choix des lieux), lancer `tests/test_ai_bench*.py` et `tests/test_knowledge_coverage.py`.
  Un nouveau lieu ajouté à la base est vérifié automatiquement. Les déclencheurs de
  `practical_facts` doivent éviter les faux positifs (« sur », « prise » dans « entreprise », « vol »).
- **Sécurité.** Ne jamais affaiblir le CSRF (`require_json_post`), les limites de débit, la CSP
  (`services/http_headers.py`) ni les hôtes de confiance. Pas de script ou de police venant d'un
  autre domaine : tout est servi par le site (`static/fonts/`). Seule exception, décidée par le propriétaire le 13 novembre 2026 :
  l'annonce Google AdSense (`services/adsense.py`), seulement sur les pages de guide qui la portent, avec la CSP
  stricte demandée par Google (nonce + `'strict-dynamic'`) ; jamais sur l'accueil, le chat ni les urgences.
- **Garde-fou des agents.** Avant chaque commande de Claude Code, `.claude/hooks/garde_fou.py` (déclaré
  dans `.claude/settings.json`) bloque : pousser sur `main`, une poussée forcée (`--force-with-lease`
  reste permis), `git reset --hard`, `rm -r` sur la racine, le dossier personnel ou le projet, et
  l'écriture directe sur `main` par les outils GitHub. Ne jamais le retirer ni le contourner : un
  blocage à tort se corrige dans le script, avec un test (`tests/test_garde_fou.py`).
- **Secrets.** Ne jamais écrire, demander ni afficher une clé (OpenAI, Anthropic, Redis, Google,
  `SECRET_KEY`, `STATS_TOKEN`) ni les fichiers de signature Android. Elles vivent uniquement
  dans les variables d'environnement de Render.
- **Accessibilité et mobile.** Zones tactiles ≥ 44 px, vrais `<button>`/`<a>`, libellés `aria-label`
  sur les boutons-icônes, pas d'émoji comme icône d'interface, pages lisibles à 390 px de large.
- **Partenaires.** Tout lien affilié passe par `/go/<type>` et reste marqué « Lien partenaire ».
- **Petites PR** : un sujet par PR, description en français (Résumé + Tests).

## Variables d'environnement (Render)

Obligatoires : `OPENAI_API_KEY`, `SECRET_KEY` (≥ 32 caractères en production), `TERANGA_ENV=production`.
Utiles : `REDIS_URL`, `SITE_URL`, `CONTACT_EMAIL`, `PARTNER_WHATSAPP`, `STATS_TOKEN`,
`GOOGLE_SITE_VERIFICATION`, `GETYOURGUIDE_PARTNER_ID`, `BOOKING_AID`, `TAXI_PARTNER_URL`,
`ANTHROPIC_API_KEY`, `AI_PRINCIPALE`, `ANTHROPIC_MODEL`, `ANALYTICS_SCRIPT_URL`, `ANALYTICS_SITE_ID`,
`ADSENSE_CLIENT` (compte Google AdSense, publie `/ads.txt`), `ADSENSE_SLOT` (bloc d'annonces : affiche les annonces).
Plafond de dépense IA : `AI_PLAFOND_JOUR` (requêtes vers l'IA par jour pour tout le site : chat, planificateur, voix ; défaut 500 ; au-delà, la base vérifiée répond jusqu'à minuit ; un secours après une panne du fournisseur peut faire un second appel pour la même requête).
**En production, Claude est l'IA principale** (`AI_PRINCIPALE=claude`, modèle `claude-sonnet-5-5` vu dans les journaux du 2 au 8 novembre 2026 ; choix confirmé par le propriétaire le 9 novembre 2026) : OpenAI sert de secours.
Modèles OpenAI (vide ou invalide = défaut ; lus par `services/model_params.py`) : `OPENAI_MODEL` (défaut `gpt-5.6-luna`), `OPENAI_COMPLEX_MODEL` (défaut `gpt-5.6-sol`), `OPENAI_TRIP_MODEL` (planificateur, sans défaut).
Les tests n'ont besoin d'aucune vraie clé (`OPENAI_API_KEY=test-key` suffit).
