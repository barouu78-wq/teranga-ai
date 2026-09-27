"""Gunicorn entrypoint for the Flask application.

Routing is registered directly on the Flask app in app.py so Render/Gunicorn
uses the same route table as local development.
"""
from flask import Response

from app import app

INDEXNOW_KEY = "8078ffb659c643b58bddddca48be0627"


@app.route(f"/{INDEXNOW_KEY}.txt")
def indexnow_key():
    return Response(INDEXNOW_KEY, mimetype="text/plain")
