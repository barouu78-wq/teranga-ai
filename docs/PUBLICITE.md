# Publicité Google (AdSense) sur Teranga AI

Décision du propriétaire du 13 novembre 2026 : des annonces Google qui rapportent, avec la maquette validée le même
jour. Le code est dans `services/adsense.py`. Il reste **éteint** tant que les variables ci-dessous ne sont pas
définies sur Render.

## Ce que voient les visiteurs

- **Une seule annonce par page**, marquée « Publicité », tout en bas des pages de guide (lieux, régions, guides,
  calendrier…), après le contenu.
- **Jamais d'annonce** sur l'accueil et le chat, le planificateur, les urgences, la confidentialité, les pages
  partenaires et presse, les réponses partagées, ni sur les pages privées.
- Si Google n'a rien à montrer, l'emplacement disparaît.
- La page Confidentialité ajoute alors un paragraphe « Publicité » (cookies de Google, consentement en Europe).

## Les étapes, dans l'ordre

1. **Créer le compte** sur adsense.google.com (gratuit) et ajouter le site `teranga-ai.fr`. Google donne
   l'identifiant du compte : `ca-pub-` suivi de 16 chiffres. Il n'est pas secret : il apparaît dans les pages.
2. **Vérification du site** : choisir la méthode « ads.txt ». Ajouter sur Render la variable `ADSENSE_CLIENT` avec
   cet identifiant. Le site publie alors `https://teranga-ai.fr/ads.txt`, mais n'affiche encore aucune annonce.
   Google examine ensuite le site avant d'accepter le compte.
3. **Une fois le compte accepté**, dans AdSense :
   - **Confidentialité et messages → RGPD** : publier le message de consentement de Google. Il est obligatoire
     pour les visiteurs européens, et Google l'affiche lui-même.
   - **Contrôle des annonces → catégories sensibles** : bloquer au minimum les jeux d'argent, les rencontres et
     l'argent facile, puisque le site met en garde contre les arnaques.
   - **Annonces → Par bloc d'annonces → Annonces display** : créer un bloc « responsive » nommé
     « Teranga fin de page ». Son numéro est le `data-ad-slot`.
4. Ajouter sur Render la variable `ADSENSE_SLOT` avec ce numéro. Les annonces s'affichent après le redéploiement.

Pour tout arrêter, il suffit de supprimer `ADSENSE_SLOT` sur Render. Supprimer aussi `ADSENSE_CLIENT` retire
`ads.txt`.

## Sécurité

Google ne prend en charge qu'une CSP « stricte » : un nonce et `'strict-dynamic'`, parce que ses domaines
changent. Cette CSP ne vaut que pour les pages qui portent une annonce, et seuls les scripts du site y reçoivent
le nonce. L'accueil et le chat gardent leur CSP habituelle. Les pages avec annonce ne sont plus gardées en cache
public, puisque le nonce change à chaque visite.

## À vérifier avant d'allumer

- **L'application Android** (TWA) affiche le même site. Il faut vérifier dans les règles de Google Play et
  d'AdSense que des annonces AdSense sont permises dans une TWA.
- **Ce que ça rapporte** dépend du nombre de visiteurs. Avec le trafic de novembre 2026 (une dizaine de visites
  par semaine), ce sera presque rien au début.
