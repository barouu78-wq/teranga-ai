"""Réglages Gunicorn du site, lus automatiquement (`./gunicorn.conf.py`) quel que soit l'hébergeur.

Pourquoi un fichier : sur Render, la commande de démarrage saisie dans le tableau de bord
(`gunicorn app:app`) remplace le `Procfile` et `render.yaml`. Gunicorn tournait donc avec ses valeurs
par défaut : un seul processus « sync » et un délai de 30 s. Une génération longue (planificateur de
voyage, réponse de l'IA) était alors coupée par `WORKER TIMEOUT`, et une seule requête lente bloquait
tous les visiteurs. Ce fichier applique les mêmes valeurs que `Procfile`, `render.yaml` et `Dockerfile`.

Les options passées en ligne de commande (`--workers`, `--timeout`…) l'emportent sur ce fichier.
"""
import os


def _entier(nom, defaut, minimum=1, maximum=16):
    """Lit un entier dans l'environnement ; une valeur absente, invalide ou hors bornes donne le défaut."""
    try:
        valeur = int(os.environ.get(nom, ""))
    except ValueError:
        return defaut
    return valeur if minimum <= valeur <= maximum else defaut


# 2 processus × 4 fils : une réponse en cours de génération ne bloque plus les autres visiteurs.
# Avec plus d'un fil, Gunicorn choisit lui-même le mode « gthread ».
workers = _entier("GUNICORN_WORKERS", 2)
threads = _entier("GUNICORN_THREADS", 4)

# Une réponse de l'IA ou un plan de voyage peut durer plus de 30 s (le défaut de Gunicorn).
timeout = 120
graceful_timeout = 30
keepalive = 30
