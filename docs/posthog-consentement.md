# PostHog — activation avec consentement

## Variables Render à configurer après validation de la PR

Ne pas activer le suivi avant d'avoir confirmé la région du compte PostHog dans ses paramètres.

- `POSTHOG_PROJECT_KEY` : clé publique de projet commençant par `phc_`. Ne pas la recopier dans Git.
- `POSTHOG_API_HOST` : origine officielle d'ingestion affichée par PostHog pour ce projet (HTTPS, sans chemin).
- `POSTHOG_ASSET_HOST` : origine officielle du SDK PostHog correspondant à la région du projet (HTTPS, sans chemin).

Si une variable manque ou si les hôtes ne sont pas des origines HTTPS valides, l'intégration reste désactivée. N'utilise pas les anciennes variables `ANALYTICS_SCRIPT_URL` / `ANALYTICS_SITE_ID` pour PostHog.

## Confidentialité

- Le SDK tiers n'est chargé qu'après un choix explicite « Accepter les statistiques ».
- Le refus est mémorisé localement ; aucune requête PostHog n'est envoyée.
- Pas d'autocapture, de capture de page automatique, de replay, ni de profils de personnes.
- Seul un événement `$pageview` avec le chemin sans paramètres de requête est envoyé après acceptation.
- La persistance PostHog est en mémoire et l'option d'envoi de l'adresse IP est désactivée.
- Le lien « Paramètres de confidentialité » permet de rouvrir le panneau. Pour retirer son accord, choisir « Refuser ».
- Les journaux techniques du serveur restent séparés de PostHog.

## Vérifications

1. Tester en navigation privée : aucun chargement du SDK avant consentement.
2. Refuser : vérifier dans l'onglet Réseau qu'aucune requête vers les hôtes PostHog ne part.
3. Accepter : vérifier qu'un seul `$pageview` est reçu et qu'il n'y a pas de capture automatique.
4. Vérifier le refus et l'acceptation sur mobile et sur les pages en français/anglais.
5. Confirmer l'avis de confidentialité/cookies et les exigences légales applicables avant activation publique.

Cette PR ne modifie pas `main` et ne déclenche aucun déploiement. Les variables Render ne doivent être ajoutées qu'après vérification de la région PostHog et validation du changement.
