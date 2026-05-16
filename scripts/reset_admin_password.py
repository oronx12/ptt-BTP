"""
scripts/reset_admin_password.py — Reinitialise le mot de passe admin.

Usage :
    python scripts/reset_admin_password.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import User

NEW_PASSWORD = "Admin2026!"   # <-- change ici si tu veux un autre mot de passe

app = create_app()
with app.app_context():
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        print("Aucun admin trouve en base.")
        sys.exit(1)
    admin.set_password(NEW_PASSWORD)
    db.session.commit()
    print(f"Mot de passe reinitialise pour : {admin.email}")
    print(f"Nouveau mot de passe           : {NEW_PASSWORD}")
