---
name: offres-emploi
description: Règles des offres d'emploi de Teranga Emploi (sites sénégalais, accord écrit, robots.txt, lien vers l'annonce d'origine, offres expirées retirées, arnaques). À utiliser avant d'ajouter, d'activer ou de modifier une source d'offres, et pour tout code ou page qui affiche des offres.
---

# Offres d'emploi au Sénégal

Décision du propriétaire du 15 novembre 2026 : Teranga Emploi s'appuie sur les offres publiées par des sites
sénégalais, pour aider les jeunes à trouver du travail. Les règles d'`AGENTS.md` priment, d'abord « Exactitude avant
tout ». Pour le CV et la lettre de motivation, voir le skill `cv-senegal`.

## Décision du 22 novembre 2026 : des liens, pas d'offres recopiées

Le propriétaire : « on met juste leur lien », l'offre s'ouvre sur le site qui la publie. La page `/offres-emploi`
(`services/offres_emploi.py`) renvoie vers la page d'offres de sites vérifiés à la main, sans lire ni recopier leurs
offres : ce simple lien ne demande pas d'accord. Règles qui restent : aucun site présenté comme partenaire, le lien
respecte les conditions d'utilisation du site (Emploi Dakar : page d'accueil seulement, liens profonds interdits),
chaque site est rouvert avant d'être ajouté (offres récentes, rien de payant pour postuler), retrait sur simple
demande. Afficher les offres une par une sur Teranga reste soumis aux règles ci-dessous.

## Règles

1. **Aucune source affichée sans accord écrit du site.** La date de l'accord est notée avec la source (comme
   `accord_ecrit` dans Teranga Hôtes). Sans elle, la source reste éteinte, même si le code sait la lire.
2. **robots.txt respecté**, relu avant d'activer une source et chaque mois. Ne lire que les pages autorisées, une page
   par seconde au plus, avec un User-Agent qui nomme Teranga AI.
3. **Afficher peu, renvoyer toujours** : titre, employeur, ville, type de contrat, date de publication, date limite,
   nom du site source, et le lien vers l'annonce d'origine. Jamais le texte complet de l'annonce.
4. **Offres retirées** : expirée (date limite passée), hors du Sénégal (certains sites publient aussi des offres
   d'autres pays), en double, ou retirée par le site source.
5. **Arnaques** : une offre qui demande de l'argent (frais de dossier, formation payante obligatoire, « visa
   garanti ») est signalée ou retirée. Le message « Ne paie jamais pour obtenir un emploi » accompagne la liste des offres
   (repère « arnaques » de `services/practical_facts.py`).
6. **Aucune offre inventée.** Une maquette montre de vraies offres avec leur date, ou des exemples marqués « Exemple ».
   Un test n'appelle jamais un vrai site : il lit des pages enregistrées dans `tests/` (AGENTS.md, aucun appel réseau).
7. **Retrait sur simple demande** d'un site ou d'un employeur, sans discussion.
8. **Messages aux sites** (demande d'accord, partenariat) : rédigés par l'agent, envoyés par le propriétaire seulement.

## Vérification du 15 novembre 2026

Pages lues ce jour-là, à revérifier avant toute activation :

| Site | robots.txt (pages d'offres) | Données lisibles | Conditions d'utilisation |
|---|---|---|---|
| senjob.com | autorisées (CV et profils interdits) | page d'offre avec données JobPosting : titre, employeur, ville, dates | non trouvées |
| goafricaonline.com/sn/emploi | autorisées (`/api/`, `/graphql` interdits) | page d'offre avec données JobPosting | non trouvées |
| concoursn.com | autorisées | flux RSS : titre, date, lien (offres du Sénégal et d'ailleurs) | non trouvées |
| EmploiDakar (emploidakar.com) | autorisées (CV interdits) | page d'offre avec données JobPosting | **interdisent les liens profonds et l'extraction de la base** (`/conditions-generales-dutilisation-cgu/`) : accord écrit indispensable |

Un prototype non publié a lu 12 vraies offres du jour sur senjob.com, goafricaonline.com et concoursn.com ; une était
déjà expirée, et la première offre du flux de concoursn.com était au Yémen. D'où les règles 4 et 5.

## Services officiels

À montrer à côté des offres : les services publics d'emploi et d'accompagnement déjà vérifiés dans le site (ANPEJ,
DER/FJ : `services/youth_opportunities.py`), avec leur lien officiel.
