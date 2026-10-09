# Connecteurs de recherche externe — Teranga AI

## Étape 1 : connecteurs prêts à configurer

Le module `services/external_research.py` ajoute des appels serveur facultatifs vers :

- **Tavily** : recherche web (`search_tavily`)
- **Exa** : recherche sémantique (`search_exa`)
- **Firecrawl** : extraction Markdown d'une URL HTTP(S) (`scrape_firecrawl`)

Ils utilisent la dépendance `httpx` déjà présente dans le projet. Aucune clé n'est requise au démarrage, aucun appel réseau n'est effectué à l'import et aucune clé n'est envoyée au navigateur. Les erreurs de fournisseur sont normalisées sans recopier les corps de réponse susceptibles de contenir des informations sensibles.

La fonction `configured_providers()` indique seulement la présence de variables d'environnement. Elle ne valide pas les clés, ne teste pas les comptes et n'affirme pas qu'une intégration est active.

## Configuration

Dans les variables d'environnement du service de production, ajouter uniquement les clés des fournisseurs activés :

- `TAVILY_API_KEY`
- `EXA_API_KEY`
- `FIRECRAWL_API_KEY`

Ne jamais placer les vraies clés dans `.env.example`, GitHub, le navigateur ou les messages de chat. Utiliser les secrets du gestionnaire de déploiement.

## Ce qui reste à faire avant la production

Cette PR installe les connecteurs de base, mais ne branche pas encore automatiquement les réponses du chat sur ces fournisseurs et n'active aucun compte tiers.

1. Fusionner après succès des contrôles CI et tests.
2. Ajouter les secrets de production dans le gestionnaire d'environnement.
3. Ajouter une couche d'orchestration côté serveur : choix du fournisseur selon l'intention, délais maximum, limite de résultats, cache, attribution des sources et solution de repli.
4. Ajouter des tests d'intégration contrôlés avec clés valides, sans exposer les secrets.
5. Intégrer séparément Google Search Console via OAuth/service account autorisé et tester les permissions sur la propriété du site.
6. Intégrer Semrush selon le produit et les droits API du compte. La présence de `SEMRUSH_API_KEY` ne constitue pas une intégration Semrush.

Les appels réseau sont déclenchés uniquement par une invocation explicite des fonctions du module. Toute intégration au chat doit aussi conserver les limites de débit, les délais et les règles de sécurité existantes.
