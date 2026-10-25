---
name: video-reponse
description: Fabriquer une vidéo courte « question → vraie réponse de Teranga » (Reels, TikTok, statut WhatsApp) dans le style « Nuit dorée », à partir d'une réponse prête capturée sur le site local. À utiliser quand le propriétaire demande une vidéo sur un sujet précis (plat, fête, conversion, urgences, présentation de Teranga…), ou pour la vidéo de la semaine.
---

# Vidéo « question → vraie réponse »

Recette éprouvée le 24 octobre 2026 (vidéos du plat national et « Un assistant pour tout le Sénégal »). Pour les autres
formats et les règles générales, voir aussi le skill `faire-une-video`.

## 1. Choisir une question qui a une réponse prête
En local, sans clé, **seules les réponses prêtes** répondent (`services/quick_answers.py`). Sujets possibles aujourd'hui :
numéros d'urgence, conversion euro ↔ FCFA, coût d'un transfert d'argent, heure à Dakar et décalage avec Paris,
indicatif +221, dates des fêtes, plats de la base (« C'est quoi le plat national ? »), présentation de Teranga
(« Que peux-tu faire ? »). Pour vérifier une question : `quick_answer({"message": q, "language": "fr"}, {})` ne doit pas
renvoyer None.

**Une réponse qui dépend de la date** ne doit pas devenir fausse après la publication. Exemple : le 24 octobre, l'heure à
Dakar donnait « 2 h de moins qu'à Paris (heure d'été) », faux dès le lendemain (passage à l'heure d'hiver). Tourner une
telle vidéo après le changement, ou ne pas montrer la partie datée.

## 2. Capturer la vraie réponse
```bash
OPENAI_API_KEY=test-key ALLOWED_ORIGINS="http://127.0.0.1:5055" python -c "from app import app; app.run(port=5055)" &
python scripts/video/reponses.py /chemin/captures --theme dark \
    --question reponse "C'est quoi le plat national ?" "Plat national"
```
Sans `ALLOWED_ORIGINS`, `/chat` répond 403 « Origine non autorisée ». Le script remonte le fil jusqu'à la question
(`reponse.jpg`) et garde aussi la fin (`reponse-bas.jpg`). **Regarder la capture** : la question et le début de la
réponse doivent être visibles, rien de coupé. Arrêter le site après.

## 3. Écrire la vidéo
Copier `scripts/video/modeles/reponse-nuit.html` dans un dossier de travail (pas dans `modeles/` : un modèle ajouté là
doit être déclaré dans `tests/test_video_scripts.py`). Changer seulement les textes :
- scène 1 : thème (« CUISINE »), titre en question, accroche ;
- scène 2 : deux cartes avec deux faits de la réponse ;
- scène 4 : un détail ou un chiffre de la réponse ;
- scène 5 : l'adresse et une phrase d'appel.

Chaque fait écrit dans la vidéo doit se lire **mot pour mot ou presque** dans la capture. Un mot trop long pour sa
carte se règle par la taille de police, pas par une coupure (« Commer-çants » a dû être refait).

## 4. Rendre et regarder
```bash
python scripts/video/rendu.py ma-video.html sortie.mp4 --duree 18 --ecrans /chemin/captures
for t in 0 2 5.5 9 14.5 17.5; do ffmpeg -loglevel error -y -ss $t -i sortie.mp4 -vframes 1 -vf scale=270:-1 img-$t.jpg; done
```
Lire les images, surtout la **Première image** (titre et logo visibles) et la dernière (teranga-ai.fr).

## 5. Livrer
Le MP4 (18 s, 9:16, sans son) et un fichier de légendes prêtes à copier-coller, avec seulement des faits de la réponse.
Le propriétaire ajoute une musique libre de droits et publie. **Ne jamais publier** soi-même.

## Règles (celles de `faire-une-video` s'appliquent toutes)
- **Aucune réponse de l'IA inventée** : seule une réponse prête capturée sur le site apparaît à l'écran.
- Aucune personne générée ; le logo de Teranga (baobab doré) représente le service.
- Pas de logo d'une autre marque, rien sur la politique, pas de pulaar (pas réintroduit sans décision du propriétaire).
