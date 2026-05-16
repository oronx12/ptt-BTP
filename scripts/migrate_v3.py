"""
scripts/migrate_v3.py — Migration V3 : refonte modèle Client/User/Projet.

Changements :
  - Nouvelle table user_clients  (User ↔ Client many-to-many)
  - Nouvelle table clients_projets (Client ↔ Projet + rôle mdc/entreprise)
  - Suppression : User.profil, User.client_id, Client.plan, table membres_projet

Idempotent : peut être relancé sans risque.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from sqlalchemy import text

MIGRATIONS = [

    # 1. Table many-to-many Utilisateur ↔ Client
    """
    CREATE TABLE IF NOT EXISTS user_clients (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
        client_id  INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        CONSTRAINT uq_user_client UNIQUE (user_id, client_id)
    );
    """,

    # 2. Table Client ↔ Projet avec rôle (remplace membres_projet)
    """
    CREATE TABLE IF NOT EXISTS clients_projets (
        id         SERIAL PRIMARY KEY,
        client_id  INTEGER NOT NULL REFERENCES clients(id)  ON DELETE CASCADE,
        projet_id  INTEGER NOT NULL REFERENCES projets(id)  ON DELETE CASCADE,
        role       VARCHAR(20) NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        CONSTRAINT uq_client_projet UNIQUE (client_id, projet_id)
    );
    """,

    # 3. Migrer user.client_id existant → user_clients
    """
    INSERT INTO user_clients (user_id, client_id)
    SELECT id, client_id FROM users
    WHERE client_id IS NOT NULL
    ON CONFLICT DO NOTHING;
    """,

    # 4. Supprimer User.profil
    """
    ALTER TABLE users DROP COLUMN IF EXISTS profil;
    """,

    # 5. Supprimer User.client_id (après migration)
    """
    ALTER TABLE users DROP COLUMN IF EXISTS client_id;
    """,

    # 6. Supprimer Client.plan
    """
    ALTER TABLE clients DROP COLUMN IF EXISTS plan;
    """,

    # 7. Supprimer l'ancienne table membres_projet
    """
    DROP TABLE IF EXISTS membres_projet CASCADE;
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
            print("\nOK Migration V3 terminee avec succes.")
        except Exception as e:
            conn.rollback()
            print(f"\nERREUR : {e}")
            sys.exit(1)
        finally:
            conn.close()


if __name__ == "__main__":
    run()
