# Teranga AI

Assistant IA pour découvrir, comprendre et valoriser le Sénégal.

## Développement local

1. Créer un environnement virtuel.
2. Installer les dépendances :
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Copier `.env.example` vers `.env` et renseigner `OPENAI_API_KEY`.
4. Lancer :
   ```bash
   python app.py
   ```

## Tests

```bash
pytest -q
```

## Déploiement Render

Le fichier `render.yaml` décrit le service web et utilise Gunicorn.
La clé `OPENAI_API_KEY` doit rester un secret Render et ne doit jamais être commitée.

## CI

GitHub Actions exécute les tests sur les pushes vers `main`, les pull requests et sur demande manuelle.
