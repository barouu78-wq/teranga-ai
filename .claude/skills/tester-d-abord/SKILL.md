---
name: tester-d-abord
description: Écrire le test avant le code de Teranga AI et le voir échouer (rouge), puis écrire le minimum pour le faire passer (vert). À utiliser pour toute nouvelle fonction, correction de bug ou changement de comportement, avant d'écrire le code.
---

# Tester d'abord (rouge, puis vert)

Adapté de Superpowers (`test-driven-development`), licence MIT : voir `.claude/skills/LICENCE-superpowers.txt`.

**Règle : si on n'a pas vu le test échouer, on ne sait pas s'il teste la bonne chose.**

## Le cycle
1. **Rouge.** Un test, un comportement, un nom qui décrit le comportement, en français comme le reste du projet
   (`test_la_banniere_disparait_a_la_premiere_question`). Le lancer :
   `OPENAI_API_KEY=test-key python -m pytest -q tests/test_x.py -k nom`. Il doit échouer **pour la bonne raison**
   (fonction absente, mauvaise valeur), pas à cause d'une faute de frappe ou d'une importation.
2. **Vert.** Écrire le code le plus simple qui le fait passer, rien de plus.
3. **Toute la suite.** Lancer `pytest -q --cov=app --cov=routes --cov=services --cov-fail-under=85` et, si l'écran
   change, `E2E_REQUIRED=1 python -m pytest -q tests/e2e -rs`. Un test vert tout seul ne fait pas une suite verte.
   Tout échec vu, même s'il ne vient pas de nous, est cité dans le rapport.
4. **Nettoyer** les noms et les doublons, en restant vert.

## Code écrit avant le test ?
Ça arrive (maquette, exploration). Il faut alors prouver le rouge quand même, en lançant le nouveau test sur une
copie de `main` qui n'a pas le changement :
```bash
git worktree add --detach /tmp/rouge origin/main
cp tests/test_nouveau.py /tmp/rouge/tests/
(cd /tmp/rouge && OPENAI_API_KEY=test-key python -m pytest -q tests/test_nouveau.py -p no:cacheprovider)
git worktree remove --force /tmp/rouge
```
Il doit échouer sur la copie de `main` et passer sur la branche. Le dire dans la PR : « rouge sur main, vert ici ».

## Un bon test
- **Nommer d'abord le changement de code qui le ferait échouer.** Si on n'en trouve pas, le test ne protège rien.
- **La valeur attendue est écrite à la main** (un littéral), jamais recalculée par le code testé.
- **Tester le vrai comportement** : réponse HTTP, page rendue, clic dans Chromium.
- **Ne simuler que ce qui sort de la machine** : OpenAI, Anthropic, Redis, météo, `/chat` en e2e. Jamais d'appel
  réseau réel dans les tests.
- **Aucune vérification sur la simulation elle-même** : elle ne prouve que la présence de la simulation.
- **Ne jamais assouplir, sauter ni supprimer un test pour passer** (règle d'`AGENTS.md`). Si un changement voulu
  modifie un comportement testé, mettre le test à jour et l'expliquer dans la PR.

## Signaux d'alerte : revenir au rouge
- Un test qui passe du premier coup : il teste ce qui existait déjà.
- « je testerai après ».
- « déjà testé à la main ».
- « trop simple pour un test ».
