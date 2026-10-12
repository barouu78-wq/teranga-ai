---
name: verifier-avant-d-annoncer
description: Avant de dire qu'un travail de Teranga AI est fini, corrigé, vert ou en ligne, lancer la commande qui le prouve et lire son résultat. À utiliser avant chaque commit, PR, fusion, message au propriétaire ou compte rendu d'agent.
---

# Vérifier avant d'annoncer

Adapté de Superpowers (`verification-before-completion`), licence MIT : voir `.claude/skills/LICENCE-superpowers.txt`.
Ce skill complète la règle « Réussi ≠ ignoré ≠ non exécuté » d'`AGENTS.md`.

**Règle : pas d'annonce sans preuve fraîche.** Une commande lancée avant le dernier changement ne prouve plus rien.

## Avant chaque annonce
1. Trouver la commande qui prouve ce qu'on va dire.
2. La lancer en entier, maintenant.
3. Lire la sortie : nombre de tests réussis, échoués et ignorés, code de sortie.
4. Annoncer exactement ce que dit la sortie, chiffres compris. Si elle dit autre chose, annoncer l'état réel.

## Ce qui prouve quoi
| On annonce | Preuve | Ne suffit pas |
|---|---|---|
| Tests verts | `pytest` : 0 échec, chiffres cités | une exécution antérieure au dernier changement |
| Tests e2e verts | `E2E_REQUIRED=1 … -rs` : 0 échec, 0 ignoré | des tests e2e ignorés faute de navigateur |
| Bug corrigé | le test du bug : rouge avant, vert après | « le code a changé » |
| CI verte | les contrôles du **dernier** commit de la PR | les contrôles d'un commit précédent |
| En ligne | déploiement Render « live » sur le bon commit, puis la page ou le journal | « fusionné » |
| Un agent a fini | `git diff` et les fichiers relus | le rapport de l'agent |
| Demande remplie | la demande relue point par point | « les tests passent » |

## Signaux d'alerte
- « ça devrait marcher », « normalement », « parfait ! » avant d'avoir regardé.
- Pousser ou fusionner sans avoir relancé les contrôles.
- Croire sur parole le rapport d'un agent ou d'un bot.
- Ne pas pouvoir vérifier (réseau bloqué, outil absent) et annoncer quand même. Dans ce cas, écrire
  « non vérifié, parce que… ».
