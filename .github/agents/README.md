# Organisation des agents Teranga AI

Ce document définit la répartition des responsabilités, les règles de coordination et les critères de validation. Les fichiers `.github/agents/*.agent.md` décrivent les rôles ; ils ne signifient pas, à eux seuls, que des agents autonomes tournent en permanence. L'exécution dépend des outils et workflows réellement activés.

## 1. Répartition des rôles

### Agent SEO — acquisition et visibilité
**Responsable :** indexabilité et croissance organique.
- Contrôler robots.txt, sitemap XML, canonicals, redirections, métadonnées, données structurées et liens internes.
- Prioriser les pages utiles au Sénégal, à Dakar et à la diaspora, sans créer de pages artificielles.
- Analyser Search Console/Semrush uniquement si les identifiants et accès sont configurés et fonctionnels.
- Livrer un rapport avec preuves, URL concernées, impact, effort et indicateurs de suivi.
- Ne pas modifier DNS, domaine, secrets ou paramètres de production.

### Agent Performance — vitesse, disponibilité et infrastructure applicative
**Responsable :** latence, fiabilité et coût.
- Mesurer la disponibilité et les temps de réponse avant/après toute optimisation.
- Examiner les erreurs HTTP/TLS, délais, cache, appels réseau, CPU/RAM et journaux sans données sensibles.
- Séparer les problèmes applicatifs des problèmes DNS, certificat, proxy ou hébergeur.
- Fournir une procédure de retour arrière pour toute modification à risque.
- Ne jamais contourner la validation des certificats TLS pour faire passer un contrôle.

### Agent Développeur — correction et implémentation
**Responsable :** code et correctifs.
- Reproduire les anomalies signalées et lire AGENTS.md et les tests existants.
- Implémenter la correction minimale, ajouter des tests de régression et documenter les risques.
- Travailler dans une branche dédiée et ouvrir une PR ; jamais de push direct sur main.
- Ne pas déclarer une correction terminée sans tests et preuve vérifiable.

### Agent QA — qualité et décision de validation
**Responsable :** tests indépendants et non-régression.
- Vérifier les tests unitaires, intégration, E2E, accessibilité et parcours critiques.
- Tester les profils Touriste, Résident, Diaspora et Commerçant, le chat et la pertinence géographique des photos.
- Ne pas supprimer ni affaiblir un test pour obtenir un résultat vert.
- Publier les commandes, résultats, échecs et limites de couverture.
- Ne fusionne pas et ne déploie pas ; signale les contrôles bloquants.

## 2. Ordre de travail et passages de relais

1. **SEO ou Performance détecte** un problème et ouvre un rapport reproductible, avec URL, heure, statut, preuve et impact.
2. **Développeur diagnostique** la cause et propose un correctif isolé dans une branche/PR.
3. **QA vérifie indépendamment** la reproduction, la régression et les tests associés.
4. **SEO/Performance recontrôle** le résultat sur les critères de leur domaine, notamment sur le site public lorsque cela est sûr et accessible.
5. **Fusion** uniquement lorsque tous les checks requis sont verts, les changements sont examinés et les risques sont documentés. Sinon, la PR reste ouverte.

## 3. Priorités actuelles

### P0 — HTTPS / certificat
- Confirmer le certificat réellement présenté pour `teranga-ai.fr` et `www.teranga-ai.fr`, sa chaîne de confiance, son nom et son expiration.
- Distinguer DNS, proxy/CDN, Render et application ; ne pas présumer la cause.
- Ne jamais demander à l'utilisateur d'ignorer l'avertissement du navigateur.
- Refaire un contrôle externe après toute correction d'hébergement.

### P1 — Sitemap XML
- Vérifier le corps brut de `/sitemap.xml`, le statut HTTP et le type de contenu.
- Valider la structure XML, les balises `<url>`, `<loc>` et `<lastmod>`, les dates ISO 8601 et l'absence de contenu concaténé ou mal formé.
- Vérifier que les URL canoniques utilisent le domaine principal en HTTPS.
- Ajouter un test automatisé de parsing XML et de cohérence du sitemap.

### P2 — Automatisation SEO et performance
- Exécuter le workflow planifié et sur les changements pertinents.
- Conserver les rapports comme artefacts, avec une durée de rétention définie.
- Distinguer clairement échec de disponibilité, erreur TLS, problème sitemap et seuil de latence.
- Une exécution échouée est une alerte à diagnostiquer, pas une validation réussie.

### P3 — Connexions externes
- Vérifier la présence et la validité des variables nécessaires à Search Console et Semrush dans l'environnement d'hébergement, sans afficher les valeurs secrètes.
- Si les accès ne sont pas configurés, signaler « non configuré » ; ne jamais prétendre qu'une collecte de données réelles a eu lieu.

## 4. Règles communes
- Une seule PR par objectif cohérent ; pas de changements non liés.
- Aucun secret dans les commits, rapports ou logs.
- Tests externes tolérants aux pannes transitoires, mais jamais au prix d'ignorer une erreur TLS.
- Chaque rapport distingue **confirmé**, **probable** et **non vérifié**.
- Aucune fusion ou annonce de succès sans résultats de CI vérifiables.
- Les workflows automatisés sont des contrôles planifiés ; ils ne constituent pas, à eux seuls, des agents IA capables de modifier le code de manière autonome.

## 5. Format obligatoire du rapport
- **Rôle responsable :**
- **Problème et impact :**
- **Preuve reproductible :**
- **Cause confirmée / hypothèse :**
- **Correction proposée :**
- **Tests et résultats exacts :**
- **PR / artefacts :**
- **Risques et prochaines étapes :**
