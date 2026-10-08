---
name: ajouter-un-lieu
description: Ajouter un lieu sourcé à la base de connaissances de Teranga AI (data/senegal_knowledge.json) : fiche complète, sources, coordonnées, tests. À utiliser pour tout nouveau lieu, site, marché, île, musée ou localité.
---

# Ajouter un lieu

Règle d'or (AGENTS.md) : **aucun fait inventé**. Pas de prix, d'horaire, d'effectif ni de date non confirmés ;
ce qui peut changer est formulé « à vérifier sur place ». Un nouveau lieu cite ses sources.

## 1. Rassembler
Au moins une source fiable (administration, UNESCO, collectivité, musée, presse reconnue) ; deux si possible
pour l'histoire et les chiffres. Noter les adresses : elles vont dans `sources`.

## 2. Écrire la fiche dans `places` de `data/senegal_knowledge.json`
| Champ | Règle |
|---|---|
| `id` | minuscules, chiffres et tirets (`[a-z0-9-]+`), **unique** : c'est l'adresse `/lieux/<id>` |
| `name` | unique dans la base |
| `type` | une valeur déjà utilisée : `heritage`, `monument`, `museum`, `religious_site`, `cultural_site`, `natural_site`, `coastal_site`, `island`, `beach`, `locality` |
| `region` | un nom existant de `regions` ; `locality` : la commune ou le département |
| `summary` | une phrase claire (sert à la page et aux résultats Google) |
| `history` | 2 à 4 phrases vérifiées, sans balise HTML |
| `what_to_see` | éléments séparés par des points-virgules |
| `latitude`, `longitude` | dans le Sénégal (12,2 à 16,8 / −17,6 à −11,3). Position approximative : `"coordinates_precision": "approximate"` |
| `image_queries` | au moins une requête de recherche d'images (`"<Nom> Sénégal"`) |
| `access` | facultatif ; tarifs et horaires toujours « à vérifier » |
| `aliases` | autres noms et graphies (aide à retrouver le lieu quand on le nomme) |
| `sources` | liste d'adresses ; **obligatoire pour un nouveau lieu** |

Ajouter aussi le lieu dans `highlights` de sa région si c'est un incontournable.

## 3. Tests
1. Ajouter l'`id` à la liste de `test_new_places_cite_their_sources` (`tests/test_knowledge_places.py`).
2. `tests/test_knowledge_coverage.py` teste le lieu automatiquement : « Que voir à <nom> ? » doit le placer dans
   les 3 premiers « LIEUX PERTINENTS ». S'il échoue, ajouter des `aliases` ou renommer.
3. Lancer `tests/test_data_integrity.py`, `tests/test_knowledge_places.py`, `tests/test_ai_bench*.py`, puis la
   suite complète, puis le skill `audit-seo` (la page `/lieux/<id>` entre au sitemap : titre ≤ 65, description 70-165).

## 4. PR
Une PR par lot de lieux ; description en français (Résumé + Tests) avec la liste des sources utilisées.
