# Plan commercial opérationnel — 30 jours (Dakar d'abord)

Rédigé le 2026-10-10 par l'agent commercial. Ce document **complète** les guides existants, il ne les remplace pas :

| Besoin | Document existant |
|---|---|
| Activer les revenus (affiliation, adresses partenaires, statistiques) | `docs/MONETISATION.md` |
| Messages WhatsApp, objections, procédure « le partenaire dit oui » | `docs/VENTES-MESSAGES.md` |
| 5 messages déjà personnalisés (Saint-Louis, Lompoul, Kafountine, AIBD) | `docs/messages-prospects-prets.md` |
| Démonstration de 5 minutes | `docs/DEMO.md` |
| Stratégie générale et règles (pas de spam, pas de faux chiffres) | `docs/COMMERCIAL_PLAN.md` |

Chaque section sépare **faits vérifiés** (constatés dans le dépôt), **hypothèses** (à confirmer sur le terrain)
et **recommandations**. Aucun prospect, aucune coordonnée et aucun résultat n'est inventé ici.

---

## 1. Faits vérifiés dans le dépôt

| Fait | Où le vérifier |
|---|---|
| La page `/offres-partenaires` présente 3 offres (adresse partenaire, bouton sur le site, guide sponsorisé) et un formulaire « Demander un partenariat ». | `routes/monetization.py` (`OFFERS`, `_request_form`) |
| Types d'activité acceptés par le formulaire : hôtel/maison d'hôtes/campement, restaurant/bar, guide/piroguier, taxi/VTC/location, agence de voyage, autre. | `services/partner_requests.py` (`KINDS`) |
| Les demandes reçues sont gardées dans Redis (200 au plus, environ 400 jours) et lisibles sur `/stats-partenaires`, protégée par `STATS_TOKEN`. Les journaux ne contiennent pas les coordonnées. | `services/partner_requests.py`, `routes/monetization.py` |
| Les clics vers les liens partenaires (`/go/hotels`, `/go/activites`, `/go/taxi`) sont comptés par mois et par fiche d'origine, sans donnée personnelle, avec une limite anti-gonflage. | `services/click_stats.py`, `routes/monetization.py` |
| **Aucun partenaire n'est en ligne** : la liste est vide. | `data/partners.json` (`"partners": []`) |
| Un partenaire est rattaché à des lieux (identifiants de `data/senegal_knowledge.json`, localités ou régions) et disparaît après sa date `until`. | `services/monetization.py` (`partners_for_place`, `_is_active`) |
| Le widget `widget.js` ajoute un bouton « Une question sur le Sénégal ? » et transmet `utm_source=<data-partner>`, `utm_medium=widget`. Ses couleurs sont **fixes** : la version « à vos couleurs » annoncée sur `/offres-partenaires` demande encore du développement. | `static/widget.js` |
| Fiches existantes utiles pour Dakar : `dakar`, `goree`, `dakar-corniche`, `dakar-renaissance`, `pointe-des-almadies`, `ile-de-ngor`, `lac-rose`, `grande-mosquee-dakar`, `cathedrale-dakar`. | `data/senegal_knowledge.json` |
| Pages commerciales en ligne : `/pour-les-entreprises`, `/partenaires`, `/presse`, `/media-kit`. | `services/seo.py` |
| `/partners` et `/opportunities` servent **Teranga Projet** (jeunes porteurs de projets) : ce ne sont pas des pages de vente aux entreprises. | `routes/youth_projects.py` |
| Il n'existe **ni comptes partenaires, ni CRM, ni paiement en ligne** dans le code. Le suivi des prospects se fait dans des fichiers CSV. | `docs/prospection_modele.csv` |
| La liste `docs/prospects-octobre-2026.csv` (13 lignes) cible surtout Saint-Louis, Lompoul, le Saloum et la Casamance. Elle n'a **ni URL source précise ni date de vérification**, et contient le nom d'un gérant. | `docs/prospects-octobre-2026.csv` |

### Données manquantes (non vérifiées)
- Audience réelle du site : non mesurée dans le dépôt. La mesure n'existe que si `ANALYTICS_SCRIPT_URL` est configurée sur Render, ce que l'agent ne peut pas voir.
- Nombre de demandes reçues et de clics : visibles seulement sur `/stats-partenaires` en production, non consultés.
- Prix acceptables pour le marché sénégalais : aucun retour client enregistré.
- Moyen de paiement des abonnements : Wave et Orange Money sont cités dans `docs/VENTES-MESSAGES.md`, sans procédure écrite.

---

## 2. Offres proposées

> **Tous les prix ci-dessous sont des hypothèses de départ, non validées par le marché.** Ils reprennent les
> fourchettes déjà notées dans `docs/MONETISATION.md` pour rester cohérents. Ils doivent être testés en entretien
> (question : « Combien seriez-vous prêt à payer pour ce résultat ? ») avant d'être affichés.

### Offre A — « Adresse partenaire » (hôtels, maisons d'hôtes, restaurants, guides)
- **Problème client** : un petit établissement dépend de Booking, Google Maps ou du bouche-à-oreille ; il est peu visible au moment où le voyageur prépare son séjour et pose ses questions.
- **Valeur pour le partenaire** : apparaître, avec la mention « Partenaire », sur la fiche du lieu de son quartier ou de sa ville, et dans les recommandations de l'assistant quand un visiteur cherche ce qu'il propose. Lien direct vers son site ou son téléphone.
- **Fonctionnalités nécessaires** : existent déjà (`data/partners.json`, badge, contexte de l'assistant, date de fin automatique).
- **Hypothèse de prix (non validée)** : 15 000 à 25 000 FCFA par mois, premier mois offert aux premiers partenaires.
- **MVP réaliste** : 3 partenaires gratuits pendant un mois à Dakar, ajoutés à la main dans `data/partners.json`, avec un bilan écrit à la fin du mois (clics, retours du partenaire).

### Offre B — « Bouton Teranga AI sur votre site » (agences de voyage, hôtels, PME)
- **Problème client** : l'équipe répond toujours aux mêmes questions (transfert depuis AIBD, météo, quartiers, que visiter) par téléphone ou WhatsApp.
- **Valeur pour le partenaire** : ses clients trouvent ces réponses eux-mêmes, sur son site, en français, anglais ou wolof ; le partenaire garde son propre site.
- **Fonctionnalités nécessaires** : le widget de base existe (`/widget.js`, `data-partner`). Pour une version payante, il manque : couleurs personnalisables et mise en avant des adresses du partenaire dans les réponses ouvertes depuis son bouton.
- **Hypothèse de prix (non validée)** : version de base gratuite ; version personnalisée autour de 10 000 FCFA par mois.
- **MVP réaliste** : version gratuite installée chez 2 agences ou PME de Dakar. On mesure les visites `utm_source` (si la mesure d'audience est active) avant de développer la version payante.

### Offre C — « Pilote PME / agence » de 6 semaines
- **Problème client** : une agence, une école ou une PME veut tester l'IA pour ses clients ou sa communication, sans projet technique lourd.
- **Valeur pour le partenaire** : un pilote cadré avec des indicateurs fixés à l'avance (voir `docs/DEMO.md`), un guide thématique dédié si c'est pertinent (gastronomie, excursions, artisanat), clairement indiqué comme partenariat.
- **Fonctionnalités nécessaires** : existantes (widget, partage de réponses `/partage`, fiches lieux) ; le guide thématique est un contenu à rédiger, avec des faits sourcés.
- **Hypothèse de prix (non validée)** : gratuit pendant le pilote ; guide sponsorisé autour de 50 000 FCFA, une seule fois.
- **MVP réaliste** : 1 pilote signé par écrit, avec un compte rendu partagé à la fin.

---

## 3. Plan de prospection — 30 jours

### Pourquoi Dakar d'abord
- Dakar est la porte d'entrée aérienne du pays (aéroport AIBD, déjà traité par la page `/aibd-dakar`) et le dépôt a déjà au moins 9 fiches de lieux dans la région (voir § 1).
- Le propriétaire peut faire des démonstrations en personne plus facilement.
- Extensions justifiées ensuite : **Saint-Louis** (fiche existante et 3 prospects déjà repérés), **Petite-Côte et Saloum** (prospects déjà repérés à Ndangane et Toubacouta), **Lompoul**. La Casamance vient après, faute de démonstration possible sur place.

### Segments par ordre de priorité
1. Maisons d'hôtes et petits hôtels de Dakar (Plateau, Almadies, Ngor, Yoff) : offre A.
2. Guides et piroguiers de Gorée et de l'île de Ngor : offre A.
3. Restaurants de la Corniche et des Almadies : offre A.
4. Agences de voyage et transferts AIBD : offres B et A.
5. PME, écoles et incubateurs de Dakar : offre C.

### Objectifs hebdomadaires (objectifs d'activité, pas des résultats promis)

| Semaine | Actions | Objectifs mesurables |
|---|---|---|
| 1 | Construire la liste : 20 établissements de Dakar (segments 1 à 3), chacun vérifié avec une source publique datée. Préparer une capture de la fiche du lieu concerné. | 20 lignes complètes dans le CSV (colonnes `source_url` et `date_verification` remplies). |
| 2 | Premier contact avec 10 prospects qualifiés (score ≥ 3, voir § 4), un message personnalisé chacun. | 10 contacts envoyés ; nombre de réponses noté. |
| 3 | Relance unique (J+4 ou J+5) ; démonstrations ; 5 premiers contacts du segment 4 ou 5. | Démonstrations réalisées, essais acceptés, notés dans le CSV. |
| 4 | Mise en ligne des essais acceptés ; bilan ; décision sur l'extension à Saint-Louis. | Partenaires en essai en ligne ; bilan écrit (chiffres réels seulement). |

### Indicateurs de conversion (à calculer, jamais à estimer)
- Taux de réponse = réponses / contacts envoyés.
- Taux de démonstration = démonstrations / réponses.
- Taux d'essai = essais acceptés / démonstrations.
- Taux de conversion payante = abonnements payés / essais terminés.
- Délai moyen entre le premier contact et l'essai.
- Côté produit : clics `/go` et demandes `/stats-partenaires` par mois ; visites `utm_source` du widget si la mesure d'audience est active.

> Repère d'hypothèse (à remplacer par les chiffres réels dès la semaine 2) : environ 1 réponse pour 3 contacts
> et 1 essai pour 3 démonstrations. Ce ne sont pas des résultats.

---

## 4. Qualification et suivi

### Critères de qualification (1 point chacun, priorité si score ≥ 3)
1. L'organisation existe : vérifiée sur une source publique (site officiel, fiche d'office du tourisme, annuaire professionnel reconnu, page professionnelle publique).
2. Ses coordonnées **professionnelles** sont publiées volontairement (site, page professionnelle, annuaire).
3. Elle est située près d'un lieu qui a déjà une fiche sur teranga-ai.fr.
4. Elle reçoit des voyageurs ou des membres de la diaspora (activité visible sur sa propre page).
5. Elle a une présence en ligne active (site ou page mise à jour récemment).

### Étapes de suivi (colonne `statut`)
`identifié` → `vérifié` → `contacté` → `relancé` → `démo` → `essai` → `payant`
ou, à tout moment : `pas intéressé` (recontact possible après 3 mois) / `ne plus contacter` (définitif).

### Outil de suivi
Le modèle `docs/prospection_modele.csv` contient maintenant les colonnes `segment`, `source_url`,
`date_verification` et `score`. Une ligne n'est contactée que si `source_url` et `date_verification` sont remplies.

**Données personnelles** : noter uniquement des coordonnées professionnelles publiées par l'organisation, pas
de numéro personnel ni de nom de salarié trouvé ailleurs. Le Sénégal encadre ces données (loi n° 2008-12 sur la
protection des données à caractère personnel, contrôlée par la CDP). Le fichier de travail rempli devrait rester
**hors du dépôt public** (tableur privé) : seul le modèle vide est versionné.

**Recommandation** : avant tout contact issu de `docs/prospects-octobre-2026.csv`, revérifier chaque ligne et
compléter l'URL source et la date, puis la recopier dans le tableur privé.

---

## 5. Modèles de messages complémentaires

Les messages WhatsApp pour hôtels, guides, restaurants et agences existent déjà dans `docs/VENTES-MESSAGES.md`.
Ci-dessous : ce qui manque (e-mail, PME, compte rendu après démonstration, dernière relance). Remplacer les
[crochets] et citer **un détail vrai** sur l'activité, trouvé sur sa source publique.

### E-mail — hôtel ou maison d'hôtes à Dakar
> Objet : Recommander [Nom de l'établissement] aux voyageurs qui préparent leur séjour à Dakar
>
> Bonjour [Madame / Monsieur Nom],
>
> Je m'appelle [Prénom Nom] et je développe Teranga AI (teranga-ai.fr), un assistant numérique gratuit qui aide
> les voyageurs et la diaspora à préparer leur séjour au Sénégal.
>
> J'ai découvert [Nom de l'établissement] sur [source] : [détail vrai, par exemple « votre terrasse face à l'île de Ngor »].
> Nous cherchons quelques adresses de confiance près de [lieu] pour les recommander, toujours avec la mention
> « Partenaire ». Le premier mois est offert, sans engagement.
>
> Le service est récent : je ne vous annoncerai pas de chiffres d'audience que je ne peux pas prouver. Je peux en
> revanche vous montrer en 10 minutes comment votre établissement apparaîtrait.
>
> Seriez-vous disponible [jour] ou [jour] ?
>
> Si vous ne souhaitez pas être recontacté, il suffit de me le dire.
>
> [Prénom Nom] — Teranga AI — teranga-ai.fr

### E-mail — PME, école ou incubateur (offre C)
> Objet : Un pilote de 6 semaines avec Teranga AI pour [Nom de l'organisation] ?
>
> Bonjour [Prénom],
>
> Teranga AI (teranga-ai.fr) est un assistant numérique consacré au Sénégal, en français, anglais et wolof, à l'écrit
> comme à la voix. J'ai vu que [Nom de l'organisation] [détail vrai : activité, événement, public].
>
> Je vous propose un pilote gratuit de 6 semaines : un bouton Teranga AI sur votre site ou un guide pratique pour
> votre public, avec des indicateurs définis ensemble au départ et un bilan partagé à la fin.
>
> Pourriez-vous m'accorder 15 minutes pour en parler ?
>
> Si ce n'est pas le bon interlocuteur ou le bon moment, je vous remercie de me le dire.
>
> [Prénom Nom] — Teranga AI

### WhatsApp — guide ou piroguier à Gorée ou Ngor
> Salaam aleekum [Prénom],
> Je suis [Ton prénom], de Teranga AI (teranga-ai.fr), un assistant qui aide les visiteurs à préparer leur séjour.
> Beaucoup demandent comment visiter [Gorée / l'île de Ngor] avec quelqu'un de sérieux. J'ai vu [détail vrai].
> J'aimerais vous recommander sur la page [Gorée / Ngor], avec la mention « Partenaire » ; le premier mois est offert.
> Est-ce que je peux vous montrer en 2 minutes ?

### Compte rendu après une démonstration
> Bonjour [Prénom], merci pour votre temps aujourd'hui.
> Ce que nous avons convenu : [offre A / B / C], essai du [date] au [date], sans engagement.
> Ce que je mettrai en ligne : [nom, description d'une phrase, lieu, lien, téléphone que vous m'avez donnés].
> Ce que nous regarderons à la fin : [clics vers votre lien / visites par votre bouton / vos retours clients].
> Pouvez-vous me confirmer ces informations par écrit ?

### Dernière relance (une seule fois, 4 à 5 jours après le premier message)
> Bonjour [Prénom], je reviens vers vous une dernière fois au sujet de Teranga AI. Si le moment n'est pas bon,
> aucun souci : je ne vous relancerai pas. Bonne journée !

---

## 6. Recommandations outillage (non implémentées)

Classées par utilité ; chacune serait une PR distincte, avec tests.
1. **Exporter les demandes de `/stats-partenaires` en CSV** pour les recopier dans le tableur de suivi (aujourd'hui : copie à la main).
2. **Widget à couleurs personnalisables** (`data-color`), condition de l'offre B payante. Respecter la CSP et le contraste.
3. **Compter les ouvertures du widget par `data-partner`** dans `ClickStats`, sans donnée personnelle, pour un chiffre à montrer au partenaire même sans outil d'audience.
4. **Pas de CRM ni de comptes partenaires** tant qu'il y a moins de 20 partenaires : le tableur privé suffit et évite de stocker des données personnelles sur le serveur.

## 7. Ce que l'agent ne fait pas
Il ne contacte personne, n'envoie aucun message, ne crée aucun compte et n'engage aucune dépense. Chaque envoi
reste une décision du propriétaire.
