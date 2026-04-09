"""
scripts/migrate_v2.py — Migration base de données vers V2.

Exécute les ALTER TABLE et CREATE TABLE nécessaires sans toucher aux données V1.
Idempotent : peut être relancé sans risque (IF NOT EXISTS / IF column does not exist).

Usage :
    python scripts/migrate_v2.py
"""
import os
import sys

# Assure que le répertoire racine est dans le path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from sqlalchemy import text

MIGRATIONS = [
    # ── 1. Colonne plan sur la table clients existante ──────────────────────
    """
    ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'solo';
    """,

    # ── 2. Table projets (V2) ────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS projets (
        id               SERIAL PRIMARY KEY,
        client_id        INTEGER NOT NULL REFERENCES clients(id),
        nom              VARCHAR(200) NOT NULL,
        description      TEXT,
        excel_key        VARCHAR(255),
        pk_debut         VARCHAR(50),
        pk_fin           VARCHAR(50),
        tolerance_defaut FLOAT,
        actif            BOOLEAN NOT NULL DEFAULT TRUE,
        created_at       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );
    """,

    # ── 3. Table portions (V2) ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS portions (
        id                   SERIAL PRIMARY KEY,
        projet_id            INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
        nom                  VARCHAR(200) NOT NULL,
        pk_debut             VARCHAR(50),
        pk_fin               VARCHAR(50),
        excel_key            VARCHAR(255),
        membres_specifiques  BOOLEAN NOT NULL DEFAULT FALSE,
        coordonnees_gps      JSONB,
        created_at           TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );
    """,

    # ── 4. Table membres_projet (V2) ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS membres_projet (
        id             SERIAL PRIMARY KEY,
        projet_id      INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
        user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role           VARCHAR(20) NOT NULL,
        email_notif    VARCHAR(150),
        nom_affichage  VARCHAR(200),
        actif          BOOLEAN NOT NULL DEFAULT TRUE,
        created_at     TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        CONSTRAINT uq_membre_projet_user UNIQUE (projet_id, user_id)
    );
    """,

    # ── 5. Profil utilisateur (solo | pro) ───────────────────────────────────
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS profil VARCHAR(20) NOT NULL DEFAULT 'solo';
    """,

    # ── 6. Plan du projet (solo | pro) ───────────────────────────────────────
    """
    ALTER TABLE projets
    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'solo';
    """,
]


def run():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        try:
            for i, sql in enumerate(MIGRATIONS, 1):
                print(f"[{i}/{len(MIGRATIONS)}] {sql.strip().splitlines()[0].strip()[:60]}...")
                conn.execute(text(sql))
            conn.commit()
            print("\nOK Migration terminee avec succes.")
        except Exception as e:
            conn.rollback()
            print(f"\nERREUR : {e}")
            sys.exit(1)
        finally:
            conn.close()


if __name__ == "__main__":
    run()
