"""
scripts/migrate_v4.py — Migration V4 : verdict de réception.

Changements :
  - Ajout colonne statut_reception sur demandes_reception
    (validee | non_validee | a_reprendre | NULL)

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
    ALTER TABLE demandes_reception
    ADD COLUMN IF NOT EXISTS statut_reception VARCHAR(20);
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
            print("\nOK Migration V4 terminee avec succes.")
        except Exception as e:
            conn.rollback()
            print(f"\nERREUR : {e}")
            sys.exit(1)
        finally:
            conn.close()


if __name__ == "__main__":
    run()
