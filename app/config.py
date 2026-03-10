# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Charge automatiquement le fichier .env à la racine du projet
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "changez-moi-en-production")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # PostgreSQL Supabase
    # Render fournit parfois "postgres://" (ancien format) — SQLAlchemy 2.x exige "postgresql://"
    _db_url = os.environ.get("DATABASE_URL", "")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url or None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Pool stable pour Supabase Session Pooler
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Cloudflare R2 (variables lues directement depuis os.environ dans r2_service.py)
    R2_ENDPOINT         = os.environ.get("R2_ENDPOINT", "")
    R2_BUCKET           = os.environ.get("R2_BUCKET", "ptt-btp-models")
    R2_ACCESS_KEY_ID    = os.environ.get("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")

    # Fichiers locaux (fallback si R2 indisponible)
    MODEL_EXCEL      = BASE_DIR / "data" / "Projet_Routier_Topographie.xlsx"
    TEMP_DIR         = BASE_DIR / "data" / "tmp"
    CLIENTS_DATA_DIR = BASE_DIR / "data" / "clients"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG      = False
    SECRET_KEY = os.environ.get("SECRET_KEY")  # obligatoire en prod


class TestingConfig(Config):
    DEBUG    = True
    TESTING  = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


_configs = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(env: str = None):
    """Retourne la classe de configuration selon l'environnement."""
    env = env or os.environ.get("FLASK_ENV", "development")
    return _configs.get(env, DevelopmentConfig)
