---
name: faire-une-video
description: Fabriquer une vidéo courte de Teranga AI (Reels, TikTok, présentation) à partir des vrais écrans du site et d'une animation HTML, rendue image par image en MP4 avec scripts/video/. À utiliser quand le propriétaire demande une vidéo, ou pour tourner un script de vidéo écrit par l'agent communication.
---

# Faire une vidéo de Teranga AI

Trois modèles existent dans `scripts/video/modeles/`, tous au format vertical 9:16 (1080×1920) :

| Modèle | Durée | Contenu |
|---|---|---|
| `presentation.html` | 25 s | logo, questions en français, anglais et wolof, voix, planificateur, repères vérifiés, teranga-ai.fr |
| `clip-pub.html` | 19 s | style « pub d'application » : ruban doré, « Trop de questions ? », TERANGA vertical, téléphone en 3D avec les vrais écrans |
| `reponse-nuit.html` | 18 s | style « Nuit dorée » (noir et or) : une question, la **vraie réponse prête** de Teranga en mode nuit, ses chiffres, l'adresse ; recette pas à pas dans le skill `video-reponse` |

## Étapes
1. Lancer le site en local, sans vraie clé : `OPENAI_API_KEY=test-key python -c "from app import app; app.run(port=5055)"`.
2. Capturer les vrais écrans (si le modèle en montre) :
   `python scripts/video/ecrans.py /chemin/captures --theme light` (ou `dark`) pour les pages ;
   `python scripts/video/reponses.py /chemin/captures --question nom "question" "texte attendu"` pour une vraie réponse
   prête (site lancé avec `ALLOWED_ORIGINS="http://127.0.0.1:5055"`, sinon `/chat` répond 403).
3. Copier un modèle, changer les textes, les durées (`animation-delay`) et l'ordre des scènes.
4. Rendre : `python scripts/video/rendu.py mon-modele.html sortie.mp4 --duree 19 --ecrans /chemin/captures`.
5. Regarder avant de livrer : extraire quelques images avec ffmpeg et les lire
   (`ffmpeg -ss 5 -i sortie.mp4 -vframes 1 image.jpg`), surtout la **première** et la **dernière**.
6. Livrer le MP4 au propriétaire, avec la durée et le format.

Les modèles sont dessinés pour 540×960 (rendu ×2). L'option `--format 16x9` demande un modèle dessiné pour
960×540 : copier un modèle et changer `html,body{width;height}` et les positions.

## Règles
- **Vrai seulement** : de vraies fonctions du site, de vrais écrans, aucun chiffre ni avis inventé. Un exemple
  (itinéraire, question) est marqué « Exemple ».
- **Aucune réponse de l'IA inventée** : en local, sans clé, l'IA ne répond pas. Ne pas fabriquer de fausse réponse.
- **Personnes** : aucune personne générée ; une vraie personne seulement sur une photo ou une vidéo fournie par le
  propriétaire, avec l'accord de la personne. Le logo de Teranga (baobab doré, version 3.0) remplace le personnage.
- **Première image** : le titre et le logo sont visibles dès la première image (vignette des réseaux, lecteurs qui ne
  démarrent pas seuls). Une première image vide a déjà été livrée une fois, le 17 octobre 2026.
- **Son** : pas de musique ni de voix dans le MP4. Le propriétaire ajoute une musique libre de droits dans CapCut,
  Instagram ou TikTok.
- **Publication** : la visibilité revient à ChatGPT et au propriétaire. Ne jamais publier soi-même.
- **Date** : un fait qui change avec la date (heure d'été, fête à venir) ne doit pas devenir faux après la publication.
- **Captures** : la question et le début de la réponse visibles, aucun mot coupé ; un texte trop long se règle par la
  taille de police (« Commer-çants » a dû être refait le 24 octobre 2026).
- **Légendes** : livrer avec la vidéo un fichier de légendes prêtes à copier-coller, avec seulement des faits montrés.
- Pas de logo d'une autre marque, rien sur la politique.
