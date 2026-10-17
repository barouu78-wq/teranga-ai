# Banc d’essai du moteur IA — Teranga AI

## Objectif

Établir une référence reproductible avant de modifier le modèle, les prompts, le cache ou l’hébergement. Aucun changement de production n’est autorisé par ce protocole.

## Jeu de 15 questions

Utiliser exactement les mêmes questions, dans le même ordre, sur la configuration de référence puis sur chaque candidate. Pour éviter qu’une information récente soit notée comme fausse uniquement parce qu’elle a changé, les questions « actuelles » doivent être évaluées avec leurs sources et leur date.

| ID | Langue | Catégorie | Question |
|---|---|---|---|
| Q01 | fr | simple | Quelle est la capitale du Sénégal ? Réponds en deux phrases maximum. |
| Q02 | fr | connaissance locale | Cite trois lieux à visiter à Dakar et explique en une phrase ce qui distingue chacun. |
| Q03 | fr | transport | Je viens d’atterrir à l’AIBD et je veux rejoindre le centre de Dakar. Quelles options de transport comparer et quelles informations vérifier avant de partir ? |
| Q04 | fr | tourisme | Propose un itinéraire d’une journée à Gorée, avec un ordre logique et les éléments pratiques à vérifier. |
| Q05 | fr | culture | Explique ce qu’est le thiéboudiène et distingue les variantes sans présenter une seule recette comme universelle. |
| Q06 | fr | vie pratique | Je m’installe au Sénégal. Donne une checklist des démarches à vérifier, en séparant les obligations officielles des conseils pratiques. |
| Q07 | fr | sécurité factuelle | Quelles informations faut-il vérifier avant de donner un numéro d’urgence ou une adresse d’un service public au Sénégal ? Donne une réponse utile sans inventer de coordonnées. |
| Q08 | fr | calcul | J’achète un produit à 6 000 FCFA et le revends à 8 500 FCFA. Calcule le bénéfice brut unitaire et la marge sur le prix de vente. Montre le calcul. |
| Q09 | fr | commerce | Je veux lancer un petit commerce à Dakar avec un budget limité. Donne un plan d’action en cinq étapes et les questions à clarifier avant de dépenser. |
| Q10 | fr | projet jeunesse | Aide-moi à structurer un projet destiné aux jeunes au Sénégal : problème, bénéficiaires, activités, budget, résultats mesurables et partenaires à rechercher. |
| Q11 | fr | diaspora | Je vis en France et veux préparer un séjour de trois semaines au Sénégal. Propose une checklist et indique ce qui dépend de ma situation personnelle ou des règles en vigueur. |
| Q12 | fr | recherche web | Quelles sont les informations à vérifier pour connaître les horaires et tarifs actuels du ferry Dakar–Gorée ? Si tu peux rechercher sur le web, cite les sources et leur date ; sinon, dis-le clairement. |
| Q13 | wo | compréhension wolof | Tuddal ñaari dëkk ci Senegaal te wax ci benn baat lu ñu xamle. (Réponds en wolof simple.) |
| Q14 | en | langue anglaise | I am visiting Dakar for two days. Suggest a practical itinerary and clearly mark details that need checking before travel. |
| Q15 | fr | raisonnement multi-étapes | Je veux créer une petite activité touristique au Sénégal. Propose trois hypothèses à tester, un test peu coûteux pour chacune, des indicateurs de réussite et les risques à vérifier. |

## Protocole

1. Noter le commit Git, les modèles/configurations utilisés, la date, la région d’hébergement et les paramètres de raisonnement. Ne jamais enregistrer de clé API ni de données personnelles.
2. Utiliser un environnement de test ou de préproduction. Ne pas lancer une rafale de tests sur le site public : le chat applique des limites de débit et chaque requête peut consommer des crédits fournisseur.
3. Exécuter chaque question trois fois pour la référence, avec les mêmes paramètres. Pour les questions répétables et éligibles au cache, mesurer séparément un passage à froid et un passage à chaud ; ne pas comparer un cache chaud à une requête froide.
4. Mesurer le délai avant le premier texte visible, la durée totale jusqu’à la fin du flux, le code HTTP, le modèle réellement utilisé, les erreurs, les indicateurs de cache/recherche web et l’usage fournisseur (tokens et coût, lorsque l’API les expose).
5. Évaluer chaque réponse à l’aveugle, sans afficher le nom du modèle au correcteur.

## Grille de qualité (0 à 2 points par critère)

- Exactitude : faits corrects, calculs justes, aucune invention.
- Pertinence : répond à la demande réelle, sans digression.
- Ancrage Sénégal : contexte local concret, sans généralités trompeuses.
- Prudence : signale les détails changeants et les incertitudes ; sources datées pour la recherche web.
- Langue et clarté : français, wolof ou anglais naturel selon la question.

Maximum : 10 points par réponse. Pour Q12, l’absence de recherche web doit être annoncée explicitement ; des horaires ou tarifs inventés valent 0 en exactitude.

## Tableau de résultats à compléter

| Configuration | Médiane premier texte | Médiane réponse complète | P95 réponse complète | Score qualité /10 | Erreurs | Coût moyen/réponse |
|---|---:|---:|---:|---:|---:|---:|
| Référence (commit à noter) | — | — | — | — | — | — |
| Candidate A | — | — | — | — | — | — |

Calculer médiane et P95 à partir des mesures individuelles, pas à partir de moyennes déjà agrégées. Comparer les mêmes questions et le même nombre d’exécutions.

## Règle de décision

Ne retenir une candidate que si elle améliore le délai de façon reproductible sans dégrader le score moyen de qualité de plus de 0,3/10, sans baisse notable sur une langue, sans hausse du taux d’erreur et avec un coût par réponse acceptable. Le seuil budgétaire doit être décidé à partir des coûts réels mesurés, avant tout changement payant.

## État initial connu

Le dépôt dispose déjà de journaux de latence dans `services/latency.py` et d’un cache de réponses dans `services/answer_cache.py`. Un petit échantillon des journaux de production consultés le 16 octobre 2026 montrait un délai de premier texte variable ; il n’est pas assez large pour servir de benchmark officiel. Les métriques HTTP Render consultées pour `/chat` n’avaient pas de points de données sur la période interrogée. Ne pas présenter ces données limitées comme un résultat final.
