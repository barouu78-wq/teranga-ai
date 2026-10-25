# Audit V3 — 03. Banc de 100 questions : protocole et résultats mesurés

Date de la mesure : 25 octobre 2026. Code mesuré : `main` au commit `c8e999d`. Script : `scripts/banc_v3.py`.

## Ce que ce banc mesure, et ce qu'il ne mesure pas

- **Mesuré** : le **routage réel** de chaque question par la vraie route `/chat` du site : réponse prête sans IA,
  outil de recherche web proposé au modèle, modèle choisi, plafond de réponse, taille du contexte envoyé, temps de
  préparation côté serveur (champ `contexte_ms` de la ligne de journal « latence »).
- **Non mesuré ici** : la justesse des réponses de l'IA, la latence du fournisseur et le coût. L'IA est simulée
  (aucune clé, aucun coût) et le réseau est coupé, comme dans les tests : la météo, les images et la recherche
  externe échouent tout de suite. Les temps sont ceux de la machine de l'audit, pas de Render.
- **Routage local = routage OpenAI** : le banc tourne sans clé Anthropic. En production, depuis le 25 octobre
  15 h 08 UTC, Claude Opus est l'IA principale (`AI_PRINCIPALE=claude`). Les décisions « réponse prête » et
  « outil web proposé » sont les mêmes ; seul le modèle change (Claude Opus pour tout).
- **Outil web proposé ≠ recherche faite** : le modèle décide seul s'il cherche. La part des questions où la
  recherche a réellement eu lieu ne se lit que dans les journaux de production (voir 01-audit-technique.md).
- **Concurrents** : aucun service concurrent n'a été interrogé (réseau de la session restreint, conditions
  d'utilisation non vérifiées). Aucun score de concurrent n'est donné.

Relancer : `OPENAI_API_KEY=test-key python scripts/banc_v3.py --json resultat.json`

## Jeu de questions

100 questions, 10 thèmes de 10 : démarches, transport, tourisme, langues locales (wolof et mélange wolof-français),
emploi et formation, commerce et argent, informations qui changent, santé et urgences, diaspora, questions
ambiguës ou hors du champ. Langue choisie dans l'interface : français 92 (dont une phrase en wolof, « Dama bëgg
jënd mburu, ñaata la ? », envoyée avec l'interface en français), wolof 4, anglais 4 (tableau complet plus bas).

Chaque question porte une **route attendue** : c'est le **jugement de l'audit**, pas une vérité mesurée.

| Attendu | Sens |
|---|---|
| `prete` | réponse exacte sans IA : calcul, conversion, date connue, numéro d'urgence, présentation de Teranga |
| `web` | l'information change (actualité, prix du jour, horaires, offres) : il faut chercher |
| `base` | connaissance stable : base vérifiée du site + modèle, sans recherche web |
| `service` | service dédié (météo) |
| `precis` | question ambiguë : demander une précision, ne rien chercher |
| `inconnu` | hors du champ ou invérifiable : le dire honnêtement, sans inventer |

## Résultats (mesurés le 25 octobre 2026)

| Thème | Questions | Accord avec l'attendu | Prêtes | Outil web proposé | Modèle sans web | Contexte envoyé, médiane (caractères) | Préparation serveur, médiane (ms) |
|---|---|---|---|---|---|---|---|
| demarches | 10 | 4/10 | 0 | 8 | 2 | 9675 | 12.4 |
| transport | 10 | 4/10 | 0 | 9 | 1 | 11174 | 12.6 |
| tourisme | 10 | 10/10 | 0 | 1 | 9 | 10434 | 9.2 |
| langues | 10 | 8/10 | 0 | 1 | 9 | 8341 | 10.3 |
| emploi | 10 | 9/10 | 0 | 3 | 7 | 8312 | 11.9 |
| commerce | 10 | 6/10 | 1 | 3 | 6 | 9189 | 12.5 |
| dynamique | 10 | 9/10 | 2 | 8 | 0 | 10021 | 13.7 |
| sante | 10 | 6/10 | 3 | 5 | 2 | 10838 | 11.9 |
| diaspora | 10 | 8/10 | 1 | 4 | 5 | 8741 | 12.8 |
| ambigu | 10 | 7/10 | 1 | 1 | 8 | 7398 | 11.1 |
| **TOTAL** | **100** | **71/100** | **8** | **43** | **49** | **9675** | **11.6** |

Autres mesures sur les 100 questions :
- 100 réponses HTTP 200, 0 erreur.
- Préparation serveur (`contexte_ms`) : médiane 11,6 ms, p95 17,2 ms, maximum 79,9 ms (première requête,
  chargement à froid). **La préparation de Teranga n'est pas un goulot** : le temps d'attente vient du fournisseur.
- Modèle choisi (routage OpenAI) : `gpt-5.6-luna` 88 fois, `gpt-5.6-sol` 4 fois (séjour de 5 jours, emploi à
  Dakar, CV, budget familial), aucun modèle 8 fois (réponses prêtes).
- Plafond de réponse : 1 200 jetons pour 47 questions, 800 pour 45.

## Les 29 écarts, regroupés

1. **Outil web proposé pour une question stable : 22 cas.** Démarches (carte d'identité, passeport, Senelec,
   légalisation, casier judiciaire, Wave), transport (AIBD → Dakar, taxi AIBD, chaloupe de Gorée, car rapide,
   Dakar → Touba), santé (fièvre, vaccins, hôpital, paludisme), visa, TVA, création d'entreprise, traduction en
   wolof, élection présidentielle.
   - Cause (lue dans `services/web_policy.py`, `should_use_web`) : une liste de mots déclencheurs volontairement
     large (« transport », « taxi », « démarche », « passeport », « santé », « paludisme », « chaloupe »…), parce que
     ces informations peuvent changer.
   - Effet à vérifier en production : si le modèle cherche vraiment, la réponse attend la recherche (mesure du
     18 octobre : 16 s avant le premier mot avec `web=oui`). Plusieurs de ces sujets ont déjà des repères
     vérifiés dans `services/practical_facts.py`.
2. **Réponse prête attendue mais non servie : 5 cas, dont un seul vrai défaut.**
   - **Défaut** : « Convertis 50 000 FCFA en euros ». L'impératif « convertis » n'était pas reconnu. Mesuré aussi
     hors banc : « Convertis 100 euros en FCFA » et « 10 000 F CFA en € » ne l'étaient pas, alors que
     « 50 000 FCFA en euros » l'est. Correction proposée dans une PR séparée (`ia/conversions-convertis`).
   - **Choix déjà faits et testés** (`tests/test_reponse_seule_conversion.py`, décision de #503) :
     - le calcul de marge d'un commerçant va au modèle, avec le bloc de calcul vérifié ;
     - l'anglais va au modèle, parce que les nombres de la réponse prête sont au format français ;
     - le wolof va au modèle, et aucune réponse prête n'existe en wolof (`quick_answer` ne sert que `fr`, plus
       `en` pour les numéros d'urgence).
     L'audit garde ces cas comme pistes, pas comme défauts.
   - « Bonjour » : aucune réponse prête de salutation. Le modèle répond, ce qui coûte un appel ; l'effet sur les
     utilisateurs n'est pas mesuré.
3. **Météo : 1 cas non concluant.** « Quel temps fera-t-il à Dakar demain ? » reçoit l'outil web. Le réseau
   étant coupé, le service météo a échoué ; le banc ne permet pas de savoir ce qui se passe quand il répond.
4. **Recherche web attendue mais non proposée : 1 cas.** « Quelles formations gratuites en informatique au
   Sénégal ? » (les offres changent).

## Limites

- La route attendue est un jugement ; un autre auditeur pourrait classer autrement certaines questions
  (par exemple l'élection présidentielle, ou le taxi AIBD dont les prix sont « à vérifier »).
- 100 questions ne représentent pas le trafic réel : à compléter par les questions réelles des journaux
  (sans texte personnel) quand le volume le permet.
- La justesse des réponses n'est pas mesurée. Proposition (coût API à valider par le propriétaire) : passer les
  100 questions par le vrai modèle et noter chaque réponse (juste, source, honnêteté, prochaine étape).

## Tableau complet

| n° | Thème | Langue | Question | Attendu (audit) | Observé | Modèle |
|---|---|---|---|---|---|---|
| 1 | demarches | fr | Comment refaire ma carte d'identité au Sénégal ? | base | outil web proposé | gpt-5.6-luna |
| 2 | demarches | fr | Quels documents faut-il pour un passeport sénégalais ? | base | outil web proposé | gpt-5.6-luna |
| 3 | demarches | fr | Comment payer ma facture Senelec ? | base | outil web proposé | gpt-5.6-luna |
| 4 | demarches | fr | Comment déclarer une naissance à Dakar ? | base | modèle sans web | gpt-5.6-luna |
| 5 | demarches | fr | Où faire légaliser un document à Dakar ? | base | outil web proposé | gpt-5.6-luna |
| 6 | demarches | fr | Comment obtenir un extrait de casier judiciaire ? | base | outil web proposé | gpt-5.6-luna |
| 7 | demarches | fr | Quel est le prix actuel du sac de riz à Dakar ? | web | outil web proposé | gpt-5.6-luna |
| 8 | demarches | fr | Comment ouvrir un compte Wave ? | base | outil web proposé | gpt-5.6-luna |
| 9 | demarches | fr | Quels sont les jours fériés au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 10 | demarches | fr | Quelle pharmacie est de garde à Dakar ce soir ? | web | outil web proposé | gpt-5.6-luna |
| 11 | transport | fr | Comment aller de l'aéroport AIBD à Dakar ? | base | outil web proposé | gpt-5.6-luna |
| 12 | transport | fr | Combien coûte un taxi de l'AIBD au Plateau ? | base | outil web proposé | gpt-5.6-luna |
| 13 | transport | fr | Le TER circule-t-il normalement aujourd'hui ? | web | outil web proposé | gpt-5.6-luna |
| 14 | transport | fr | Quels sont les horaires du BRT de Dakar ? | web | outil web proposé | gpt-5.6-luna |
| 15 | transport | fr | Comment aller à Saint-Louis depuis Dakar ? | base | modèle sans web | gpt-5.6-luna |
| 16 | transport | fr | Comment prendre la chaloupe pour Gorée ? | base | outil web proposé | gpt-5.6-luna |
| 17 | transport | fr | Y a-t-il un bateau Dakar–Ziguinchor cette semaine ? | web | outil web proposé | gpt-5.6-luna |
| 18 | transport | fr | C'est quoi un car rapide ? | base | outil web proposé | gpt-5.6-luna |
| 19 | transport | fr | Combien de temps de route entre Dakar et Touba ? | base | outil web proposé | gpt-5.6-luna |
| 20 | transport | en | How do I get from Dakar airport to the city centre? | base | outil web proposé | gpt-5.6-luna |
| 21 | tourisme | fr | Que visiter à Dakar en deux jours ? | base | modèle sans web | gpt-5.6-luna |
| 22 | tourisme | fr | C'est quoi le Lac Rose ? | base | modèle sans web | gpt-5.6-luna |
| 23 | tourisme | fr | Raconte-moi l'histoire de l'île de Gorée | base | modèle sans web | gpt-5.6-luna |
| 24 | tourisme | fr | Que faire en Casamance ? | base | modèle sans web | gpt-5.6-luna |
| 25 | tourisme | en | What is the best time to visit Senegal? | base | modèle sans web | gpt-5.6-luna |
| 26 | tourisme | fr | Visiter le parc du Niokolo-Koba | base | modèle sans web | gpt-5.6-luna |
| 27 | tourisme | fr | Que voir à Saint-Louis ? | base | modèle sans web | gpt-5.6-luna |
| 28 | tourisme | fr | Prépare-moi un séjour de 5 jours au Sénégal | base | modèle sans web | gpt-5.6-sol |
| 29 | tourisme | fr | Quels sites sont classés à l'UNESCO au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 30 | tourisme | fr | Quel est le prix d'une nuit à l'hôtel Terrou-Bi ce soir ? | web | outil web proposé | gpt-5.6-luna |
| 31 | langues | fr | Comment dire merci en wolof ? | base | modèle sans web | gpt-5.6-luna |
| 32 | langues | wo | Nanga def ? | base | modèle sans web | gpt-5.6-luna |
| 33 | langues | wo | Lan mooy thiéboudienne ? | prete | modèle sans web | gpt-5.6-luna |
| 34 | langues | fr | Traduis « combien ça coûte » en wolof | base | outil web proposé | gpt-5.6-luna |
| 35 | langues | fr | Que veut dire teranga ? | base | modèle sans web | gpt-5.6-luna |
| 36 | langues | wo | Dama bëgg dem Ndakaaru, naka laa def ? | base | modèle sans web | gpt-5.6-luna |
| 37 | langues | fr | Apprends-moi à compter en wolof | base | modèle sans web | gpt-5.6-luna |
| 38 | langues | fr | Comment saluer un aîné en wolof ? | base | modèle sans web | gpt-5.6-luna |
| 39 | langues | wo | Ana yoonu Tubaa ? | base | modèle sans web | gpt-5.6-luna |
| 40 | langues | fr | Dama bëgg jënd mburu, ñaata la ? | precis | modèle sans web | gpt-5.6-luna |
| 41 | emploi | fr | Comment trouver un emploi à Dakar ? | base | modèle sans web | gpt-5.6-sol |
| 42 | emploi | fr | Aide-moi à préparer mon CV | base | modèle sans web | gpt-5.6-sol |
| 43 | emploi | fr | Quelles offres d'emploi pour un comptable à Dakar en ce moment ? | web | outil web proposé | gpt-5.6-luna |
| 44 | emploi | fr | Quelles sont les dates d'inscription à l'université Cheikh Anta Diop cette année ? | web | outil web proposé | gpt-5.6-luna |
| 45 | emploi | fr | Quelles formations gratuites en informatique au Sénégal ? | web | modèle sans web | gpt-5.6-luna |
| 46 | emploi | fr | Prépare-moi à un entretien d'embauche | base | modèle sans web | gpt-5.6-luna |
| 47 | emploi | fr | Quel est le SMIG au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 48 | emploi | fr | Comment devenir enseignant au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 49 | emploi | fr | Quelles bourses pour étudier en France cette année ? | web | outil web proposé | gpt-5.6-luna |
| 50 | emploi | fr | C'est quoi l'ANPEJ ? | base | modèle sans web | gpt-5.6-luna |
| 51 | commerce | fr | Combien font 100 euros en FCFA ? | prete | prête | - |
| 52 | commerce | fr | Convertis 50 000 FCFA en euros | prete | modèle sans web | gpt-5.6-luna |
| 53 | commerce | fr | Comment créer une entreprise au Sénégal ? | base | outil web proposé | gpt-5.6-luna |
| 54 | commerce | fr | Je veux vendre du jus naturel à Thiès, par où commencer ? | base | modèle sans web | gpt-5.6-luna |
| 55 | commerce | fr | Combien coûte aujourd'hui l'immatriculation d'une SARL à l'APIX ? | web | outil web proposé | gpt-5.6-luna |
| 56 | commerce | fr | Comment obtenir un microcrédit au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 57 | commerce | fr | J'achète à 1 500 FCFA et je revends à 2 000 FCFA : quelle est ma marge ? | prete | modèle sans web | gpt-5.6-luna |
| 58 | commerce | fr | Comment négocier au marché Sandaga ? | base | modèle sans web | gpt-5.6-luna |
| 59 | commerce | fr | Quel est le taux de TVA au Sénégal ? | base | outil web proposé | gpt-5.6-luna |
| 60 | commerce | fr | Fais-moi un budget mensuel pour une famille à Dakar avec 250 000 FCFA | base | modèle sans web | gpt-5.6-sol |
| 61 | dynamique | fr | Quel temps fera-t-il à Dakar demain ? | service | outil web proposé | gpt-5.6-luna |
| 62 | dynamique | fr | Quelles sont les dernières nouvelles au Sénégal ? | web | outil web proposé | gpt-5.6-luna |
| 63 | dynamique | fr | Quel est le résultat du dernier match des Lions du Sénégal ? | web | outil web proposé | gpt-5.6-luna |
| 64 | dynamique | fr | Combien vaut le dollar en FCFA aujourd'hui ? | web | outil web proposé | gpt-5.6-luna |
| 65 | dynamique | fr | Quel est le prix de l'essence au Sénégal ce mois-ci ? | web | outil web proposé | gpt-5.6-luna |
| 66 | dynamique | fr | Y a-t-il des coupures d'électricité à Dakar aujourd'hui ? | web | outil web proposé | gpt-5.6-luna |
| 67 | dynamique | fr | C'est quand la Tabaski cette année ? | prete | prête | - |
| 68 | dynamique | fr | Quand est le prochain Magal de Touba ? | prete | prête | - |
| 69 | dynamique | fr | Quels concerts à Dakar ce week-end ? | web | outil web proposé | gpt-5.6-luna |
| 70 | dynamique | fr | Qui est l'actuel ministre de la Santé du Sénégal ? | web | outil web proposé | gpt-5.6-luna |
| 71 | sante | fr | Quel est le numéro des pompiers au Sénégal ? | prete | prête | - |
| 72 | sante | fr | Quels sont les numéros d'urgence au Sénégal ? | prete | prête | - |
| 73 | sante | fr | J'ai de la fièvre depuis trois jours, que faire ? | base | outil web proposé | gpt-5.6-luna |
| 74 | sante | fr | Quels vaccins pour voyager au Sénégal ? | base | outil web proposé | gpt-5.6-luna |
| 75 | sante | fr | Où trouver un hôpital à Saint-Louis ? | base | outil web proposé | gpt-5.6-luna |
| 76 | sante | fr | Comment fonctionne la CMU au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 77 | sante | fr | Paludisme : comment se protéger ? | base | outil web proposé | gpt-5.6-luna |
| 78 | sante | fr | Mon enfant a avalé un produit ménager, que faire ? | base | modèle sans web | gpt-5.6-luna |
| 79 | sante | fr | Le SAMU, c'est quel numéro au Sénégal ? | prete | prête | - |
| 80 | sante | fr | Faut-il un test Covid pour entrer au Sénégal en ce moment ? | web | outil web proposé | gpt-5.6-luna |
| 81 | diaspora | fr | Comment envoyer de l'argent de France au Sénégal ? | base | modèle sans web | gpt-5.6-luna |
| 82 | diaspora | en | Do I need a visa to visit Senegal? | base | outil web proposé | gpt-5.6-luna |
| 83 | diaspora | fr | Comment acheter un terrain au Sénégal depuis la France ? | base | modèle sans web | gpt-5.6-luna |
| 84 | diaspora | fr | Comment renouveler mon passeport sénégalais en France ? | base | outil web proposé | gpt-5.6-luna |
| 85 | diaspora | fr | Quels frais pour envoyer 200 euros avec Wave aujourd'hui ? | web | outil web proposé | gpt-5.6-luna |
| 86 | diaspora | fr | Comment voter depuis l'étranger à la prochaine élection ? | web | outil web proposé | gpt-5.6-luna |
| 87 | diaspora | fr | Rapatriement d'un corps vers le Sénégal : quelles démarches ? | base | modèle sans web | gpt-5.6-luna |
| 88 | diaspora | fr | Comment investir au Sénégal depuis la diaspora ? | base | modèle sans web | gpt-5.6-luna |
| 89 | diaspora | fr | Peut-on avoir la double nationalité sénégalaise ? | base | modèle sans web | gpt-5.6-luna |
| 90 | diaspora | fr | Combien font 300 euros en francs CFA ? | prete | prête | - |
| 91 | ambigu | fr | Combien ? | precis | modèle sans web | gpt-5.6-luna |
| 92 | ambigu | fr | Et là-bas ? | precis | modèle sans web | gpt-5.6-luna |
| 93 | ambigu | fr | Quel est le meilleur logiciel de comptabilité pour mon garage ? | inconnu | modèle sans web | gpt-5.6-luna |
| 94 | ambigu | fr | Donne-moi le numéro de téléphone du chef de village de Ndiaganiao | inconnu | modèle sans web | gpt-5.6-luna |
| 95 | ambigu | fr | Qui va gagner la prochaine élection présidentielle ? | inconnu | outil web proposé | gpt-5.6-luna |
| 96 | ambigu | fr | Écris un petit poème sur le baobab | base | modèle sans web | gpt-5.6-luna |
| 97 | ambigu | fr | Bonjour | prete | modèle sans web | gpt-5.6-luna |
| 98 | ambigu | fr | Qui es-tu ? | prete | prête | - |
| 99 | ambigu | en | What can you do? | prete | modèle sans web | gpt-5.6-luna |
| 100 | ambigu | fr | C'est combien le kilo ? | precis | modèle sans web | gpt-5.6-luna |
