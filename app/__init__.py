# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from .config import get_config

# Extensions instanciées globalement, initialisées dans create_app()
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(env: str = None) -> Flask:
    """Application Factory."""
    app = Flask(__name__)
    app.config.from_object(get_config(env))

    # Initialisation des extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Connectez-vous pour accéder à cette page."
    login_manager.login_message_category = "warning"

    # Chargement utilisateur pour Flask-Login
    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Création des tables au premier lancement
    # Enveloppé dans try/except : un timeout réseau Supabase ne doit pas crasher le démarrage
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "db.create_all() échoué au démarrage (BDD inaccessible ?) : %s", e
            )

    # Blueprints
    from .blueprints.pages import pages_bp
    from .blueprints.api   import api_bp
    from .blueprints.auth  import auth_bp
    from .blueprints.admin import admin_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app
