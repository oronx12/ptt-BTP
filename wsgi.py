# wsgi.py — Point d'entrée production
# Usage Gunicorn  : gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
# Usage Waitress  : waitress-serve --port=5000 wsgi:app
import os
from app import create_app

app = create_app(env="production")
