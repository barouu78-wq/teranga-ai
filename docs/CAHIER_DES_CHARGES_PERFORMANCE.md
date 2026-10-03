# Cahier des charges — Performance et rapidité Teranga AI

## 1. Objectif

Réduire la latence perçue du chat sans dégrader la fiabilité, la sécurité ni la qualité des réponses.

## 2. Cibles de production

| Indicateur | Cible |
|---|---:|
| TTFB question simple | <= 1,5 s |
| TTFB question dynamique avec web | <= 3,5 s |
| Réponse complète question simple | <= 5 s |
| Réponse complète complexe | <= 10 s |
| Timeout OpenAI | <= 20 s |
| Enrichissements images/cartes | jamais bloquants pour le premier texte |
| 0 erreur sur requête simple | obligatoire |

Les mesures doivent être prises sur la production Coolify et complétées par les logs `X-Response-Time-ms`, `chat_ttfb_ms` et `chat_model_startup_ms`.

## 3. Règles d'architecture

1. Une question simple utilise le modèle rapide.
2. Le modèle complexe est réservé aux vrais besoins multi-étapes.
3. Le web est utilisé uniquement quand l'information est réellement dynamique ou explicitement vérifiée.
4. Les images et cartes restent des enrichissements indépendants et ne doivent pas retarder le premier texte.
5. Le streaming doit commencer dès réception du premier delta du modèle.
6. Aucun appel réseau secondaire ne doit être exécuté avant le premier texte.
7. Les historiques envoyés au modèle restent bornés.
8. Chaque optimisation doit avoir un test automatisé et un indicateur observable.

## 4. Plan d'exécution

### Phase P0 — Mesurer
- Exploiter les métriques existantes.
- Tester: question simple, question de suivi, question web, itinéraire, question avec images.
- Identifier précisément: parsing, TTFB modèle, web, enrichissements, réponse finale.
- Ne pas optimiser à l'aveugle.

### Phase P1 — Chemin rapide
- Réserver le modèle complexe aux demandes réellement multi-étapes.
- Éviter les déclencheurs trop larges de deep reasoning.
- Garder `reasoning=low` pour le chemin standard.
- Réduire les tokens de sortie pour les questions simples si les tests montrent que c'est sans impact qualité.
- Ajouter des tests de non-régression sur la sélection du modèle.

### Phase P2 — Web plus intelligent
- Conserver le web pour météo, prix, horaires, transport, réservations, actualités, etc.
- Ne pas lancer une recherche web pour une question statique simplement parce qu'un mot ambigu apparaît.
- Maintenir des domaines préférés par domaine métier.
- Mesurer le TTFB avec et sans web.

### Phase P3 — Enrichissements non bloquants
- Images et cartes en arrière-plan après le premier texte.
- Timeout strict par enrichissement.
- Aucun enrichissement ne doit empêcher une réponse textuelle.
- Tester les cas où images/cartes échouent.

### Phase P4 — Cache
- Cache court pour les données très répétées et peu sensibles: contexte Sénégal, résultats d'images, cartes si applicable.
- Redis si disponible en production.
- TTL courts et invalidation claire.
- Aucun cache de données personnelles ou de secrets.

### Phase P5 — Production Coolify
- Vérifier workers Gunicorn, CPU/RAM et saturation.
- Vérifier Redis partagé si activé.
- Vérifier logs et métriques après déploiement.
- Conserver les ports de production publics uniquement sur 80/443.

### Phase P6 — Validation finale
- Test de charge léger et contrôlé.
- Comparaison avant/après.
- Validation fonctionnelle: FR/EN/WO/FF, web, suivi conversationnel, images, cartes, sécurité.
- Déploiement uniquement après CI verte.

## 5. Definition of Done

Une phase est terminée uniquement si:
- le code est testé;
- la CI est verte;
- les métriques sont comparables;
- aucune régression fonctionnelle n'est détectée;
- le déploiement Coolify est terminé;
- la production répond correctement.

## 6. Ordre impératif

`P0 Mesurer -> P1 Chemin rapide -> P2 Web -> P3 Enrichissements -> P4 Cache -> P5 Coolify -> P6 Validation`

Aucune optimisation ne doit être faite en supprimant arbitrairement des fonctionnalités ou la sécurité.
