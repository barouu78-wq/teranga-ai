# Gagner de l'argent avec Teranga AI

Trois sources de revenus sont prêtes dans le code. Elles restent **invisibles tant qu'elles ne sont pas activées** : rien ne change pour les visiteurs avant que tu remplisses les étapes ci-dessous.

| Source | Comment ça rapporte | Ce qu'il te faut |
|---|---|---|
| 1. Réservation d'activités (GetYourGuide) | Commission sur chaque excursion réservée via nos liens | Un compte partenaire GetYourGuide |
| 2. Réservation d'hôtels (Booking.com) | Commission sur chaque séjour réservé via nos liens | Un compte affilié Booking.com |
| 3. Adresses partenaires locales | Abonnement payé par l'hôtel, le guide ou le restaurant | Des partenaires et un e-mail de contact |

---

## 1. Activités : GetYourGuide

1. Va sur **partner.getyourguide.com** et crée un compte « Partner ».
2. Site web à déclarer : `https://teranga-ai.fr`. Catégorie : guide de voyage / contenu.
3. Une fois accepté, copie ton **Partner ID** (une suite de lettres et chiffres, par exemple `AB12CD3`).
4. Sur **Render** → ton service → **Environment** → **Add Environment Variable** :
   - Key : `GETYOURGUIDE_PARTNER_ID`
   - Value : ton Partner ID
5. Clique sur **Save Changes**. Le site redémarre en une minute environ.

Résultat : un bouton « 🎟️ Visites et activités » apparaît sur les fiches des lieux (/lieux/…) et sous les réponses du chat qui parlent d'un lieu.

## 2. Hôtels : Booking.com

1. Va sur **booking.com/affiliate-program** et inscris-toi avec le site `https://teranga-ai.fr`.
2. Une fois accepté, récupère ton identifiant d'affilié, appelé **aid** (un nombre).
3. Sur Render, ajoute :
   - Key : `BOOKING_AID`
   - Value : ton numéro aid

Résultat : un bouton « 🏨 Hôtels à … » apparaît à côté du précédent.

## 2 bis. Taxi / VTC : Sengo ou une autre appli

1. Contacte l'appli de taxi (par exemple Sengo, sengoservices.com) et demande un **lien de parrainage ou d'affiliation** : une adresse en `https://…` qui ouvre l'appli ou sa page de téléchargement, et qui leur permet de compter les clients venus de Teranga AI.
2. Sur Render, ajoute :
   - Key : `TAXI_PARTNER_URL`
   - Value : ce lien complet (il doit commencer par `https://`)

Résultat : un bouton « 🚕 Commander un taxi pour … » apparaît sur les fiches des lieux et sous les réponses du chat qui parlent d'un lieu. Chaque clic est compté dans les journaux Render (`affiliate-click kind=taxi`), ce qui te donne un chiffre concret à montrer au partenaire pour négocier une commission.

Sans cette variable, les fiches affichent quand même un bouton « 🧭 Itinéraire » (Google Maps) et le conseil de fixer le prix du taxi avant de monter.

> Les commissions et conditions dépendent de chaque programme : lis-les au moment de l'inscription. Les visiteurs voient toujours la mention « Lien partenaire : Teranga AI peut recevoir une commission ».

## 3. Adresses partenaires (hôtels, guides, restaurants, agences)

C'est la source la plus intéressante au Sénégal : tu vends directement une mise en avant aux professionnels.

### Ce que voit le partenaire
- Sa fiche, avec le badge **Partenaire**, sur les pages des lieux de sa ville.
- L'assistant peut le recommander quand un visiteur cherche ce qu'il propose. Il précise toujours « partenaire de Teranga AI » : c'est une obligation légale et une question de confiance.
- La page **teranga-ai.fr/offres-partenaires** présente les offres.

### Tarifs de lancement : à toi de décider
Suggestions de départ, à ajuster selon tes premiers retours :

| Offre | Prix de lancement suggéré |
|---|---|
| Adresse partenaire (1 ville) | 15 000 à 25 000 FCFA par mois (ou 25 à 40 € pour la France) |
| Bouton Teranga AI aux couleurs du partenaire | 10 000 FCFA par mois |
| Guide thématique sponsorisé | 50 000 FCFA, une seule fois |

Astuce : offre **le premier mois** aux 3 premiers partenaires en échange d'un retour. Ça donne des exemples à montrer.

### Activer le contact
Sur Render, ajoute :
- `CONTACT_EMAIL` : ton e-mail professionnel. Il apparaît sur /offres-partenaires et sur la page de confidentialité.
- `PARTNER_WHATSAPP` : ton numéro WhatsApp **avec l'indicatif, chiffres seulement** (exemple : `221771234567`). Optionnel.

### Ajouter un partenaire
Envoie-moi dans le chat : nom, type (hôtel, guide…), une phrase de description, les lieux ou villes concernés, le site web (https), le téléphone et la date de fin du contrat. J'ajoute la fiche dans `data/partners.json` :

```json
{
  "id": "hotel-de-la-poste-saint-louis",
  "name": "Hôtel Exemple",
  "category": "Hôtel",
  "description": "Hôtel historique au cœur de l'île, à deux pas du pont Faidherbe.",
  "places": ["saint-louis", "Saint-Louis"],
  "url": "https://exemple.sn",
  "phone": "+221 33 000 00 00",
  "until": "2027-01-31"
}
```

Le partenaire disparaît automatiquement après la date `until`.

## Qui démarcher en premier
1. **Hôtels et maisons d'hôtes de Saint-Louis**, très fréquentés par les touristes.
2. **Guides et piroguiers de Gorée et du Saloum** (Ndangane, Toubacouta).
3. **Campements de Lompoul et de Casamance** (Cap Skirring, Kafountine).
4. **Restaurants de la Corniche et des Almadies** à Dakar.
5. **Agences de location de voiture** à Dakar et à l'aéroport AIBD.

Note chaque contact dans `docs/prospection_modele.csv` (date, statut, prochaine action). Les messages WhatsApp prêts à envoyer, les relances et les réponses aux objections sont dans `docs/VENTES-MESSAGES.md`.

## Suivre les résultats
- **Clics sur les liens de réservation** : Render → **Logs** → recherche `affiliate-click`. Chaque ligne indique le type (hôtels ou activités) et le lieu d'où vient le clic.
- **Ventes et commissions** : dans les tableaux de bord GetYourGuide et Booking.
- **Partenaires** : demande-leur combien de clients disent venir de Teranga AI.

## Règles à respecter
- **Google Play** : la réservation de services physiques (hôtel, excursion) par lien externe est autorisée. Ne vends **pas** de contenu numérique (abonnement premium, déblocage de fonctions) dans l'appli sans passer par le système de paiement de Google.
- Toujours signaler les partenaires : c'est déjà fait automatiquement par le site.
- Pas de faux avis ni de faux chiffres d'audience.
- **Impôts** : déclare ces revenus. En France, le statut de micro-entrepreneur est le plus simple pour commencer.

## Voir les clics vers les partenaires

Chaque clic sur un bouton partenaire (hôtels, activités, taxi) est compté par mois et par page
d'origine, sans aucune donnée personnelle. Ces chiffres servent à négocier avec les partenaires.

1. Sur **Render** → ton service → **Environment** → **Add Environment Variable** :
   - Key : `STATS_TOKEN`
   - Value : clique sur **Generate** (Render crée un mot de passe long). Copie-le dans ton
     gestionnaire de mots de passe ; ne l'envoie à personne.
2. **Save Changes**, puis ouvre **https://teranga-ai.fr/stats-partenaires** et colle le mot de passe.

Sans `STATS_TOKEN`, la page n'existe pas (erreur 404). Avec Redis, les chiffres sont gardés
environ un an ; sans Redis, ils repartent à zéro à chaque redéploiement.
