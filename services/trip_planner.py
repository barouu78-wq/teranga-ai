import json
from html import escape
from flask import Response, jsonify, request
from datetime import date

from services.http_security import origin_allowed

ALLOWED_LANGS = {"fr", "en", "wo", "ff"}