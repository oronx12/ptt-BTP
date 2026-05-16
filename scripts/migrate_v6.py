"""
scripts/migrate_v6.py — Migration V6 : infos projet dans la fiche de réception.

Changements :
  - Projet : intitule VARCHAR(500)     — titre officiel complet du projet
  - Projet : logo_mdc_url VARCHAR(500) — URL R2 du logo MDC uploadé
  - Projet : logo_et_url VARCHAR(500)  — URL R2 du logo ET uploadé
  - FicheReception : statut_verdict VARCHAR(20) — verdict final (validee/non_validee/a_reprendre)

Idempotent : peut être relancé sans risque.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from sqlalchemy import text

MIGRATIONS = [
    "ALTER TABLE projets ADD COLUMN IF NOT EXISTS intitule VARCHAR(500);",
    "ALTER TABLE projets ADD COLUMN IF NOT EXISTS logo_mdc_url VARCHAR(500);",
    "ALTER TABLE projets ADD COLUMN IF NOT EXISTS logo_et_url VARCHAR(500);",
    "ALTER TABLE fiches_reception ADD COLUMN IF NOT EXISTS statut_verdict VARCHAR(20);",
]


def run():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        try:
            for i, sql in enumerate(MIGRATIONS, 1):
                label = sql.strip()[:70]
                print(f"[{i}/{len(MIGRATIONS)}] {label}...")
                conn.execute(text(sql))
            conn.commit()
            print("\nOK Migration V6 terminee avec succes.")
        except Exception as e:
            conn.rollback()
            print(f"\nERREUR : {e}")
            sys.exit(1)
        finally:
            conn.close()


if __name__ == "__main__":
    run()
