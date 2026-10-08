# Teranga AI — guide pour les agents de code (Codex, Claude Code…)

Assistant IA du Sénégal (voyage, vie pratique, diaspora, commerçants) : https://teranga-ai.fr.
Flask + Gunicorn, hébergé sur Render (déploiement automatique à chaque fusion sur `main`),
Redis (Render Key Value) pour les limites, le cache et les compteurs. Application Android (TWA,
package `fr.teranga_ai`) qui affiche le même site.

Le propriétaire parle **français** : textes du site, messages de commit, descriptions de PR et
commentaires de code en français.

## Avant chaque PR (le CI fait la même chose)

```bash
pip install -r requirements-dev.txt
ruff check --select E9,F63,F7,F82,F401,F811,F841 .
bandit -q -r app.py routes services -ll   # failles courantes ; une alerte volontaire se justifie par « # nosec Bxxx - raison »
pytest -q --cov=app --cov=routes --cov=services --cov-fail-under=85   # ~1000 tests, < 1 min, aucun appel réseau réel
pytest -q tests/e2e           # clics réels dans Chromium (Playwright)
node --check static/home.js static/trip-planner.js
```

Une PR ne se fusionne que si **pytest et e2e sont verts**. Ne jamais désactiver, sauter ou
assouplir un test pour passer : corriger la cause. Si un changement voulu modifie un
comportement testé, mettre le test à jour **et** l'expliquer dans la PR.

## Carte du code

| Où | Quoi |
|---|---|
| `app.py` | Configuration, sécurité, limites (`GUARDED_LIMITS`), assemblage du contexte du chat (`parse_chat_payload`) |
| `routes/` | Routes Flask : `chat.py` (flux NDJSON), `places.py` (/lieux), `seo.py`, `monetization.py` (/go, /offres-partenaires, /stats-partenaires), `emergency.py` (/urgences), `events.py` (/calendrier-fetes-senegal)… |
| `services/senegal_knowledge.py` | Choix des lieux, régions et plats ajoutés au contexte de l'IA |
| `services/practical_facts.py` | Repères pratiques **vérifiés** (urgences, argent, visa, SIM, foncier…) injectés selon la question |
| `services/events.py` | Calendrier des fêtes (dates lunaires marquées « estimée ») |
| `services/trip_planner.py` + `static/trip-planner.js` | Planificateur de voyage (flux avec signes de vie toutes les 10 s) |
| `services/backup_ai.py` | Claude (Anthropic) : secours, ou IA principale si `AI_PRINCIPALE=claude` |
| `templates/home.html` + `static/home.js` | Accueil et chat (design v2) |
| `static/site.css` | Feuille des pages secondaires (mêmes jetons de couleur que l'accueil) |
| `static/sw.js` | Service worker (hors connexion) : changer `VERSION` quand les fichiers préchargés changent |
| `data/senegal_knowledge.json` | Base de connaissances : 93 lieux, 19 plats, 14 régions |
| `data/partners.json` | Adresses partenaires (toujours affichées « Partenaire ») |
| `docs/` | Guides pour le propriétaire (monétisation, partenaires, Google Play, IA de secours) |

## Skills du projet (`.claude/skills/`)

| Skill | Quand l'utiliser |
|---|---|
| `preparer-une-pr` | avant chaque commit, PR ou fusion ; mises à jour Dependabot |
| `ajouter-des-reperes` | nouveau sujet de repères pratiques vérifiés |
| `ajouter-un-lieu` | nouveau lieu sourcé dans la base |
| `banc-ia` | après toute modification du contexte de l'IA |
| `audit-seo` | après toute modification de page (`python scripts/audit_seo.py`) |
| `publier-android` | Google Play : test interne, test fermé, lien `assetlinks.json` |

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
  autre domaine : tout est servi par le site (`static/fonts/`).
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
`ANTHROPIC_API_KEY`, `AI_PRINCIPALE`, `ANTHROPIC_MODEL`, `ANALYTICS_SCRIPT_URL`, `ANALYTICS_SITE_ID`.
Les tests n'ont besoin d'aucune vraie clé (`OPENAI_API_KEY=test-key` suffit).
