# Plan « utilisateurs d'abord » : la diaspora (20 octobre – 16 novembre 2026)

**Décision du propriétaire, 19 octobre 2026** : pendant quatre semaines, le projet vise les premiers vrais
utilisateurs, en commençant par la diaspora sénégalaise, et Teranga doit devenir visible. Le code ne sert que ce que
ces utilisateurs demandent. Rien n'est envoyé ni publié automatiquement : Claude Code prépare, le propriétaire envoie
et publie. Suivi chaque lundi dans le tableau de bord (#417).

## Point de départ (mesuré)

- **Questions au chat du 12 au 19 octobre 2026 : 18**, en quatre rafales de quelques minutes (13, 15, 16 et
  18 octobre), d'après les lignes `latence route=chat` des journaux Render. Ce sont surtout des essais : le site n'a
  pas encore d'utilisateurs réguliers.
- **Application Android** : test fermé lancé sur Google Play, pas assez de testeurs.
- **Partenaires payants** : objectif de 3 avant le 30 novembre (#496), non atteint.
- **Le site lui-même est prêt** : 3 101 tests verts, aucune erreur en production depuis le 17 octobre.

## Objectifs au 16 novembre

1. **12 testeurs Android inscrits sans interruption pendant 14 jours**, puis demande d'accès à la production. C'est
   la condition de Google pour les nouveaux comptes personnels ; l'examen prend en général 7 jours ou moins (voir
   Sources). Viser 15 personnes : celles qui quittent le test avant 14 jours ne comptent pas.
2. **Des questions de vrais utilisateurs chaque semaine**, comptées le lundi. Cible (pas une mesure) : 100 questions
   pendant la semaine du 9 au 15 novembre.
3. **La liste des questions de la diaspora auxquelles Teranga répond mal.** Ce sont les seules corrections de code
   de la période.

## Rendre Teranga visible

Du plus rapide au plus lent :

| Moyen | Effet | Qui | Quand |
|---|---|---|---|
| **Bouche-à-oreille de la diaspora** (WhatsApp, famille, associations) | Immédiat | Propriétaire envoie les messages 1 et 2 ; Claude Code les prépare | Dès le 20 octobre |
| **Partage des réponses** : le bouton « Partager » sous chaque réponse ouvre le menu de partage du téléphone (WhatsApp compris) avec un lien vers la réponse | Chaque bonne réponse partagée amène un nouveau visiteur | Les utilisateurs ; le propriétaire montre l'exemple | Dès le 20 octobre |
| **Vidéos courtes** (TikTok, Reels, statut WhatsApp) tournées sur les vrais écrans du site (`scripts/video/`, skill `faire-une-video`) | Quelques jours | Claude Code fabrique la vidéo ; le propriétaire la publie | Une par semaine, la première le 22 octobre |
| **Google Play** : l'application devient publique et trouvable dans le Play Store | Après les 14 jours de test et l'examen de Google | Propriétaire (Play Console) | Demande le 9 novembre si les testeurs sont inscrits le 26 octobre |
| **Recherche Google** : page `/diaspora-senegalaise` concrète, puis demande d'indexation de quelques pages clés dans la Search Console | Plusieurs semaines | Claude Code (page, PR à valider) ; propriétaire (Search Console) | Page la semaine du 20 octobre |

## Qui fait quoi

| Propriétaire | Claude Code |
|---|---|
| Envoie les messages ci-dessous (famille, amis, groupes WhatsApp dont il est membre, associations), en respectant les règles de chaque groupe, sans envoi en masse | Prépare et met à jour les textes |
| Ajoute les adresses Gmail des testeurs dans la Play Console et leur envoie le lien du test | Compte les questions chaque lundi et met à jour le tableau de bord (#417) |
| Publie les vidéos | Fabrique une vidéo par semaine à partir des vrais écrans |
| Lit le journal des lacunes (page protégée par `STATS_TOKEN`) et transmet les thèmes qui reviennent | Corrige ce que les utilisateurs signalent (PR, avec l'accord du propriétaire si l'écran ou les réponses changent) |

## Semaine par semaine

| Semaine | Propriétaire | Claude Code |
|---|---|---|
| 20 – 26 oct | Message 1 (testeurs) à 15 personnes avec un Android ; message 2 dans 2 ou 3 groupes ; première vidéo publiée | Réponses sans IA en ligne (#503, #504, #505) ; vidéo « 100 euros en FCFA » ; page `/diaspora-senegalaise` concrète (PR à valider) ; premier comptage le 26 |
| 27 oct – 2 nov | Relance douce des testeurs qui n'ont pas accepté le lien ; deuxième vidéo | Lire les thèmes posés, corriger les réponses faibles ; vidéo 2 |
| 3 – 9 nov | Le 9 novembre, si 12 testeurs sont inscrits depuis le 26 octobre : demander l'accès à la production ; troisième vidéo | Comptage ; fiche Google Play définitive ; vidéo 3 |
| 10 – 16 nov | Bilan avec Claude Code | Bilan chiffré (questions par semaine, testeurs, thèmes) et proposition pour la suite (autre public, partenaires) |

## Message 1 : recruter les testeurs Android

À envoyer à des proches qui ont un téléphone Android (un iPhone ne peut pas servir).

> Salam aleekum ! J'ai créé Teranga AI, un assistant gratuit pour le Sénégal : démarches, argent, voyage, fêtes, en
> français, anglais et wolof. L'application Android est en test avant sa sortie sur Google Play, et Google demande
> 12 testeurs pendant 14 jours.
>
> Si tu as un téléphone Android et deux minutes :
> 1. envoie-moi ton adresse Gmail (celle de ton téléphone) ;
> 2. je t'envoie un lien : tu acceptes le test et tu installes l'application ;
> 3. reste inscrit 14 jours et pose-lui de temps en temps une vraie question.
>
> Tes remarques m'aident beaucoup. Merci !

## Message 2 : présenter Teranga dans un groupe de la diaspora

Une seule fois par groupe, si les règles du groupe le permettent. À envoyer quand #503 et #504 sont en ligne (les deux
premiers exemples en dépendent).

> Salam aleekum. Je partage un outil gratuit que j'ai créé pour garder le lien pratique avec le pays : Teranga AI
> (teranga-ai.fr).
>
> Quelques questions qu'on peut lui poser :
> • « 100 euros en FCFA ? » : la réponse tombe tout de suite, au taux fixe de 655,957 FCFA pour 1 €
> • « C'est quand la Tabaski ? » : la date du calendrier, avec la mention « estimée » tant qu'elle n'est pas confirmée
> • « Quels papiers pour renouveler ma carte d'identité ? »
> • « Que faut-il vérifier avant d'acheter un terrain au Sénégal ? »
>
> On peut écrire ou parler en français, en anglais ou en wolof. Teranga indique quand une information est à vérifier
> auprès des services officiels.
>
> Dites-moi ce qui manque : vos retours décident de la suite.

## Mesure (chaque lundi)

- **Questions au chat** : lignes `latence route=chat` de Render, par jour ; part des réponses prêtes (`pret=oui`).
  Les journaux ne contiennent jamais le texte d'une question.
- **Thèmes et lacunes** : journal des lacunes (`services/coverage_log.py`), lu par le propriétaire.
- **Testeurs** : nombre d'inscrits donné par le propriétaire (Play Console).
- **Clics vers les partenaires** : page `/stats-partenaires` (protégée).

## Sources

- Google Play, conditions de test des nouveaux comptes personnels (12 testeurs inscrits sans interruption pendant
  14 jours, examen en 7 jours ou moins en général) :
  https://support.google.com/googleplay/android-developer/answer/14151465 , relevé le 19 octobre 2026 par une
  recherche sur l'aide Google.
- Comptage des questions : journaux Render du service `teranga-ai-1`, du 12 au 19 octobre 2026.
- Exemples du message 2 : `services/quick_answers.py` (conversion et fêtes, en ligne après #503 et #504),
  `services/practical_facts.py` (sujets « papiers » et « foncier »).
- Bouton « Partager » sous chaque réponse : `static/home.js` (`addActs`, lien signé `/partage`, menu de partage du
  téléphone).
