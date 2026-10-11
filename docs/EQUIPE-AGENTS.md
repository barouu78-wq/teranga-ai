# Équipe d'agents de Teranga AI

Neuf agents spécialisés sont décrits dans `.claude/agents/`. Toute session Claude Code ouverte sur ce dépôt (locale ou
dans le cloud) les connaît et peut les lancer. Ce document dit qui fait quoi, dans quel ordre, et ce que chacun n'a
pas le droit de faire.

## Organisation

- **Le propriétaire décide.** Il fixe les priorités et valide ce qui change l'écran, ce que dit l'IA, les coûts, le
  DNS, les secrets et les réglages.
- **Claude Code (la session principale) est le chef de projet.** Il lance les agents, relit leurs PR, teste les PR
  fusionnées ensemble, fusionne ce que la règle en vigueur lui permet (tests, outils, documents, correctifs invisibles,
  contrôles verts) et surveille la production après chaque fusion.
- **Les agents font un sujet chacun.** Ils ouvrent une PR **brouillon** en français et ne fusionnent jamais. Ils ne se
  parlent pas entre eux : ils rendent un rapport au chef de projet.
- **Isolation.** Les quatre agents qui écrivent des fichiers (`qualite-ia`, `verificateur-reperes`, `voix`,
  `seo-visibilite`) déclarent `isolation: worktree` dans leur en-tête : chacun travaille dans sa propre copie du dépôt,
  sans partager fichiers ni index Git avec un autre agent. Sans isolation, deux agents lancés ensemble se mêlent et une PR
  peut contenir le sujet de l'autre. Si un lancement n'applique pas ce réglage (un défaut a été signalé pour des agents
  fournis par un plugin), passer `isolation: "worktree"` dans l'appel à l'outil Agent. Les agents en lecture seule n'en
  ont pas besoin.

## Les neuf agents

| Agent | À utiliser quand | Accès | Livrable |
|---|---|---|---|
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
que ces agents n'ont aucun outil d'écriture et que `gardien-prod` n'a que des outils Render de lecture.

## Qui touche à quels fichiers

Deux agents ne modifient pas le même fichier en même temps : les fusions deviennent des conflits.

| Fichiers | Un seul agent à la fois |
|---|---|
| `routes/chat.py`, `services/intelligence.py`, `services/chat_payload_service.py`, `app.py` | agent de routage ou de latence |
| `static/home.js`, `templates/home.html`, `static/sw.js`, `tests/e2e/*voice*` | `voix` |
| `services/senegal_knowledge.py`, `services/practical_facts.py`, `services/web_policy.py`, `services/guide_modes.py` | `qualite-ia` |
| `services/facts/*.py` | `verificateur-reperes` |
| pages, modèles, `scripts/audit_seo.py` | `seo-visibilite` |

## Rythme conseillé

1. **Avant une fusion** : `relecteur-pr` ; en plus `securite` si la PR touche l'un des sujets de sécurité.
2. **Après une fusion** : `gardien-prod`, dans les minutes qui suivent le déploiement.
3. **Chaque lundi** : `seo-visibilite`. **Chaque mois** : `securite` et `verificateur-reperes`.
4. **Avant une décision de vitesse** : `mesure-latence`, jamais sur une estimation.

## Règles communes

- Lire `AGENTS.md` d'abord. Textes, commits et PR en français.
- Une PR par sujet, en brouillon, avec Résumé et Tests. Jamais de poussée sur `main`, jamais de fusion par un agent.
- **Pousser après chaque étape** : la limite de session de Claude a déjà arrêté des agents en cours de route.
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
