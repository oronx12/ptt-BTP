"""
scripts/migrate_v5.py — Migration V5 : avatar utilisateur.

Changements :
  - Ajout colonne photo_url sur users (URL ou clé R2 de l'avatar, nullable)

Idempotent : peut être relancé sans risque.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from sqlalchemy import text

MIGRATIONS = [
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500);
    """,
]


def run():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        try:
            for i, sql in enumerate(MIGRATIONS, 1):
                label = sql.strip().splitlines()[0].strip()[:70]
                print(f"[{i}/{len(MIGRATIONS)}] {label}...")
                conn.execute(text(sql))
            conn.commit()
            print("\nOK Migration V5 terminee avec succes.")
        except Exception as e:
            conn.rollback()
            print(f"\nERREUR : {e}")
            sys.exit(1)
        finally:
            conn.close()


if __name__ == "__main__":
    run()
