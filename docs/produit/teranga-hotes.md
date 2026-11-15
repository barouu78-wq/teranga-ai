# Teranga Hôtes : l'assistant de séjour des maisons d'hôtes

Fiche produit du 15 novembre 2026. Décision du propriétaire du même jour : la nouvelle version de Teranga
s'adresse d'abord aux hébergeurs.

**Objectif** : 3 hébergeurs payants avant fin février 2027 (plan clients du 10 novembre).

## Pour qui

- **Le client payant** : une maison d'hôtes, un petit hôtel ou un campement au Sénégal. Ce sont d'abord les
  7 adresses du plan clients (Ziguinchor, Saint-Louis, Lompoul, Kafountine).
- **L'utilisateur** : le voyageur qui loge chez lui, avant d'arriver et pendant son séjour.

## Le problème

Les clients posent sans arrêt les mêmes questions : comment venir depuis l'aéroport, les horaires, les excursions,
où manger, les numéros d'urgence, l'argent. L'hôte répond une par une sur WhatsApp, souvent la nuit.

## Le parcours

1. L'hôte envoie ses informations (WhatsApp ou e-mail) : arrivée et départ, transferts, excursions, repas,
   règles de la maison, contacts.
2. Teranga crée **sa page** : `teranga-ai.fr/hote/<nom>`. L'hôte la relit et donne son accord écrit avant la
   mise en ligne.
3. L'hôte envoie le lien avant l'arrivée et pose le **QR code** dans les chambres.
4. Le voyageur ouvre la page sur son téléphone. Il voit l'essentiel en un coup d'œil, et il pose ses questions à
   l'assistant, qui connaît les informations de la maison **et** la base vérifiée de Teranga.
5. L'hôte voit chaque semaine **ce que ses clients demandent** : des compteurs par sujet, sans les questions
   elles-mêmes ni aucune donnée personnelle.

## Dans la version 1

- Une page par hébergeur, faite pour le téléphone (390 px), en français. L'assistant répond déjà dans la
  langue du voyageur ; la page en anglais viendra dans une version suivante.
- Les informations de l'hôte en blocs courts, chacun marqué « Information de l'établissement ».
- L'assistant de Teranga, avec les informations de l'hôte ajoutées à son contexte. Ce que l'hôte n'a pas donné,
  l'assistant ne l'invente pas : il renvoie vers l'accueil.
- Un QR code à imprimer.
- Des compteurs anonymes des questions, par sujet : **version 1.1**, dans une seconde PR (ils s'ajoutent aux
  compteurs existants de `services/coverage_log.py`).
- Une **page de démonstration** pour montrer le produit aux 7 hébergeurs. Elle est clairement marquée
  « Exemple — établissement fictif ».

## Pas dans la version 1

- Pas de compte ni d'espace d'édition pour l'hôte : ses informations sont mises à jour par une PR.
- Pas de réservation, de prix ni de disponibilité inventés (règle du projet).
- Pas de code Wi-Fi sur une page publique : le code reste à l'accueil.
- Pas de robot WhatsApp ni de paiement en ligne.
- Pas de photo sans l'accord de l'hôte sur ses droits.

## Règles

- Aucun établissement n'apparaît sans son **accord écrit**. Rien n'est présenté comme « partenaire officiel » sans
  cet accord.
- Chaque information de l'hôte garde sa date (« fournie par l'établissement le … »).
- Les pages des hébergeurs ne sont pas indexées par Google (`noindex`), sauf si l'hôte le demande.

## Prix (à confirmer avec les hébergeurs)

Un mois d'essai gratuit, puis **15 000 FCFA par mois** (prix fixé le 18 octobre 2026). Un client ne compte que
s'il paie.

## Critères d'acceptation de la version 1

1. La page de démonstration s'ouvre sur téléphone, lisible à 390 px. Les zones tactiles font au moins 44 px.
2. À « À quelle heure est le petit-déjeuner ? », l'assistant répond avec l'horaire donné par l'hôte.
3. À une question que l'hôte n'a pas renseignée, l'assistant répond qu'il faut demander à l'accueil, sans rien
   inventer.
4. Le QR code mène à la bonne page.
5. (Version 1.1) Les compteurs comptent les questions par sujet, sans jamais garder le texte de la question.
6. Tous les contrôles du dépôt sont verts (pytest, e2e, ruff, bandit).

## Indicateur de réussite

Le nombre d'hébergeurs payants : 3 avant fin février 2027. En second, le nombre de questions posées chaque semaine
sur les pages des hébergeurs.

## Ajouter un hébergeur (après son accord écrit)

1. Copier `data/hotes/exemple.json` en `data/hotes/<nom>.json` (minuscules, chiffres et tirets). Le nom du fichier
   est l'adresse : `teranga-ai.fr/hote/<nom>`.
2. Remplir **seulement** ce que l'hôte a envoyé :
   - `nom`, `ville`, `region`, une `accroche` courte ;
   - les blocs `infos` (`titre`, `valeur`, `detail`, et une `icone` parmi `heure`, `repas`, `route`, `wifi`,
     `boussole`, `maison`, `info`) ;
   - au plus 4 `questions` fréquentes ;
   - le `whatsapp` de l'accueil, en chiffres avec l'indicatif.
3. Mettre `"demo": false`, `accord_ecrit` (date de l'accord écrit) et `fourni_le` (date des informations).
   Sans accord écrit, la fiche est refusée au démarrage et par le CI.
4. Ne jamais mettre de mot de passe ni de code Wi-Fi. Une fiche qui contient « mot de passe » est refusée
   automatiquement ; pour le reste, c'est à relire.
5. Ouvrir une PR. Une fois fusionnée, envoyer à l'hôte le lien de sa page et le QR code
   (`teranga-ai.fr/hote/<nom>/qr.svg`, à imprimer).

## Comment l'assistant connaît la maison

La boîte « Pose ta question » et les suggestions de la page ouvrent le chat de Teranga avec `?hote=<nom>`. Le chat
garde la maison pendant la visite et l'envoie avec chaque question. Le serveur ajoute alors les informations de la
maison au contexte de l'IA, avec la règle « ce qui manque se demande à l'accueil ». La question écrite ou choisie
sur la page part tout de suite. Ailleurs sur le site, une question passée dans l'adresse reste seulement
pré-remplie.
