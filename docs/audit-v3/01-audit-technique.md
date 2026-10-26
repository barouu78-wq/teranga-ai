# Audit V3 — 01. Audit technique : architecture, tests, sécurité, performances

Date : 25 et 26 octobre 2026. Code audité : `main` au commit `c8e999d` (#531). Production : service Render
`teranga-ai-1`, lu en lecture seule. Aucun secret n'a été lu ni affiché.

Chaque constat dit d'où il vient :
- **exécuté** : commande lancée, résultat lu ;
- **lu** : code ou journal lu ;
- **déclaré** : source tierce non vérifiable ici ;
- **non mesuré** : à mesurer.

## 1. Résumé

1. **Le code est en bonne santé.** Tous les contrôles de la CI passent (3 232 tests, couverture 94,28 %, 171 tests
   navigateur, audit SEO sans défaut). La revue de sécurité ne trouve **aucun P0** ; elle trouve 4 P1 et 8 P2.
2. **Il n'y a presque pas d'utilisateurs.** Production : 13 requêtes au chat en 7 jours (18 au 25 octobre),
   probablement des essais. Les performances réelles ne peuvent pas être mesurées sans trafic (lu, journaux Render).
3. **Le serveur de Teranga n'est pas le goulot.** Sur les 5 réponses mesurées, 96 à 99 % du temps avant le premier
   mot est l'attente du fournisseur d'IA. La préparation du contexte prend 11,6 ms en médiane sur 100 questions
   (exécuté, banc V3).
4. **La recherche web est proposée trop largement.** L'outil web est proposé sur 43 questions sur 100, dont 22
   questions stables : carte d'identité, chaloupe de Gorée, paludisme (exécuté, 03-benchmark-teranga.md).
5. **Une information est dépassée.** La page `/transport-senegal` dit que le prolongement du TER vers l'aéroport
   AIBD « est prévu ». Selon l'APS et la presse, il est en service depuis le 28 septembre 2026 (déclaré : extraits de
   recherche ; la page de l'APS n'est pas lisible depuis la session, voir §7).

## 2. L'inventaire du rapport V3, vérifié dans le code

| Fonction annoncée | Où dans le code | État vérifié |
|---|---|---|
| Chat en français, anglais, wolof | `routes/chat.py`, `services/language_quality.py`, `app.py` (`SAFE_LANG` : fr, en, wo, ff) | En place (lu, tests verts) |
| Compréhension du pulaar côté serveur | `services/language_quality.py`, `services/voice_quality.py` | Comprise côté serveur, retirée du sélecteur (README) ; ne pas réintroduire sans décision du propriétaire |
| Base de connaissances | `data/senegal_knowledge.json` | 98 lieux, 19 plats, 14 régions, 7 sites UNESCO, 7 dossiers d'histoire, 15 expressions wolof, 8 pulaar (exécuté) |
| Explorer, cartes, images (Google puis Wikimedia) | `routes/explorer.py`, `services/images.py`, `services/image_topics.py` | En place ; Google Custom Search répond 403 en production, les photos viennent de Wikipédia et Commons (lu, journaux) |
| Recherche web | `services/web_policy.py`, `services/external_research.py`, outil web du fournisseur | En place ; déclenchement large (voir §5) |
| Planificateur, météo, infos pratiques | `services/trip_planner.py`, `services/weather.py`, `services/practical_facts.py` | En place ; le planificateur n'écrit pas de ligne de latence |
| Reconnaissance et synthèse vocales | `routes/stt.py` (`gpt-4o-transcribe`), `routes/tts.py` (`gpt-4o-mini-tts`), `routes/realtime.py` | En place ; 1 délai de 30 s sur 6 lectures `/tts` (lu, journaux) |
| Calculs, change, fêtes, urgences | `services/quick_answers.py`, `services/calculators.py`, `services/events.py`, `routes/emergency.py` | En place, réponses sans IA ; deux formulations de conversion manquées (corrigé, PR #539) |
| Projets des jeunes, opportunités | `routes/youth_projects.py` | En place |
| SEO, partage, widget partenaire | `services/seo.py`, `routes/share.py`, `routes/monetization.py` | En place ; 205 pages dans le plan du site, 0 défaut (exécuté) |
| Cache, limites, sécurité, tests | `app.py` (`GUARDED_LIMITS`), `services/http_headers.py`, `tests/` | En place (voir §4 et §6) |
| IA principale | `services/backup_ai.py` | Claude Opus depuis le 25 octobre 15 h 08 UTC (`AI_PRINCIPALE=claude`) ; OpenAI en secours ; aucune question réelle depuis |

## 3. Architecture

- 17 695 lignes de Python dans `app.py`, `routes/` (17 fichiers) et `services/` (67 fichiers). Tests : 187 fichiers,
  plus 11 fichiers navigateur (exécuté, `wc`).
- Carte du code (graphify 0.9.86, locale, sans IA, sur `main` au commit `9cbd26b`) : 4 952 éléments, 10 951 liens,
  258 groupes. Éléments les plus reliés :
  - `parse_chat_payload()` : 75 liens ;
  - `matching_topics()` : 57 ;
  - `VoiceBench` : 57 ;
  - `format_senegal_knowledge()` : 50 ;
  - `quick_answer()` : 46.

  Toucher à l'un d'eux demande le plus de tests.
- Hébergement : Render Starter (0,5 processeur, 512 Mo), Gunicorn 2 processus × 4 fils (`gunicorn.conf.py`,
  `render.yaml`), Redis pour les limites et le cache.

## 4. Contrôles exécutés (25 octobre 2026, `main` au commit `c8e999d`)

| Contrôle | Résultat |
|---|---|
| `python scripts/check_dev_env.py` | outils présents ; e2e « non vérifié » par ce script, lancé à part ci-dessous |
| `ruff check --select E9,F63,F7,F82,F401,F811,F841 .` | réussi |
| `ruff check .` (toutes les règles, pour information) | 53 remarques de style, dont 36 E402 ; aucune n'est exigée par la CI |
| `bandit -q -r app.py routes services -ll` | aucune alerte moyenne ou haute |
| `pip-audit` (requirements et requirements-dev) | aucune vulnérabilité connue (agent sécurité) |
| `node --check static/home.js static/trip-planner.js` | réussi |
| `python scripts/audit_seo.py` | 205 pages, 0 problème |
| `pytest --cov … --cov-fail-under=85 --ignore=tests/e2e` | 3 232 réussis en 118 s, couverture 94,28 % |
| `E2E_REQUIRED=1 pytest tests/e2e -rs` | 171 réussis, 0 ignoré |

Modules les moins couverts :
- `services/click_stats.py` : 68 % ;
- `services/seo_integrations.py` : 71 % ;
- `services/observability.py` : 75 % ;
- `services/explorer.py` : 81 %.

## 5. Production et performances (lu, journaux Render, 18 au 25 octobre 2026)

- **Conservation** : les journaux remontent à environ 7 jours seulement ; avant le 18 octobre, rien n'est lisible.
- **Volume** :
  - 13 requêtes `/chat` (6 le 21 octobre, 7 le 24) ;
  - 6 requêtes `/tts` ;
  - aucune requête `/stt` ni `/api/trip-planner`.

  Les 765 à 1 033 réponses 200 par jour viennent des robots et des contrôles de santé.
- **Temps** : chaque groupe compte moins de 20 mesures, rien n'est concluant.

  | Groupe | Mesures | Médiane avant le premier mot |
  |---|---|---|
  | Appels au modèle | 5 | 3 807 ms |
  | Appels avec web | 1 | 5 309 ms |
  | Photos seules | 8 | 780 ms |
- **Erreurs** :
  - `/chat` : 0 erreur 5xx sur 13 ;
  - `/tts` : 1 sur 6 (délai de 30 s chez OpenAI, réponse 502) ;
  - 0 `WORKER TIMEOUT` et 0 secours utilisé.
- **Claude** : aucune question réelle depuis le passage à Claude Opus ; la prochaine ligne `latence` doit afficher
  un modèle Claude dans `modele=`. Claude reçoit `max_tokens` 4 000, contre 800 ou 1 200 pour OpenAI (lu,
  `services/chat_service.py`) : réponses potentiellement plus longues et plus chères, non mesuré.
- **Banc local** (03-benchmark-teranga.md) :
  - 100 questions, 100 réponses HTTP 200 ;
  - 8 réponses prêtes sans IA ;
  - outil web proposé 43 fois, dont 22 sur des questions stables ;
  - préparation serveur : médiane 11,6 ms, p95 17,2 ms.

## 6. Sécurité (revue indépendante de l'agent sécurité, 25 octobre 2026)

Aucun P0. Aucun secret dans l'arbre, dans les 2 376 commits ni dans les 1 202 issues, PR et commentaires.
`/image-proxy`, la CSP de l'accueil, les hôtes de confiance et les limites coûteuses sont conformes.

| Gravité | Constat | Fichiers | Suite |
|---|---|---|---|
| P1-1 | `main` n'est pas protégée ; le pont Claude garde un jeton d'écriture (`persist-credentials: true`) et autorise `Write` + `pytest` : une consigne injectée dans un fil d'issue pourrait pousser du code sur `main`, que Render déploie | `.github/workflows/claude-bridge.yml:30-94` | Protéger `main` (réglage GitHub, **propriétaire**) ; `persist-credentials: false` (PR à faire) |
| P1-2 | Un lien `/trip-planner#trip=…` ou `?context_place=` injectait du texte dans les **instructions** du modèle (risque d'escroquerie : « payer au numéro X ») | `services/chat_payload_service.py` | **Corrigé**, branche `secu/contexte-interface-en-donnees` |
| P1-3 | 8 requêtes longues en parallèle (2 × 4 fils) bloquent tout le site ; mesuré en local : `/health` passe de 0,01 s à 6,7 s | `gunicorn.conf.py`, `routes/chat.py:434` | Limite de requêtes en cours par IP, plafond global (à concevoir) |
| P1-4 | Aucun plafond global de dépense IA ; seulement des limites par IP | `app.py:288-305`, `services/backup_ai.py` | Compteur quotidien global dans Redis + budgets chez les fournisseurs (**propriétaire**) |
| P2-1 | `'unsafe-inline'` pour les scripts sur 40 pages sans nonce | `services/http_headers.py:29` | Nonce partout |
| P2-2 | 6 routes POST hors `require_json_post` ; un JSON très imbriqué donne une erreur 500 sur 3 routes | `services/trip_planner.py:720,754`, `routes/share.py:19`… | Décorateur ou équivalent |
| P2-3 | Blocage par IP : effet collatéral sur les IP partagées (CGNAT), IPv6 non regroupée | `services/abuse.py`, `app.py:271` | IP + identité, /64 |
| P2-4 | `/explorer-image` accepte des requêtes libres (jusqu'à 7 appels sortants chacune) | `routes/explorer.py:154-173` | N'accepter que les titres de la base |
| P2-5 | Liens de partage sans expiration ; balise de fin d'historique non neutralisée | `services/shared_answers.py`, `services/conversation.py` | Neutraliser, expirer |
| P2-6 | Actions GitHub épinglées par version, pas par commit ; dépendances de dev non figées | `.github/workflows/*`, `requirements-dev.txt` | Épingler |
| P2-7 | Script d'audience tiers possible sur `/stats-*` | `services/analytics.py` | Exclure ces pages |
| P2-8 | `.gitignore` sans `*.jks`, `*.keystore` ; `# nosec` sans raison | `.gitignore`, plusieurs fichiers | Hygiène |

## 7. Interface et exactitude

- **Règles d'interface de Vercel** (web-design-guidelines) sur `templates/home.html`, `static/home.js`,
  `static/site.css`, `services/site_layout.py`. Conformes :
  - focus clavier visible ;
  - animations réduites sur demande ;
  - zoom non bloqué ;
  - `touch-action` ;
  - `color-scheme` et `theme-color` ;
  - zones sûres (`safe-area`) ;
  - libellés des boutons-icônes ;
  - `aria-live` ;
  - photos sans saut de mise en page.

  Défauts :
  - glyphes décoratifs lus à voix haute et « Teranga AI » traduisible : **corrigés**, PR #538 ;
  - émojis utilisés comme icônes (🚀 🔎 🤝 📍 🎯 🌍) dans « Mon projet » et les parcours, contraires à la règle du
    projet : changent l'écran, **Go du propriétaire attendu** ;
  - espace insécable manquant dans « 50 000 ».
- **TER jusqu'à l'AIBD** :
  - `services/seo.py:500` (« son prolongement vers l'aéroport est prévu ») et `:504` (« jusqu'à Diamniadio ») sont
    dépassés ;
  - `services/practical_facts.py:334` reste prudent (« vérifier si le prolongement… est en service ») ;
  - sources trouvées : [APS](https://aps.sn/phase-2-du-ter-laibd-desormais-relie-directement-a-dakar/),
    [International Railway Journal](https://www.railjournal.com/passenger/main-line/dakar-regional-express-reaches-international-airport/),
    [Dakaractu](https://www.dakaractu.com/TER-la-desserte-de-l-AIBD-officiellement-mise-en-service_a276475.html)
    (extraits de recherche, pages non lisibles depuis la session) ;
  - règle du projet : un nouveau fait ne s'écrit qu'après lecture d'une source officielle. Il faut autoriser
    `aps.sn` dans le réseau de la session (propriétaire).

## 8. Bugs connus cités par le rapport V3

| Sujet | Constat vérifié |
|---|---|
| Boutons de l'accueil (profils, parcours) | Couverts par les tests navigateur : 171 réussis (exécuté). Accessibilité corrigée (PR #538). |
| Images | Google Custom Search refuse (403) : 15 avertissements en 7 jours. Repli sur Wikipédia et Commons. Cache des photos en mémoire par processus, vidé à chaque mise en ligne (lu). Suivi : #493. |
| Lenteurs | Attente du fournisseur d'IA : 96 à 99 % du premier mot. Teranga ne contrôle que la part des questions envoyées au modèle et à la recherche web. |
| Voix | 1 lecture `/tts` sur 6 bloquée 30 s puis en erreur, sans nouvelle tentative (`routes/tts.py`). |
| Recherche web | Proposée sur 22 questions stables du banc ; l'effet en production n'est pas mesuré (une seule réponse avec web dans les journaux). |

## 9. Ce qui n'a pas pu être fait

- Mesures de performance concluantes : il faut au moins 20 requêtes par groupe, et il y en a 13 au total.
- Lecture des sites officiels (APS, Hugging Face, sites des acteurs sénégalais) : bloqués par le réseau de la session.
- Tableau des indicateurs de trafic (agent analyste) : interrompu par une limite d'usage, à relancer.
- Justesse des réponses de l'IA : non mesurée, faute de budget validé pour passer le banc par le vrai modèle.
