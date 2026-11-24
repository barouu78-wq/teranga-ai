# Banc qualité : premier passage réel (22 novembre 2026)

Questions : `tests/banc_qualite/questions.json` (50 questions, 10 catégories). Site interrogé : https://teranga-ai.fr,
par GitHub Actions (workflow `banc-qualite-reel`, passage n° 45075422082), avec l'accord du propriétaire. Le code en
ligne était celui de `main` après les PR #634 à #640.

Fichiers :
- `banc-2026-11-22-rapport.md` : les 50 réponses telles quelles, temps et contrôles automatiques ;
- `banc-2026-11-22-fiche-proposee.csv` : notes proposées par Claude, **à valider ou corriger par un humain**
  (`python scripts/banc_qualite.py noter docs/qualite/banc-2026-11-22-fiche-proposee.csv`).

## Mesuré par la machine

| | Valeur |
|---|---|
| Réponses en échec ou vides | 0 / 50 |
| Réponses dégradées (secours sans IA) | 0 / 50 |
| Recherche web utilisée | 6 / 50 |
| Interdits trouvés (faux numéro d'urgence, numéro inventé, dose en mg…) | 0 |
| Attendus manquants | 2, relus à la main : réponses justes, attendus trop stricts (corrigés, voir plus bas) |
| Premier mot, médiane | 1,2 s |
| Réponse complète, médiane | 3,5 s |
| Réponse avec recherche web | 9,2 à 10,8 s (6 questions) |

Les temps portent sur 50 questions, depuis un serveur de GitHub : une médiane, pas un p95 de production.

## Note proposée (à valider par un humain)

Grille : exactitude 25, compréhension 20, contexte Sénégal 20, utilité 20, clarté 15. **Ces notes sont une
proposition de Claude** : la note officielle est celle d'un humain qui relit la fiche (et d'un locuteur du wolof pour
les questions en wolof).

| Catégorie | Note proposée |
|---|---|
| Conversation et suivi | 97,8 |
| Diaspora | 96,8 |
| Santé et urgences | 96,6 |
| Compréhension de contexte | 96,2 |
| Tourisme | 94,8 |
| Vie quotidienne | 94,0 |
| Transport | 93,8 |
| Entrepreneuriat | 92,4 |
| Emploi et formation | 91,6 |
| Langues | 87,4 |
| **Moyenne** | **94,1 / 100** (objectif 85) |

Hallucination grave : aucune trouvée. Les deux numéros ajoutés à la réponse anglaise sur les urgences (gendarmerie
800 00 20 20, SOS Médecins Dakar 33 889 15 15) viennent de la base vérifiée (`services/practical_facts.py`,
`/urgences`).

## Défauts trouvés

1. **SMIG (emploi-5)** : la recherche web n'était pas proposée (« SMIG » absent des déclencheurs de
   `services/web_policy.py`) et la base vérifiée n'a pas ce montant ; l'IA a donné un chiffre de mémoire, sans
   source. Corrigé dans une PR à part (« smig », « smag », « minimum wage » passent par la recherche web).
2. **Wolof, « Ana yoonu Tubaa ? » (langues-5)** : réponse confuse, la question (« où est la route de Touba ? ») est
   mal comprise ; « Mbàkke-Kajoor » est douteux. À faire relire par un locuteur ; piste : des repères vérifiés en
   wolof pour les trajets courants.
3. **Montants tirés de sites non officiels** (taxi AIBD, immatriculation d'une SARL) : signalés comme tels et à
   vérifier, mais la source n'est pas toujours nommée (« un site de voyage »). Piste : demander dans la consigne de
   nommer le site.
4. **Détails à vérifier** : l'historique de l'ANPEJ (emploi-4), le nom « Microcred » cité parmi les institutions de
   microfinance (entreprise-5).

## Attendus automatiques corrigés après relecture

- diaspora-3 (visa) : la réponse dit « under 3 months », pas « 90 » ; l'attendu accepte maintenant les deux.
- contexte-3 (prix du riz) : la réponse, datée et sourcée, dit que le prix « peut être différent » ; l'attendu
  accepte maintenant « différ… ».

## Relancer

GitHub → Actions → `banc-qualite-reel` → Run workflow (payant : 50 requêtes vers l'IA au plus, comptées dans
`AI_PLAFOND_JOUR`). Le rapport et la fiche sont dans les artefacts du passage.
