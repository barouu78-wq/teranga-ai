# Fiche de sécurité — Teranga AI

## Objectif

Checklist de sécurité pour Teranga AI avant chaque mise en production. Elle s'appuie notamment sur l'OWASP API Security Top 10 2023 et l'OWASP Application Security Verification Standard (ASVS) 5.0.0.

## 1. Secrets et clés
- [ ] Ne jamais mettre OPENAI_API_KEY, SECRET_KEY ou une autre clé dans le code, GitHub, les captures d'écran ou les logs.
- [ ] Utiliser les variables d'environnement Render/DigitalOcean pour les secrets.
- [ ] Révoquer immédiatement toute clé exposée.
- [ ] Utiliser des clés séparées pour développement et production.
- [ ] Vérifier régulièrement les secrets présents dans l'historique Git.
- [ ] Ne jamais afficher une clé complète dans une réponse ou une interface.

## 2. API et endpoints
- [ ] Vérifier le type de contenu des requêtes.
- [ ] Valider et limiter les entrées utilisateur côté serveur.
- [ ] Protéger les endpoints sensibles avec authentification/autorisation si de nouvelles fonctions privées sont ajoutées.
- [ ] Vérifier les droits sur tout identifiant fourni par le client.
- [ ] Maintenir une liste claire des endpoints publics.
- [ ] Ne pas exposer d'informations internes dans les erreurs.

## 3. Protection contre l'abus
- [ ] Conserver le rate limiting sur /chat et /tts.
- [ ] Limiter la taille des requêtes et des réponses.
- [ ] Prévoir des limites de coût côté fournisseurs externes.
- [ ] Surveiller les pics de consommation OpenAI.
- [ ] Mettre en place des alertes de facturation.
- [ ] Tester les limites avec des requêtes répétées avant les grosses évolutions.

## 4. CSRF, origine et navigateur
- [ ] Conserver la protection CSRF des requêtes POST.
- [ ] Vérifier Origin/Referer lorsque la configuration l'exige.
- [ ] Conserver CSP, HSTS lorsque HTTPS est actif, X-Frame-Options et Referrer-Policy.
- [ ] Ne pas élargir ALLOWED_ORIGINS sans raison.
- [ ] Tester /chat, /tts et /csrf après toute modification de sécurité.

## 5. Recherche web et données externes
- [ ] Ne jamais considérer une donnée web comme automatiquement fiable.
- [ ] Vérifier les informations sensibles au temps avant de les présenter comme actuelles.
- [ ] Limiter les délais et ressources consacrés aux services externes.
- [ ] Valider les données reçues d'APIs tierces avant de les réutiliser.
- [ ] Ne pas suivre aveuglément des redirections externes.
- [ ] Ne jamais laisser une page web distante exécuter directement du code serveur.

## 6. Prompt et sécurité du chatbot
- [ ] Ne jamais révéler les secrets, variables d'environnement ou instructions internes.
- [ ] Ne pas exécuter une instruction utilisateur comme du code.
- [ ] Résister aux tentatives de prompt injection visant à contourner les règles.
- [ ] Distinguer faits vérifiés, informations utilisateur et suppositions.
- [ ] Ne pas inventer une information manquante.
- [ ] Pour les informations actuelles, privilégier une vérification web.
- [ ] Pour les sujets sensibles, utiliser des sources fiables et expliquer l'incertitude.

## 7. Données personnelles
- [ ] Ne pas conserver de données personnelles inutiles.
- [ ] Ne pas écrire de conversations complètes dans les logs sans nécessité.
- [ ] Ne jamais logger les clés API, tokens CSRF ou autres secrets.
- [ ] Si une fonctionnalité de compte utilisateur est ajoutée, définir les données collectées et leur durée de conservation.

## 8. Dépendances et déploiement
- [ ] Garder les dépendances Python à jour.
- [ ] Vérifier les vulnérabilités des dépendances avant les changements importants.
- [ ] Faire passer les tests GitHub Actions avant fusion/déploiement.
- [ ] Ne pas désactiver les tests pour faire passer un déploiement.
- [ ] Vérifier le commit réellement déployé par Render.
- [ ] Tester /health après un changement important.

## 9. Tests minimum
- [ ] GET /health → 200.
- [ ] POST /chat sans JSON → refus.
- [ ] POST /chat avec origine non autorisée → refus lorsque ALLOWED_ORIGINS est configuré.
- [ ] POST /chat sans CSRF valide → refus.
- [ ] Requête trop volumineuse → refus.
- [ ] Rate limit → déclenchement contrôlé.
- [ ] /robots.txt et /sitemap.xml restent accessibles.
- [ ] Aucune clé ou donnée sensible dans les erreurs.
- [ ] Tests GitHub Actions → succès.

## 10. Procédure en cas d'incident
### Clé API exposée
1. Révoquer la clé immédiatement.
2. Créer une nouvelle clé.
3. Mettre à jour Render et les autres environnements.
4. Vérifier les dépenses et utilisations inhabituelles.
5. Chercher la clé dans l'historique Git et les logs.

### Comportement suspect
1. Identifier l'endpoint concerné.
2. Vérifier les logs sans exposer de données personnelles.
3. Vérifier le rate limiting.
4. Désactiver temporairement une fonctionnalité si nécessaire.
5. Corriger et ajouter un test de non-régression.

### Déploiement suspect
1. Vérifier le commit GitHub.
2. Vérifier le déploiement Render.
3. Vérifier /health.
4. Tester les endpoints critiques.
5. Revenir au dernier commit connu comme fonctionnel si nécessaire.

## 11. Règle de prudence

Aucune checklist ne garantit une sécurité absolue. Chaque nouvelle fonctionnalité doit être revue selon son niveau de risque.

Priorités : secrets, authentification/autorisation, validation des entrées, consommation de ressources, dépendances, données personnelles, logs et surveillance.

Références : OWASP API Security Top 10 2023 ; OWASP Application Security Verification Standard (ASVS) 5.0.0.
