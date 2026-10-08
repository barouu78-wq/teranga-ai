---
name: banc-ia
description: Lancer les tests d'intelligence de Teranga AI (banc d'essai, couverture de la base, repères pratiques) et en lire les résultats pour corriger la cause d'un échec. À utiliser après toute modification du contexte de l'IA (base de connaissances, practical_facts, events, choix des lieux).
---

# Banc d'essai de l'IA

Le banc vérifie le **contexte envoyé au modèle** (les faits injectés), pas la réponse finale du modèle :
si le bon fait est dans le contexte, l'IA peut bien répondre ; s'il manque, elle devine. Aucun appel réseau.

## Lancer
```bash
OPENAI_API_KEY=test-key python -m pytest -q tests/test_ai_bench.py tests/test_ai_bench_fouta.py \
  tests/test_ai_bench_pratique.py tests/test_knowledge_coverage.py tests/test_intelligence.py \
  tests/test_senegal_domain_matching.py tests/test_practical_facts.py
```
Puis la suite complète (`pytest -q --cov=app --cov=routes --cov=services --cov-fail-under=85`).

## Lire un échec
Le nom du test contient la question ou le lieu.
| Échec | Cause probable | Correction |
|---|---|---|
| `test_each_place_is_found_by_name[<id>]` | le lieu n'est pas dans les 3 premiers « LIEUX PERTINENTS » | ajouter des `aliases` au lieu, vérifier le nom (doublon proche) ; sinon `services/senegal_knowledge.py` |
| `PROBES` : phrase attendue absente | le sujet ne se déclenche pas | élargir le déclencheur dans `TOPICS` (`services/practical_facts.py`), avec `\b` |
| `NOISE` : un bloc s'ajoute à tort | faux positif (« prise » dans « entreprise », « vol », « location » dans « allocations ») | resserrer le déclencheur ; nom complet plutôt que sigle |
| un fait dépend de la date | `services/events.py` ou date de référence | dates lunaires marquées « estimée » |

## Ajouter une sonde
Dans `tests/test_ai_bench_pratique.py` : `("fr", "question réelle", ["phrase exacte attendue"])`.
Choisir une **phrase exacte** (« Police 17 », « 655,957 »), pas un nombre seul qui peut venir d'une date.
Ajouter aussi, dans `NOISE`, une question voisine qui ne doit rien déclencher.

## Interdits
- Ne jamais retirer ou affaiblir une phrase attendue pour passer : corriger la cause.
- Si un changement voulu modifie un comportement testé, mettre le test à jour **et** l'expliquer dans la PR.

## Comparer les vraies IA (propriétaire uniquement)
`python scripts/compare_ai.py --limite 5` pose les questions à OpenAI et à Claude et écrit `comparatif-ia.md`.
Cela coûte de l'argent et demande les deux clés : à lancer chez le propriétaire (Render → Shell ou son ordinateur).
**Ne jamais demander, écrire ni afficher une clé.**
