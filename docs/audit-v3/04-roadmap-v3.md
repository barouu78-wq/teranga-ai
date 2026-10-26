# Audit V3 — 04. Feuille de route V3 : priorités, dépendances, risques

Date : 26 octobre 2026. S'appuie sur :
- `01-audit-technique.md` ;
- `02-benchmark-ia-senegal.md` ;
- `03-benchmark-teranga.md`.

Aucun objectif chiffré n'est déclaré atteint : chaque cible se mesure avant et après.

## 1. Le constat qui commande tout

- **Teranga fonctionne, mais presque personne ne l'utilise** : 13 questions au chat en 7 jours.
- Sans trafic, on ne peut mesurer ni la vitesse réelle, ni la justesse perçue, ni la conversion.
- La V3 doit donc d'abord **corriger ce qui est sûr** (exactitude, sécurité, accessibilité) et **amener de vrais
  utilisateurs**, avant d'ajouter des fonctions.
- C'est aussi la règle du propriétaire jusqu'au premier partenaire payant (#496) : aucune nouvelle fonction, ni
  nouvelle langue, ni publicité avant d'avoir mesuré.

## 2. Les trois améliorations à plus fort impact, proposées dans des PR séparées

| # | Amélioration | Pourquoi elle d'abord | Preuve | PR | Décision |
|---|---|---|---|---|---|
| 1 | **Sécurité** : un lien partagé ne peut plus donner de consignes à l'IA | Protège les utilisateurs d'une escroquerie (« payer au numéro X ») ; P1 de la revue de sécurité | Test reproduit puis corrigé | `secu/contexte-interface-en-donnees` | Go du propriétaire (change le contexte de l'IA) |
| 2 | **Exactitude du calcul** : « Convertis 50 000 FCFA en euros », « 10 000 F CFA en € » | Conversion euro ↔ FCFA = besoin n° 1 de la diaspora ; réponse exacte, immédiate, sans coût d'IA | Banc V3 : 3 formulations manquées, 5 tests rouges puis verts | #539 | Go du propriétaire (change la réponse) |
| 3 | **Accessibilité** : glyphes muets pour les lecteurs d'écran, marque non traduite | Personnes malvoyantes ; aucun changement visible | Règles d'interface de Vercel ; test rouge puis vert | #538 | Fusion possible sans Go (invisible) |

## 3. Liste des corrections

### P0 — bloquant ou exploitable maintenant

Aucun P0 trouvé : ni sécurité, ni panne, ni erreur factuelle grave.

### P1 — à traiter dans la V3

| Sujet | Action | Qui | Dépend de |
|---|---|---|---|
| Sécurité P1-1 : `main` non protégée + pont Claude avec jeton d'écriture | Protéger `main` dans GitHub (PR obligatoire, tests et e2e exigés) ; PR `persist-credentials: false` | **Propriétaire** (réglage) + PR | — |
| Sécurité P1-2 : lien partagé injecté dans les consignes | Corrigé (§2) | PR | Go |
| Sécurité P1-3 : 8 requêtes longues bloquent le site | Limite de requêtes en cours par IP et plafond global, réponse 429/503 rapide | PR | Conception courte |
| Sécurité P1-4 : pas de plafond global de dépense IA | Compteur quotidien global (Redis) puis bascule sur la base vérifiée ; budgets et alertes chez OpenAI et Anthropic | PR + **propriétaire** | — |
| Exactitude : TER jusqu'à l'AIBD (en service depuis le 28 septembre 2026 selon l'APS) | Mettre à jour `services/seo.py` et `services/practical_facts.py` avec la source officielle | PR | **Autoriser `aps.sn`** dans le réseau de la session |
| Calcul : conversions manquées | Corrigé (#539) | PR | Go |
| Recherche web proposée sur des questions stables (22 sur 100) | Mesurer d'abord en production la part de recherches réellement faites et leur temps ; puis restreindre les déclencheurs aux sujets sans repère vérifié | Mesure puis PR | Trafic réel |
| Coût de Claude : `max_tokens` 4 000 contre 800 ou 1 200 | Mesurer longueur et coût des premières réponses Claude ; aligner si rien ne le justifie | Mesure puis PR | Premières questions réelles |
| Voix : délai de 30 s sans nouvelle tentative (`/tts`) | Délai plus court et une nouvelle tentative | PR | Choix du délai avec le propriétaire |
| Mesure : journaux gardés 7 jours, planificateur sans ligne de latence | Export hebdomadaire des lignes `latence` ; ligne `latence route=trip-planner` | PR | — |

### P2 — utile, non urgent

| Sujet | Action |
|---|---|
| Émojis comme icônes (🚀 🔎 🤝 📍 🎯 🌍) | Icônes dessinées au style Nuit dorée (**Go** : change l'écran) |
| CSP `'unsafe-inline'` sur 40 pages | Nonce partout |
| 6 routes POST hors `require_json_post` ; JSON imbriqué → 500 | Décorateur commun |
| Blocage par IP (CGNAT, IPv6) | IP + identité, regroupement /64 |
| `/explorer-image` à requêtes libres | Titres de la base seulement |
| Liens de partage sans expiration | Expiration et neutralisation |
| Actions GitHub non épinglées par commit ; dépendances de dev non figées | Épingler |
| Script d'audience possible sur `/stats-*` | Exclure |
| Hygiène (`.gitignore` des clés Android, `# nosec` sans raison) | Compléter |
| Réponses prêtes : salutation, anglais, wolof | À étudier après mesure du trafic réel (choix de #503 à revoir avec le propriétaire) |
| Cache des photos en mémoire par processus | Cache partagé dans Redis (gain mesuré : environ 730 ms par photo reprise, 1 cas) |

## 4. Les six priorités du rapport V3, phase par phase

| Phase | État au 26 octobre | Suite |
|---|---|---|
| A. Audit technique et produit | Fait (01) | Relancer l'agent analyste (indicateurs de trafic) |
| B. Banc mesurable | Routage mesuré sur 100 questions (03) ; justesse non mesurée | Passer le banc par le vrai modèle : **budget API à valider** |
| C. Corrections prioritaires | 3 PR prêtes (§2) | P1 de sécurité ensuite |
| D. Intelligence V3 (routage, sources, action) | Diagnostic : web trop large, réponses prêtes partielles | Après mesure du trafic réel |
| E. Langues et voix | Benchmark fait (02) : Kiriku, Oolel, AWA, Omnilingual ASR ; licences à clarifier ; aucun modèle hébergeable sur l'offre Render actuelle | Banc vocal hors production avec enregistrements consentis ; demande de licence écrite à AI Hub Sénégal |
| F. Validation commerciale | Plan diaspora en cours (#417) ; 0 partenaire payant sur 3 (#496) | Testeurs Android et premiers vrais utilisateurs d'abord |

## 5. Risques

- **Mesurer sans trafic** : toute optimisation de vitesse ou de routage serait faite à l'aveugle. Mitigation : attendre
  au moins 20 mesures par groupe.
- **Licences des modèles sénégalais** : licences non lues, ou AGPL, ou « non commercial ». Aucune intégration en
  production sans licence écrite et sans accord sur les voix des utilisateurs (loi 2008-12).
- **Coût de Claude Opus** : réponses plus longues, recherche web jusqu'à 3 fois par question ; sans plafond global
  (P1-4), un usage abusif n'a pas de limite de facture.
- **Réseau de la session** : les sources officielles sénégalaises sont bloquées, ce qui empêche de sourcer de
  nouveaux faits (TER, frais d'envoi, plafonds du mobile money).

## 6. Décisions attendues du propriétaire

1. Go pour la PR de sécurité (lien partagé) et pour #539 (conversions).
2. Protéger la branche `main` dans GitHub.
3. Fixer un budget ou des alertes de dépense chez OpenAI et Anthropic.
4. Autoriser `aps.sn` (et si possible `huggingface.co`) dans l'accès réseau de l'environnement.
5. Valider un budget API pour mesurer la justesse des 100 réponses.
6. Ordre de la V3 : garder « premiers utilisateurs d'abord » (#417, #496), ou ouvrir le chantier voix (banc
   Kiriku et Oolel).
