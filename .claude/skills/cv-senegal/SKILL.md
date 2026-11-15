---
name: cv-senegal
description: Créer ou adapter un CV et une lettre de motivation pour un emploi au Sénégal, sans rien inventer (ni diplôme, ni expérience, ni chiffre). À utiliser pour un CV fait dans la conversation, pour la consigne de l'IA du site (« Adapter mon CV ») et pour toute page CV de Teranga Emploi.
---

# CV pour l'emploi au Sénégal

> Adapté de `resume-tailor` (Paramchoudhary/ResumeSkills), licence MIT : voir `.claude/skills/LICENCE-resumeskills.txt`.
> Traduit et adapté au projet le 15 novembre 2026. Les règles d'`AGENTS.md` priment, d'abord « Exactitude avant tout ».

**Règle d'or : on ne ment pas, on met en valeur.** Toute l'expérience de la personne est une bibliothèque ; adapter un
CV, c'est choisir les livres qui répondent le mieux à l'offre. Jamais en ajouter un qui n'existe pas.

## Quand l'utiliser

- Créer un CV à partir d'un CV existant (PDF, Word, photo) ou de réponses à quelques questions.
- Adapter un CV à une offre précise (lien, texte ou photo de l'annonce).
- Écrire la lettre de motivation qui va avec.
- Écrire ou relire la consigne que l'IA de Teranga reçoit pour ces tâches.

## Ce qui est permis, ce qui est interdit

| Permis | Interdit (c'est mentir) |
|---|---|
| Réordonner ce qui est vrai | Ajouter une compétence que la personne n'a pas |
| Mettre en avant l'expérience utile pour ce poste | Inventer un diplôme, une certification, un poste |
| Reprendre les mots de l'offre quand ils décrivent un vrai travail | Changer une date, une durée ou un chiffre |
| Rendre précise une phrase vague, avec les informations données | Ajouter un chiffre (pourcentage, montant, nombre de clients) que la personne n'a pas donné |
| Retirer ce qui n'aide pas pour ce poste | Donner un titre de poste que la personne n'a pas eu |

Un résultat chiffré n'apparaît que si la personne l'a donné. S'il manque, **poser la question** (« Combien de clients
servais-tu par jour ? ») ou écrire la phrase sans chiffre. Jamais d'estimation présentée comme un fait.

## Étapes

### 1. Lire l'offre

- Le poste, l'employeur, la ville, le type de contrat, la date limite (si elle est écrite).
- Les exigences indispensables (diplôme, années d'expérience, permis, langues) et celles qui sont seulement souhaitées.
- Les mots qui reviennent : ce sont ceux que le recruteur, ou son logiciel de tri, cherchera.
- Une offre qui demande de l'argent (frais de dossier, formation obligatoire payante) : la signaler comme probable
  arnaque, avant tout travail sur le CV (`services/practical_facts.py`, repère « arnaques »).

### 2. Relire le CV, section par section

Pour chaque ligne : sert-elle **ce** poste ? Peut-on la dire mieux pour ce poste ? Doit-elle monter ou descendre ?

### 3. Ajuster

- **Profil** (3 ou 4 lignes) : le métier visé, les deux ou trois forces vraies qui répondent à l'offre.
- **Compétences** : celles que l'offre demande d'abord, si la personne les a ; les autres ensuite.
- **Expérience** : les postes les plus proches de l'offre d'abord (dates gardées), et dans chaque poste la tâche la plus
  utile en premier. Verbe d'action, ce qui a été fait, et le résultat seulement s'il est connu.
- **Formation** : diplômes, formations et certificats réellement obtenus (ou « en cours », si c'est le cas).
- **Langues** : celles que la personne parle vraiment, avec son niveau à elle (français, wolof, anglais, autre).

### 4. Jeunes sans expérience, ou peu

Rien n'est inventé, mais beaucoup compte : stages, apprentissage, bénévolat, associations, petits boulots, travail dans
le commerce familial, projets d'études, responsabilités (délégué, trésorier d'association), permis, outils maîtrisés.
Mettre alors la formation en premier. Pour un accompagnement, renvoyer aussi vers les services officiels déjà connus du
site (ANPEJ, DER/FJ : `services/youth_opportunities.py`).

### 5. Mise en forme

- Une page pour moins de dix ans d'expérience, deux au plus sinon.
- Titres simples (Profil, Expérience, Formation, Compétences, Langues), du plus récent au plus ancien.
- Pas de tableau ni d'image pour le texte important : certains logiciels de tri ne les lisent pas.
- Coordonnées en haut : ville, téléphone, e-mail. Pas d'âge, de situation familiale, de religion, d'ethnie ni de numéro de
  pièce d'identité, sauf si la personne le veut. La photo seulement si la personne la veut ou si l'offre la demande.
- Une habitude « au Sénégal » qui n'est pas vérifiée ne s'écrit pas comme une règle : elle se dit « à vérifier ».

### 6. Lettre de motivation

Courte : trois paragraphes. Pourquoi ce poste et cet employeur (avec ce que dit l'offre) ; ce que la personne apporte,
pris dans son CV ; la disponibilité et la demande d'entretien. Même règle : rien qui ne soit dans le CV ou dans ce que la
personne a dit.

## Confidentialité

Un CV contient des données personnelles. Sur le site, il reste sur le téléphone de la personne : Teranga ne le garde pas
(`services/fichiers.py`). Dans une conversation, ne pas recopier plus de données personnelles que nécessaire.

## Avant de rendre le CV

1. Le profil nomme le poste visé.
2. Les premières compétences répondent aux premières exigences de l'offre, et la personne les a vraiment.
3. L'expérience la plus utile est en haut.
4. Aucun chiffre, diplôme, poste ou date qui ne vienne de la personne.
5. Les mots de l'offre apparaissent là où ils sont vrais, sans répétition forcée.
6. Une page, lisible sur téléphone et à l'impression.
7. Ce qui manque est dit à la personne (« L'offre demande le permis B : l'as-tu ? »), pas comblé.

## Quand on adapte un CV existant, rendre aussi la liste des changements

```
Poste visé : … chez …
Profil : avant → après
Compétences : nouvel ordre ; mots de l'offre ajoutés (seulement s'ils sont vrais)
Expérience : ce qui monte, ce qui est reformulé (avant → après)
À vérifier par la personne : …
Ce que l'offre demande et qui manque : …
```
