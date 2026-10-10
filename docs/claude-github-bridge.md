# Pont GitHub ↔ Claude Code pour Teranga AI

Le pont permet de demander une intervention de Claude Code depuis un commentaire GitHub. GitHub garde la
tâche (le commentaire), le résultat (la réponse de Claude, la branche, la PR) et la trace de l'exécution
(l'onglet Actions). ChatGPT et le propriétaire relisent ensuite depuis GitHub.

Le fichier du pont est `.github/workflows/claude-bridge.yml`. Il ne contourne aucune limite de Claude : si
l'accès est refusé, l'exécution échoue et l'indique dans la conversation.

## Ce qui a été vérifié, et ce qui ne l'est pas

**Vérifié par une exécution réelle** (run [37998631452](https://github.com/barouu78-wq/teranga-ai/actions/runs/37998631452),
9 octobre 2026, commentaire sur la PR #394) :

- un commentaire du propriétaire commençant par la commande lance le workflow ;
- les commentaires des bots (`claude[bot]`, `chatgpt-codex-connector[bot]`) sont ignorés : leurs runs sont « skipped » ;
- Claude Code s'exécute (version 2.1.296, 17 tours, 67 secondes), lit le dépôt, lance les tests autorisés et répond dans un
  commentaire de suivi : `pytest` 1257 réussis, 44 ignorés (les tests e2e, Playwright absent), `node --check` OK ;
- la même exécution a montré que `ruff` n'était pas installé (`command not found`), d'où `requirements-dev.txt` complété ;
- la méthode d'accès utilisée était la **clé API** (`ANTHROPIC_API_KEY`) : l'exécution a coûté **0,2346 $** (valeur
  `total_cost_usd` du journal) pour cette tâche de lecture seule. Ce n'est pas l'abonnement.

**Non vérifié** (aucune exécution réelle observée) :

- l'écriture : création d'une branche `claude/...`, commit, poussée, lien de création de PR. Aucune branche `claude/` n'existe
  dans le dépôt à la date de cet audit ;
- la méthode abonnement (jeton `CLAUDE_CODE_OAUTH_TOKEN`) ;
- l'étape « Signaler l'échec dans la conversation » et le message d'erreur d'un secret absent ;
- les restrictions ajoutées par la PR de durcissement (commande en début de commentaire, PR du propriétaire seulement,
  outils retirés, concurrence). Elles sont vérifiées par `tests/test_claude_bridge_workflow.py` et `actionlint`, pas par un run.

Tant que ces points ne sont pas confirmés par un run réel, ne pas présenter l'écriture comme fonctionnelle.

## Choisir la méthode d'accès (un des deux secrets suffit)

Dans GitHub : **Settings → Secrets and variables → Actions → New repository secret**. Ne jamais coller une clé ou un jeton
dans une issue, un commentaire, un commit ou une conversation.

| Méthode | Secret | Facturation | Comment l'obtenir |
|---|---|---|---|
| Abonnement Claude Pro/Max | `CLAUDE_CODE_OAUTH_TOKEN` | incluse dans l'abonnement, soumise à ses limites d'usage | `claude setup-token` depuis un terminal où Claude Code fonctionne, puis coller le résultat dans le secret |
| API Anthropic | `ANTHROPIC_API_KEY` | **facturée à l'usage**, séparément de l'abonnement | console Anthropic ; créer une clé dédiée au pont (pas celle de Render) et fixer une limite de dépense mensuelle |

Le workflow transmet **un seul** secret à l'action : le jeton OAuth s'il existe, sinon la clé API (la documentation de l'action
ne dit pas lequel l'emporte si les deux sont fournis). Le journal de chaque exécution affiche la méthode retenue, jamais sa valeur.
Si aucun des deux secrets n'est configuré, l'exécution échoue tout de suite avec un message d'erreur.

Aucun achat n'est déclenché par ce document ni par le workflow. Si l'usage de l'abonnement est épuisé, il faut attendre la
réinitialisation, ou décider soi-même de configurer l'API facturée.

## Utilisation

Publier, dans une issue ou une PR, un commentaire qui **commence** par la commande du pont, suivie d'une tâche précise.
Une mention au milieu d'un texte, d'un rapport ou d'une citation ne lance rien. Exemple :

```text
/claude Lis AGENTS.md et l'issue #377. Vérifie si un test E2E couvre les quatre profils d'accueil. Si la couverture manque,
ajoute uniquement les tests nécessaires sur une branche dédiée, lance les contrôles disponibles et rapporte les résultats
exacts. Ne fusionne pas et ne déploie pas.
```

Attention : les connecteurs (ChatGPT, outils de session) publient **au nom du propriétaire**. Un de leurs commentaires qui
commence par la commande lance le pont, donc consomme des crédits ou l'abonnement. Ne jamais commencer un rapport par la commande.

## Garde-fous du workflow

- Déclenchement unique : un commentaire créé (`issue_comment`). Pas de `pull_request_target`, pas de planification.
- Le commentaire vient du compte propriétaire **et commence** par la commande. L'action vérifie en plus que l'auteur a un
  droit d'écriture et ignore les bots (réglage par défaut).
- Sur une PR, seules les PR ouvertes par le propriétaire sont acceptées : le code d'une PR tierce (fork, dépendance) ne doit pas
  s'exécuter, via les tests, avec les secrets du dépôt dans l'environnement.
- Droits par défaut en lecture seule ; le job demande `contents`, `pull-requests` et `issues` en écriture, `id-token`
  (jeton d'application GitHub) et `actions: read` (lecture des résultats de CI).
- Outils : fichiers, git en lecture, `git add` et `git commit`, tests, Ruff, Bandit et `node --check`. Retirés : `pip install`
  (code arbitraire avec les secrets en mémoire ; les dépendances sont installées avant), `git checkout`, `git switch` et
  `git branch` (elles permettraient de préparer une poussée sur `main`). `WebFetch` et `WebSearch` sont refusés par l'action.
- Les trois actions tierces sont épinglées par commit (Dependabot propose les mises à jour). Le chemin du script de poussée n'est
  plus écrit en dur : l'action ajoute elle-même l'outil avec le bon chemin.
- Un seul run à la fois par issue ou PR ; durée limitée à 20 minutes et 20 tours.
- Une exécution qui échoue (limite d'usage, secret absent ou expiré, délai) publie un commentaire d'échec dans la conversation.
- L'application GitHub ne peut pas modifier `.github/workflows/` : le workflow ne peut pas être modifié par le pont.

## Reprise sans doublon

1. Avant de relancer une tâche, chercher une branche `claude/...` ou une PR qui la traite déjà (GitHub conserve tout).
2. Chaque exécution réussie laisse un commentaire de suivi ; chaque échec laisse un commentaire d'échec avec le lien du run.
3. Si deux commandes attendent derrière une exécution en cours sur la même conversation, GitHub ne garde que la dernière :
   renvoyer la commande manquante. Les commentaires de bots n'évincent jamais une commande.
4. Le pont ne tourne pas « en arrière-plan » : sans commentaire de commande, aucun agent ne travaille.

## À configurer par le propriétaire

- **Protection de la branche `main`** (Settings → Branches ou Rulesets) : exiger une PR, les contrôles `pytest` et `e2e`, et interdire
  les poussées directes et forcées. C'est indispensable : le script de poussée de l'action accepte n'importe quel nom de branche
  valide, `main` compris ; seule la protection GitHub l'interdit réellement.
- **Un des deux secrets** (voir le tableau) et, pour l'API, une limite de dépense mensuelle.
- **L'application GitHub Claude** installée sur le dépôt (elle l'est : `claude[bot]` a répondu) et GitHub Actions autorisé.
- Optionnel, à tester lors d'un run avec écriture : `persist-credentials: false` à l'étape de checkout, pour que le jeton de
  l'étape `pip install` ne reste pas dans la configuration git. Non appliqué ici faute de test réel.

## Limites connues

- Les tests lancés par Claude exécutent du code du dépôt avec les secrets en mémoire : d'où la restriction aux PR du propriétaire.
- Le pont ne remplace pas la CI : `pytest`, `e2e` (44 tests, Playwright absent du pont) et CodeQL tournent sur chaque PR.
- Aucune fusion ni déploiement automatique : chaque fusion sur `main` déclenche un déploiement Render, donc se fait après relecture.
