# Liens entrants : les sites qui peuvent parler de Teranga AI

Recherche du 8 novembre 2026. Le site est propre techniquement (audit : 206 pages, 0 problème), mais **aucune page
d'un autre site ne cite teranga-ai.fr** : une recherche sur « teranga-ai.fr » ne renvoie que d'autres « Teranga ».
Google fait davantage confiance à un site dont d'autres sites parlent. Ce fichier liste les endroits gratuits et
sérieux où obtenir un lien, du plus rapide au plus long.

**Règles.** C'est le propriétaire qui inscrit le site et envoie chaque message (aucun agent ne publie ni n'écrit à
personne). Rien de payant : pas d'achat de liens, pas de service « 300 annuaires pour 20 € » (Google pénalise ces
liens). Aucun chiffre inventé dans les textes : seulement ce que le site montre.

## 1. À faire d'abord (15 minutes, déjà nos comptes)

| Où | Quoi faire | Pourquoi |
|---|---|---|
| Google Search Console (propriété `teranga-ai.fr`) | Sitemaps → envoyer `https://teranga-ai.fr/sitemap.xml` ; puis « Inspection de l'URL » → « Demander l'indexation » pour `/`, `/joj-dakar-2026`, `/urgences`, `/lieux` | Google découvre les 206 pages plus vite |
| Bing Webmaster Tools (site déjà vérifié : balise `msvalidate.01`) | Sitemaps → envoyer la même adresse | Bing alimente aussi d'autres moteurs |
| GitHub → Actions → « Submit IndexNow URLs » → Run workflow | Une fois, puis après chaque ajout de pages | Signale les 206 pages à Bing, Yandex, Seznam (IndexNow) |

## 2. Annuaires de produits (gratuits, en anglais)

| Site | Comment | Ce qu'on sait (vérifier sur place) |
|---|---|---|
| [Product Hunt](https://www.producthunt.com/launch/preparing-for-launch) | Compte → « Submit » → « New product » | Le guide officiel dit que chacun peut présenter son propre produit, sans payer. Choisir un mardi, mercredi ou jeudi. |
| [SaaSHub](https://www.saashub.com) | `saashub.com/services/submit` | Fiche de base gratuite, validée à la main (de 1 à plusieurs semaines selon les sources). Formule « mise en avant » payante : ne pas la prendre. |

Texte prêt (Product Hunt, SaaSHub) :

```
Nom : Teranga AI
Accroche : AI assistant for Senegal: travel, paperwork, money
Description : Teranga AI answers practical questions about Senegal in French, English and Wolof: visas, emergency numbers, Woyofal electricity, mobile money scams, holidays and 98 sourced places across the 14 regions. Free, no account needed.
Lien : https://teranga-ai.fr/?utm_source=producthunt
```

(Pour SaaSHub, remplacer `producthunt` par `saashub` dans le lien.)

## 3. Sénégal : tourisme et annuaires

| Site | Comment | Ce qu'on sait |
|---|---|---|
| [Au-Sénégal.com](https://au-senegal.com/pourquoi-devenir-partenaire-de-au-senegal-com,18038.html) | Formulaire de la page « Pourquoi devenir partenaire » | Portail touristique ; il annonce lui-même plus de 650 000 visiteurs par mois. Le formulaire vise les structures présentes sur le portail : demander s'il peut citer Teranga dans ses pages pratiques. |
| [Go Africa Online, annuaire Sénégal](https://www.goafricaonline.com/sn/annuaire) | Inscription en ligne | Annuaire d'entreprises ; l'inscription de base est annoncée comme possible en ligne, conditions à vérifier. |

## 4. Médias tech du Sénégal (un article vaut plus que dix annuaires)

| Média | Contact | Ce qu'on sait |
|---|---|---|
| [Social Net Link](https://socialnetlink.org) | `contact@socialnetlink.org` (adresse « rédaction » du magazine de mai 2025 : la vérifier sur le site) | Média sénégalais des technologies depuis 2013, rubrique « intelligence artificielle ». |

Message prêt (à envoyer par le propriétaire) :

```
Objet : Teranga AI, un assistant IA gratuit pour les questions pratiques sur le Sénégal

Bonjour,

Je m'appelle [prénom nom], je suis le créateur de Teranga AI (https://teranga-ai.fr/?utm_source=socialnetlink).
C'est un assistant IA gratuit, sans compte, qui répond en français, en anglais et en wolof aux questions
pratiques sur le Sénégal : visa, numéros d'urgence, crédit Woyofal, arnaques au mobile money, jours fériés,
et 98 lieux sourcés dans les 14 régions.

Les réponses sur les démarches s'appuient sur des sources officielles, citées et datées, et indiquent ce qui
reste à vérifier.

Je serais heureux de vous présenter l'outil, ou de répondre à vos questions pour un article.

Bien cordialement,
[prénom nom]
[téléphone]
```

## 5. À ne pas faire

- Acheter des liens ou payer un « pack d'annuaires » : liens de mauvaise qualité, risque de pénalité Google.
- Poster le lien en boucle dans des forums ou des groupes : c'est du spam, et ça peut faire bannir le compte.
- Créer une page Wikipédia sur Teranga : Wikipédia interdit l'autopromotion.

## 6. Suivi

Noter ici chaque démarche (date, statut, lien obtenu). Le compteur des réseaux (`docs/LIENS-MARQUES.md`) ne
compte que TikTok, Instagram, WhatsApp, Facebook et YouTube : les visites marquées `utm_source=producthunt`,
`saashub` ou `socialnetlink` se retrouvent dans les journaux Render (recherche du texte `utm_source=producthunt`).

| Date | Site | Démarche | Statut | Lien publié |
|---|---|---|---|---|
| | | | | |

Sources de cette recherche (8 novembre 2026) : guide de lancement Product Hunt
(producthunt.com/launch/preparing-for-launch) ; guides tiers sur SaaSHub (ideaproof.io, nicklaunches.com) ;
page partenaires d'au-senegal.com ; annuaire goafricaonline.com/sn/annuaire ; magazine Socialnetlink n° 3
(mai 2025, socialnetlink.org).
