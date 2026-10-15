---
name: conseil-hebdo
description: Conduire la réunion hebdomadaire de l'entreprise d'agents de Teranga AI - état de la production, indicateurs, avancement du plan de PR, choix des sujets de la semaine et décisions à demander au propriétaire. À utiliser chaque lundi, ou quand le propriétaire demande « où en est le projet ».
---

# Conseil de la semaine

Le chef de projet (la session Claude Code principale) conduit la réunion. Le propriétaire décide. Les agents
rapportent. Trois agents en parallèle au maximum.

## 1. Lire l'état (en parallèle)
- `gardien-prod` : santé de la production depuis le dernier conseil (déploiements, 5xx, WORKER TIMEOUT, mémoire).
- `analyste` : tableau des indicateurs sur 7 jours, comparé à la semaine précédente.
- `seo-visibilite` : audit du lundi.

Pendant ce temps : lister les PR ouvertes, leur CI et leurs relectures ; relire le plan de PR du dernier rapport d'audit.

## 2. Décider de la semaine
- Choisir **trois sujets au plus**, dans l'ordre du plan, en commençant par ce qui est rouge en production.
- Pour chaque sujet : quel agent le réalise (`developpeur`, `qualite-ia`, `voix`, `seo-visibilite`,
  `verificateur-reperes`, `chef-produit`, `partenariats`, `communication`), quels fichiers il touche (jamais deux
  agents sur le même fichier), quelle preuve dira qu'il est fini.
- Un sujet bloqué (source officielle inaccessible, décision du propriétaire, accord d'un partenaire) n'est pas lancé :
  il va dans les questions.

## 3. Rendre compte au propriétaire
Un message court, en français, sans jargon :
1. **Production** : OK, À SURVEILLER ou ALERTE, avec le chiffre qui le justifie.
2. **Indicateurs** : trois chiffres qui ont bougé, mesurés, avec leur période.
3. **Fait cette semaine** : PR fusionnées (lien), PR prêtes qui attendent son accord.
4. **Prévu** : les trois sujets choisis et l'agent de chacun.
5. **Ses décisions** : questions fermées (oui ou non, A ou B), avec la recommandation.

## Règles
- Rien n'est « fini », « vert » ou « en ligne » sans la preuve fraîche (skill `verifier-avant-d-annoncer`).
- Le chef de projet fusionne seulement ce que la règle en vigueur lui permet ; le reste attend le propriétaire.
- Aucun message commercial envoyé, aucune publication, aucun achat, aucun changement de DNS, de secret ou de réglage :
  ce sont des actions du propriétaire, que le conseil prépare.
- Un agent coupé en route (redémarrage, limite de session) : reprendre son travail depuis sa branche poussée, ou le
  refaire en petites étapes notées au fur et à mesure.
