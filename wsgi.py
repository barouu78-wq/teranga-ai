"""Gunicorn entrypoint for the Flask application.

Routing is registered directly on the Flask app in app.py so Render/Gunicorn
uses the same route table as local development.
"""
from app import app

