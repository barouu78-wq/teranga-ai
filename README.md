# teranga-ai
Assistant AI pour commerçants sénégalais

## Déploiement sur Render

1. Envoie ce dépôt vers GitHub.
2. Dans Render, choisis **New → Blueprint**, puis sélectionne le dépôt.
   Render utilise automatiquement [`render.yaml`](render.yaml).
3. Saisis les variables secrètes suivantes dans Render :
   - `OPENAI_API_KEY` : ta clé API OpenAI ;
   - `SITE_URL` : l'URL publique attribuée par Render (par exemple
     `https://teranga-ai.onrender.com`).

`SECRET_KEY` est générée automatiquement par Render. Ne dépose jamais les
clés ou un fichier `.env` dans Git.

Le service démarre avec Gunicorn et Render vérifie son état via `/health`.
