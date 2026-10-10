# Pont ChatGPT ↔ Claude Code

Deux IA travaillent sur Teranga AI avec le propriétaire. Elles ne se parlent pas en direct : **GitHub est leur mémoire commune**.
Une tâche, son contexte, le résultat, la branche et la PR y restent même si l'une des deux est hors service (limite d'usage,
session coupée). Ce document dit qui fait quoi et comment se passer le relais sans doublon ni malentendu.

## Ce que ce pont est, et n'est pas

- **Est** : des tickets, commentaires, PR et journaux sur GitHub, avec un format de message commun.
- **N'est pas** : une liaison en temps réel. Aucune des deux IA n'en réveille une autre toute seule. Sans action du propriétaire
  ni commande du pont (voir plus bas), rien ne tourne « en arrière-plan ».
- Le relais automatique qui existe : un commentaire du propriétaire qui **commence** par la commande du pont lance Claude Code
  (voir [claude-github-bridge.md](claude-github-bridge.md) : coût, limites, garde-fous).

## Qui fait quoi

| Acteur | Rôle |
|---|---|
| **Propriétaire** | Décide, valide et fusionne. Seul à toucher au DNS, aux secrets, aux réglages GitHub, Render et Google Play. |
| **ChatGPT** | Pilote les priorités et le commercial, relit, rédige les tâches. Pas de fusion ni de déploiement. |
| **Claude Code** | Code, tests, PR, audits reproductibles. Pas de fusion ni de déploiement sans validation explicite du propriétaire. |

## ChatGPT → Claude Code

1. **Tâche courte à lancer tout de suite** : un commentaire sur une issue ou une PR **du propriétaire**, qui commence par la commande
   du pont, suivie d'**une seule tâche précise** (une vérification, une correction). Les « missions » en plusieurs volets ont toutes
   échoué sur la limite de 20 tours, avec un coût perdu : les découper.
2. **Tâche qui peut attendre** : ouvrir un ticket avec le formulaire « Relais entre agents » (menu *New issue*). Claude Code le
   reprend à sa prochaine session. Rien ne coûte tant qu'aucune commande n'est lancée.

## Claude Code → ChatGPT

- Un commentaire sur le ticket ou la PR, qui commence par « À l'attention de ChatGPT : », suivi du format de rapport ci-dessous.
- Le journal commun est l'issue #387 : chaque compte rendu y est posté.
- ChatGPT ne lit GitHub que lorsque le propriétaire (ou son connecteur) l'invoque. Si son relecteur automatique a atteint sa
  limite d'usage, le propriétaire relaie.
- **Ne jamais commencer un rapport par la commande du pont** : les commentaires publiés par les connecteurs le sont au nom du
  propriétaire et lanceraient un run facturé.

## Format commun d'une tâche

```text
Objectif : une phrase.
Contexte : liens (issue, PR, run), état de main.
Contraintes : fichiers permis ou interdits, pas de secret, pas de fusion.
Résultat attendu : ce qui prouve que c'est fait (tests, PR, capture).
```

## Format commun d'un rapport

Repris de [.github/agents/README.md](../.github/agents/README.md) :

```text
Rôle responsable :
Problème et impact :
Preuve reproductible :
Cause confirmée / hypothèse :
Correction proposée :
Tests et résultats exacts :
PR / artefacts :
Risques et prochaines étapes :
```

Chaque affirmation est classée **confirmé**, **probable** ou **non vérifié**. Un contrôle est **exécuté et réussi**, **exécuté et
échoué**, **ignoré** (avec la raison) ou **non exécuté** (avec l'outil manquant) : jamais « vert » pour un contrôle qui n'a pas tourné.

## Règles communes

- Aucun secret (clé, jeton, mot de passe, fichier de signature) dans un ticket, un commentaire, un commit ou une conversation.
- Aucune fusion ni déploiement sans validation explicite du propriétaire : chaque fusion sur `main` déploie en production.
- Une PR par objectif ; aucun test désactivé ou assoupli pour passer ; aucune vérification TLS contournée.
- Aucun fait inventé : un repère qui peut changer est « à vérifier », toute donnée nouvelle est sourcée.
- Aucun achat ni abonnement déclenché sans accord du propriétaire.

## Continuité quand une IA n'est plus disponible

1. Le travail est sur GitHub : lire le ticket, la branche et la PR, pas la mémoire d'une conversation.
2. **Avant de relancer une tâche, chercher une branche ou une PR qui la traite déjà** : deux envois de la même commande ont produit
   deux branches identiques.
3. Reprendre au dernier état prouvé (un test vert, un commit poussé), pas au dernier état annoncé.
4. Si une IA ne peut plus répondre, le ticket reste ouvert avec ce qui est fait et ce qui reste ; le propriétaire peut le confier à
   l'autre ou attendre la réinitialisation. Aucune limite d'usage n'est contournée.

## À coller dans les instructions de ChatGPT

```text
Tu travailles avec Claude Code sur le dépôt barouu78-wq/teranga-ai. GitHub est la mémoire commune : lis le ticket, la PR et l'issue
#387 avant d'agir. Tu ne fusionnes ni ne déploies jamais ; tu n'écris, ne demandes et n'affiches jamais de secret.
Quand tu confies une tâche à Claude Code : une seule tâche précise (objectif, contexte, contraintes, résultat attendu), en commentaire
qui commence par la commande du pont sur une issue ou une PR du propriétaire, ou avec le formulaire « Relais entre agents ».
Quand tu rapportes : confirmé / probable / non vérifié ; exécuté et réussi / échoué / ignoré / non exécuté ; ne commence jamais un
rapport par la commande du pont. Cherche une branche ou une PR existante avant de relancer une tâche.
```

## Ce qui n'est pas vérifié

- Que ChatGPT suive ce protocole : son côté se règle dans ses propres instructions, que ce dépôt ne contrôle pas.
- Le pont durci (fusionné le 10 octobre) n'a pas encore été relancé par un commentaire réel depuis sa fusion : un essai en lecture
  seule, sur une tâche courte, le confirmera.
