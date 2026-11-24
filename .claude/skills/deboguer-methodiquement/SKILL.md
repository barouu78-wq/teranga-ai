---
name: deboguer-methodiquement
description: Trouver la cause d'un bug, d'un test rouge ou d'un comportement inattendu de Teranga AI avant de proposer une correction (production, CI, e2e, réponses de l'IA). À utiliser dès qu'un test échoue, qu'une alerte arrive ou que le propriétaire signale un problème.
---

# Déboguer méthodiquement

Adapté de Superpowers (`systematic-debugging`), licence MIT : voir `.claude/skills/LICENCE-superpowers.txt`.

**Règle : aucune correction sans cause trouvée.** Corriger un symptôme, c'est revoir le bug plus tard.

## 1. Comprendre, avant de toucher au code
- **Lire l'erreur en entier** : trace, `fichier:ligne`, code HTTP, message du test.
- **Reproduire à coup sûr** : `OPENAI_API_KEY=test-key python -m pytest -q tests/test_x.py::test_y -x`, ou le même
  clic dans Chromium (`E2E_REQUIRED=1 python -m pytest -q tests/e2e -k nom -rs`). Pas reproductible : mesurer
  davantage, ne pas deviner.
- **Ce qui a changé** : `git log --oneline -10`, `git diff origin/main`, dernière fusion, dernier déploiement Render.
- **Système à plusieurs étages** (navigateur → `/chat` → contexte → modèle ; GitHub → Render → DNS) : regarder une
  fois ce qui entre et sort à chaque frontière pour trouver l'étage qui casse. En production, journaux Render en
  lecture seule (agents `gardien-prod`, `mesure-latence`) ; ne jamais afficher de secret.
- **Remonter la donnée fausse jusqu'à sa source**, et corriger à la source, pas là où elle explose.

## 2. Comparer avec ce qui marche
- Trouver un cas voisin qui fonctionne dans le dépôt (autre route, autre test) et lister **toutes** les différences.
- Pièges déjà rencontrés ici :
  - la limite de débit, quand un test ne casse que dans la suite complète : donner au test sa propre adresse,
    `environ_base={"REMOTE_ADDR": "203.0.113.x"}` ;
  - le thème qui suit l'heure dans les captures ;
  - `#input`, caché sur téléphone : utiliser `#heroInput` ;
  - le service worker qui sert l'ancien fichier : changer `VERSION` dans `static/sw.js`.

## 3. Une hypothèse à la fois
- L'écrire : « je pense que X est la cause, parce que Y ».
- Faire le plus petit changement qui la teste, en ne touchant qu'une seule chose.
- Si c'est raté, formuler une nouvelle hypothèse, sans empiler les corrections.
- Si on ne sait pas, le dire.

## 4. Corriger
- D'abord un test qui reproduit le bug et **échoue** (skill `tester-d-abord`).
- Une seule correction, celle de la cause ; pas d'amélioration « au passage ».
- Vérifier : le test passe, la suite complète aussi (skill `verifier-avant-d-annoncer`).
- **Trois corrections ratées : s'arrêter.** Le problème vient sans doute de la conception ; en parler au
  propriétaire avant une quatrième tentative.

## Attendre une condition, pas une durée
Un test qui « attend 2 secondes » casse sur une machine lente (CI, `E2E_CPU_THROTTLE=12`). Il faut attendre l'état
voulu : `page.get_by_text(...).wait_for()`, `locator.wait_for()`. N'utiliser une attente fixe que pour tester une
durée (par exemple le signe de vie toutes les 10 s du planificateur), avec la raison en commentaire.

## Signaux d'alerte : revenir à l'étape 1
Ces phrases veulent dire qu'il faut revenir à l'étape 1 :
- « je corrige vite et je regarde après » ;
- « essayons de changer X » ;
- « c'est probablement X » ;
- plusieurs changements d'un coup ;
- « c'est un test instable » sans preuve.

« Instable » n'est pas une cause : un test rouge a une cause tant qu'on n'a pas prouvé le contraire.

## Aucune cause trouvée ?
C'est rare : le plus souvent, l'enquête est incomplète. Dans ce cas :
- écrire ce qui a été vérifié ;
- ajouter un journal ou une limite de temps adaptée ;
- le dire dans la PR.
