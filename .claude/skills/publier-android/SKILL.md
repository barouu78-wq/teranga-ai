---
name: publier-android
description: Préparer et publier l'application Android de Teranga AI sur Google Play (test interne, test fermé, fiche, questionnaires, vérification du lien assetlinks). À utiliser quand le propriétaire parle de Google Play, du paquet .aab/.apk ou du test Android.
---

# Publier l'application Android

L'application est un **TWA** (paquet `fr.teranga_ai`, généré avec PWABuilder) qui affiche le site
`https://teranga-ai.fr` sans barre d'adresse. Le site évolue seul : **une modification du site ne demande
aucune nouvelle version Android**. Une nouvelle version n'est nécessaire que pour changer le paquet
(icône, nom, paramètres) ; son numéro de version doit alors augmenter.

## Règles de sécurité (non négociables)
- Ne jamais lire, demander, afficher ni commiter `signing.keystore`, `signing-key-info.txt`, ses mots de passe
  ni aucune clé. Seuls les fichiers **publics** (`.aab`, `.apk`, certificat `.pem`) peuvent circuler.
- Les empreintes SHA-256 de `routes/legal.py` (`ANDROID_CERT_SHA256`) sont publiques : le fichier
  `assetlinks.json` est fait pour être lu par tous. La variable d'environnement du même nom ne fait
  qu'**ajouter** des empreintes.

## 1. Avant de publier : le site
```bash
OPENAI_API_KEY=test-key python -m pytest -q tests/test_legal.py tests/test_play_listing.py tests/test_offline.py
```
- `https://teranga-ai.fr/.well-known/assetlinks.json` doit contenir le paquet `fr.teranga_ai` et les deux
  empreintes (clé de signature Google Play + clé d'importation). Sans cela, l'application affiche une barre
  d'adresse au lieu du plein écran.
- `/confidentialite` doit rester cohérente avec le formulaire « Sécurité des données ».

## 2. Fiche Play Console
Textes prêts à copier dans `docs/google-play/FICHE-GOOGLE-PLAY.md` (limites de caractères vérifiées par
`tests/test_play_listing.py`) ; captures et image de présentation dans `docs/google-play/`.
Contenu généré par IA : **Oui**, avec le bouton « Signaler ». Position de l'utilisateur : **Non**.

## 3. Test interne (déjà fait une fois)
Play Console → **Tests internes** → Créer une version → importer le `.aab` →
**Enregistrer et publier**. Ajouter les e-mails Gmail des testeurs, partager le lien d'adhésion
(« opt-in ») ; le testeur doit ouvrir le lien avec le compte Gmail de la liste.
Si l'importation affiche une erreur rouge : retirer le fichier (croix) et **réimporter un fichier neuf**.

## 4. Test fermé (avant la production)
Les nouveaux comptes personnels doivent faire tester l'application par un nombre minimal de testeurs pendant
une durée minimale (au dernier contrôle : **12 testeurs pendant 14 jours consécutifs**). Cette règle peut
changer : la confirmer dans la Play Console avant de promettre une date au propriétaire.
Demander au propriétaire les adresses Gmail ; ne jamais en inventer.

## 5. Vérifier sur un téléphone
Application sans barre d'adresse · le chat répond à « Que voir à Dakar ? » · l'autorisation du micro
est demandée · le planificateur de voyage fonctionne · les pages déjà vues restent lisibles hors connexion.
Si une barre d'adresse apparaît : empreinte manquante dans `assetlinks.json`.

## 6. Production
Après le test fermé : Production → Créer une version → envoyer à l'examen de Google. Délais et
décisions dépendent de Google : ne rien promettre.
