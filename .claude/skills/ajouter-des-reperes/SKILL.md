---
name: ajouter-des-reperes
description: Ajouter un sujet de repères pratiques vérifiés à l'IA de Teranga AI (démarches, santé, argent…) sans fait inventé ni faux déclenchement. À utiliser pour enrichir services/practical_facts.py, la base de connaissances ou une page-guide.
---

# Ajouter des repères pratiques

Règle d'or (AGENTS.md) : **exactitude avant tout**. Aucun prix, numéro de téléphone, horaire ou chiffre non confirmé.

## 1. Chercher et trier
- Chercher avec plusieurs sources (administration, presse, organismes). Garder ce que **plusieurs sources
  confirment** ; le reste est formulé « annoncé », « à vérifier » ou renvoie vers l'organisme.
- Pas de prix ni de numéro d'un annuaire non officiel. Une date dépassée ou un tarif qui change : le dire.
- Noter les sources dans le bloc de commentaires au-dessus de `TOPICS` (`services/practical_facts.py`).

## 2. Écrire le sujet dans `TOPICS`
- Déclencheurs sur le texte **sans accents** (`fold_text`), avec des limites de mot (`\b`) :
  « prise » dans « entreprise », « vol », « css » (langage web), « daf » (poste), « location » dans « allocations »
  ont déjà fait de faux déclenchements. Éviter les sigles courts ; préférer le nom complet.
- Un sujet **précis** va dans `_SPECIFIC_FIRST` : il passe avant les sujets généraux quand la limite de 3 coupe.
- Un sujet qui ne concerne que les habitants ne doit pas se déclencher pour un voyageur étranger
  (voir `_FOREIGN_TRAVELLER` et `_ENTRY_WORDS`).

## 3. Vérification en direct
- Ajouter les mots du sujet dans `dynamic_intents` de `services/web_policy.py`, **dans les deux graphies**
  (« carte d'identité » et « carte d'identite » : le texte est normalisé sans accent).

## 4. Tests (obligatoires)
- `tests/test_ai_bench_pratique.py` : une question réelle par fait important (phrase exacte attendue) dans
  `PROBES`, et des questions voisines qui ne doivent **rien** ajouter dans `NOISE`.
- `tests/test_practical_facts.py` : détection du sujet, absence de faux déclenchements, interaction avec les autres sujets.
- Lancer `tests/test_ai_bench*.py`, `tests/test_knowledge_coverage.py`, puis la suite complète.

## 5. Page-guide (facultatif)
Entrée dans `SEO_PAGES` (`services/seo.py`) : titre ≤ 65 caractères, description de 70 à 165, lien depuis l'accueil.
L'empreinte du cache des réponses inclut déjà `practical_facts.py`, `events.py` et la base : une modification
invalide les anciennes réponses.
