# Entreprise Teranga : l'équipe d'agents

Quatorze agents spécialisés sont décrits dans `.claude/agents/`. Toute session Claude Code ouverte sur ce dépôt (locale
ou dans le cloud) les connaît et peut les lancer. Ensemble, ils couvrent le projet de A à Z : produit, code, qualité,
production, visibilité et commerce. Ce document dit qui fait quoi, dans quel ordre, et ce que chacun n'a pas le droit
de faire.

## Organigramme

| Pôle | Qui | Rôle |
|---|---|---|
| Direction | le propriétaire | décide des priorités ; valide ce qui change l'écran, ce que dit l'IA, les coûts, le DNS, les secrets et les réglages ; seul à envoyer, publier, signer ou payer |
| Direction | le chef de projet (la session Claude Code principale) | conduit le conseil de la semaine (`conseil-hebdo`), lance les agents, relit leurs PR, fusionne ce que la règle en vigueur lui permet |
| Direction | `analyste` | tableau des indicateurs de la semaine, en lecture seule |
| Pôle produit | `chef-produit` | fiche produit avant de construire (Mon Projet, Teranga Voyage, annuaire, diaspora) |
| Pôle produit | `qualite-ia` | contexte envoyé à l'IA : faux déclenchements, bruit, faits manquants |
| Pôle produit | `verificateur-reperes` | repères pratiques vérifiés sur des pages officielles, sourcés et datés |
| Pôle produit | `voix` | conversation vocale |
| Pôle technique | `developpeur` | une PR du plan, test d'abord |
| Pôle technique | `gardien-prod` | santé de la production après chaque fusion |
| Pôle technique | `mesure-latence` | où passe le temps d'une réponse |
| Pôle technique | `ops-infra` | état de l'infrastructure hors Render |
| Pôle qualité | `relecteur-pr` | relecture indépendante avant fusion |
| Pôle qualité | `securite` | revue de sécurité |
| Pôle visibilité | `seo-visibilite` | moteurs de recherche |
| Pôle visibilité | `communication` | marketing : astuces WhatsApp, scripts TikTok et Reels, Instagram, groupes de la diaspora, calendrier ; jamais publiés par l'agent |
| Pôle commercial | `partenariats` | trouve de nouveaux partenaires sur des sources publiques vérifiées, prospects, argumentaires, relances, partenaire pilote, suivi par `/go/` ; n'envoie jamais rien |

Ce que les agents ne font jamais, quel que soit leur pôle : envoyer un message, publier, acheter, signer, créer un
compte, changer le DNS, un secret ou un réglage de production. Ils le préparent ; le propriétaire le fait.

## Organisation

- **Le propriétaire décide.** Il fixe les priorités et valide ce qui change l'écran, ce que dit l'IA, les coûts, le
  DNS, les secrets et les réglages.
- **Claude Code (la session principale) est le chef de projet.** Il lance les agents, relit leurs PR, teste les PR
  fusionnées ensemble, fusionne ce que la règle en vigueur lui permet (tests, outils, documents, correctifs invisibles,
  contrôles verts) et surveille la production après chaque fusion.
- **Les agents font un sujet chacun.** Ils ouvrent une PR **brouillon** en français et ne fusionnent jamais. Ils ne se
  parlent pas entre eux : ils rendent un rapport au chef de projet.
- **Isolation.** Les agents qui écrivent des fichiers (`qualite-ia`, `verificateur-reperes`, `voix`, `seo-visibilite`,
  `developpeur`, `chef-produit`, `partenariats`, `communication`) déclarent `isolation: worktree` dans leur en-tête :
  chacun travaille dans sa propre copie du dépôt, sans partager fichiers ni index Git avec un autre agent. Sans
  isolation, deux agents lancés ensemble se mêlent et une PR peut contenir le sujet de l'autre. Si un lancement
  n'applique pas ce réglage (un défaut a été signalé pour des agents fournis par un plugin), passer
  `isolation: "worktree"` dans l'appel à l'outil Agent. Les agents en lecture seule n'en ont pas besoin.

## Les quatorze agents

| Agent | À utiliser quand | Accès | Livrable |
|---|---|---|---|
| `analyste` | conseil de la semaine ; avant une décision de priorité ou de prix | Render en lecture, shell, aucune écriture de fichier | tableau des indicateurs, mesuré et estimé séparés |
| `chef-produit` | avant de construire une fonction ; hésitation entre deux idées | dépôt (documents seulement), pas de shell | fiche dans `docs/produit/` en PR brouillon |
| `developpeur` | une correction ou petite fonction du plan hors voix, SEO, repères et contexte de l'IA | dépôt | PR brouillon, test vu rouge puis vert |
| `partenariats` | chaque jeudi ; démarcher un établissement, préparer un rendez-vous, suivre le pilote | dépôt, web (sources publiques) | 5 prospects vérifiés, brouillons de messages, relances, fiche pilote, PR brouillon |
| `communication` | chaque lundi ; annonce d'une nouveauté | dépôt (documents seulement) et web, pas de shell | `docs/communication/<semaine>.md` (WhatsApp, vidéos, Instagram, diaspora) en PR brouillon |
| `gardien-prod` | après chaque fusion sur `main`, ou « comment va le site » | Render en lecture seule, aucun shell | rapport OK / À SURVEILLER / ALERTE avec les lignes et heures |
| `relecteur-pr` | avant de fusionner une PR qui change le code, le contexte de l'IA ou l'écran | lecture du dépôt, shell, aucune écriture de fichier | verdict et défauts classés avec scénario |
| `securite` | PR touchant `app.py`, `routes/`, la CSP, la recherche externe ou un workflow ; chaque mois | lecture du dépôt, shell, aucune écriture de fichier | constats avec scénario d'attaque réaliste |
| `qualite-ia` | après toute modification du contexte de l'IA | dépôt (tests et correctifs) | PR brouillon : tests, mesures avant et après |
| `verificateur-reperes` | PR de repères ; fraîcheur mensuelle des sources | dépôt, web | repères confirmés, corrigés ou « non vérifié » avec source et date |
| `voix` | toute modification de la conversation vocale | dépôt (`static/home.js`, tests navigateur) | PR brouillon avec calcul des limites de débit |
| `seo-visibilite` | après toute modification de page ; le lundi | dépôt | PR brouillon, résultat de l'audit |
| `ops-infra` | savoir ce qui tourne sur Coolify, puis OVH | jetons en lecture seule de l'environnement, requêtes `GET` | état lu, avec ce qui n'a pas pu l'être |
| `mesure-latence` | une fois l'instrumentation en ligne, avant toute décision de vitesse | journaux Render en lecture, shell | médianes et p95 par étape, propositions chiffrées |

« Lecture seule » veut dire : aucun outil d'écriture de fichiers dans la liste de l'agent. Le shell reste disponible pour
lire et lancer des contrôles ; la consigne de l'agent interdit le reste. Un test (`tests/test_equipe_agents.py`) vérifie
que ces agents n'ont aucun outil d'écriture, que `gardien-prod` et `analyste` n'ont que des outils Render de lecture, et
que `partenariats` et `communication` gardent leurs interdits (rien envoyé, rien publié, aucun partenaire sans accord
écrit).

## Qui touche à quels fichiers

Deux agents ne modifient pas le même fichier en même temps : les fusions deviennent des conflits.

| Fichiers | Un seul agent à la fois |
|---|---|
| `routes/chat.py`, `services/intelligence.py`, `services/chat_payload_service.py`, `app.py` | agent de routage ou de latence, ou `developpeur` sur demande |
| `static/home.js`, `templates/home.html`, `static/sw.js`, `tests/e2e/*voice*` | `voix` |
| `services/senegal_knowledge.py`, `services/practical_facts.py`, `services/web_policy.py`, `services/guide_modes.py` | `qualite-ia` |
| `services/facts/*.py` | `verificateur-reperes` |
| pages, modèles, `scripts/audit_seo.py` | `seo-visibilite` |
| `docs/produit/` | `chef-produit` |
| `docs/communication/` | `communication` |
| `docs/prospects-*.csv`, `docs/COMMERCIAL_PLAN.md`, `docs/VENTES-MESSAGES.md`, `data/partners.json` | `partenariats` |

## Rythme conseillé

1. **Chaque lundi** : le conseil de la semaine (skill `conseil-hebdo`) avec `gardien-prod`, `analyste` et
   `seo-visibilite`, puis trois sujets au plus pour la semaine.
2. **Avant une fusion** : `relecteur-pr` ; en plus `securite` si la PR touche l'un des sujets de sécurité.
3. **Après une fusion** : `gardien-prod`, dans les minutes qui suivent le déploiement.
4. **Chaque mois** : `securite` et `verificateur-reperes`.
5. **Avant une décision de vitesse** : `mesure-latence`, jamais sur une estimation.
6. **Avant de construire** : `chef-produit` écrit la fiche ; `developpeur` la réalise.

## Règles communes

- Lire `AGENTS.md` d'abord. Textes, commits et PR en français.
- Une PR par sujet, en brouillon, avec Résumé et Tests. Jamais de poussée sur `main`, jamais de fusion par un agent.
- **Pousser après chaque étape** : la limite de session de Claude et les redémarrages du conteneur ont déjà arrêté des
  agents en cours de route.
- Preuve rouge puis verte pour chaque test nouveau ; aucun test affaibli.
- Un fichier de test sous `tests/e2e/` n'importe jamais Playwright sans protection (le job `pytest` de la CI ne l'a pas).
- Aucun fait inventé, aucun secret écrit, demandé ou affiché. Les jetons vivent dans les réglages de l'environnement.
- Dire ce qui n'a pas tourné : **exécuté et réussi**, **exécuté et échoué**, **ignoré** (raison), **non exécuté** (outil
  manquant). Ne jamais écrire « vert » pour un contrôle qui n'a pas tourné.
- Trois agents en parallèle au maximum : ils consomment le quota de la session.

## Format commun du rapport final

Ce qui a été fait, fichiers modifiés, résultats exacts de chaque contrôle (avec les quatre états ci-dessus), lien de la
PR, ce qui n'est pas vérifié, et les décisions demandées au propriétaire.

## Autres acteurs

- **ChatGPT** donne un deuxième avis et des idées par GitHub ; il ne fusionne pas. L'état du projet est sur le tableau
  de bord (issue #417).
- **Le pont GitHub** (`docs/claude-github-bridge.md`) lance des tâches courtes de Claude depuis un commentaire ; il est
  facturé à l'usage.

## Tâches planifiées

Le rythme tourne tout seul grâce à des tâches planifiées Claude (heure de Paris). Chacune ouvre une session neuve sur
ce dépôt, lance les agents indiqués et rend son rapport au propriétaire. Aucune ne fusionne, ne publie ni n'envoie.

| Quand | Tâche | Agents |
|---|---|---|
| lundi matin | Marketing de la semaine | `communication` |
| lundi matin | Conseil de la semaine (`conseil-hebdo`) | `gardien-prod`, `analyste`, `seo-visibilite` |
| mercredi matin | Qualité de l'IA | `qualite-ia`, puis `relecteur-pr` |
| jeudi matin | Commercial et partenaires | `partenariats` |
| le 1er du mois | Sécurité et repères | `securite`, `verificateur-reperes` |
