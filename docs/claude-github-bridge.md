# Pont GitHub ↔ Claude Code pour Teranga AI

Ce pont permet de demander une intervention de Claude Code depuis un commentaire GitHub, puis de conserver son travail dans le dépôt pour revue par ChatGPT et le propriétaire.

## Activation requise (une seule fois)

1. Examiner et fusionner la PR qui ajoute `.github/workflows/claude-bridge.yml`.
2. Installer l'application GitHub officielle Claude sur le dépôt : https://github.com/apps/claude
3. Depuis un terminal local où Claude Code fonctionne avec un abonnement Pro/Max éligible, exécuter `claude setup-token` et suivre les instructions officielles. Ne jamais coller le jeton dans une issue, un commentaire, un commit ou une conversation.
4. Dans GitHub, ouvrir **Settings → Secrets and variables → Actions → New repository secret**.
5. Nom du secret : `CLAUDE_CODE_OAUTH_TOKEN`. Valeur : le jeton généré localement. Ne jamais l'ajouter au dépôt.
6. Vérifier que GitHub Actions est autorisé à s'exécuter pour ce dépôt.

Documentation officielle : https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md

## Utilisation

Dans une issue ou une PR, publier un commentaire contenant `/claude` suivi d'une tâche précise. Pour éviter les exécutions involontaires, le workflow n'accepte que les commentaires de la personne propriétaire du dépôt.

Exemple :

```text
/claude Lis AGENTS.md et l'issue #377. Vérifie si un test E2E couvre les quatre profils d'accueil. Si la couverture manque, ajoute uniquement les tests nécessaires sur une branche dédiée, lance les contrôles disponibles et rapporte les résultats exacts. Ne fusionne pas et ne déploie pas.
```

Claude peut créer/mettre à jour une branche et proposer des changements, mais il ne doit pas fusionner ni déployer. ChatGPT examine ensuite la PR et les preuves de CI.

## Limite importante

Ce pont ne contourne pas les limites d'utilisation de Claude. Le jeton OAuth reste soumis aux conditions, quotas et limites applicables au compte Claude. Si l'utilisation est épuisée, il faut attendre la réinitialisation ou choisir explicitement une méthode API facturée séparément. Aucun achat ni coût API n'est déclenché par ce document lui-même.

## Sécurité

- Aucun secret dans le code ou les commentaires.
- Déclenchement uniquement sur commande explicite du propriétaire.
- Pas de push sur `main`, pas de fusion automatique, pas de déploiement.
- Ne jamais affaiblir les tests, TLS ou les contrôles de sécurité.
- Examiner chaque diff et attendre que les checks requis soient verts.
