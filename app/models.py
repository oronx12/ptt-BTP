# app/models.py
"""
Modèles de base de données SQLAlchemy.

Structure :
  Client  → une entreprise cliente (ex: "BTP Rhône-Alpes")
  User    → un utilisateur qui appartient à un Client
            (plusieurs techniciens peuvent partager le même compte client)

Le fichier Excel modèle est stocké sur S3/R2 (Bloc 2).
On ne stocke ici que le nom du fichier (clé S3).
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class Client(db.Model):
    """
    Représente une entreprise / projet client.
    Chaque client a son propre fichier Excel modèle.
    """
    __tablename__ = "clients"

    id            = db.Column(db.Integer, primary_key=True)
    nom           = db.Column(db.String(120), nullable=False)
    # Clé du fichier Excel dans le bucket S3/R2 (ex: "clients/42/modele.xlsx")
    excel_key     = db.Column(db.String(255), nullable=True)
    # Nom affiché du projet dans l'app
    projet_label  = db.Column(db.String(200), nullable=True)
    actif         = db.Column(db.Boolean, default=True, nullable=False)
    # Déprécié — le plan est désormais porté par chaque Projet, pas par le Client
    plan          = db.Column(db.String(20), nullable=False, default="solo")
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    users = db.relationship("User", back_populates="client", lazy="dynamic")

    def __repr__(self):
        return f"<Client {self.id} — {self.nom}>"


class User(UserMixin, db.Model):
    """
    Utilisateur de l'application.
    Appartient à un Client.
    Rôles : 'admin' (toi) ou 'client' (technicien BTP).
    """
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nom           = db.Column(db.String(120), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="client")
    # Profil fonctionnel : "solo" (V1 uniquement) | "pro" (accès projets collaboratifs V2)
    profil        = db.Column(db.String(20), nullable=False, default="solo")
    # NULL si role == 'admin' (admin n'appartient à aucun client)
    client_id     = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)
    actif         = db.Column(db.Boolean, default=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login    = db.Column(db.DateTime, nullable=True)

    client = db.relationship("Client", back_populates="users")

    # --- Sécurité mot de passe ---
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # --- Propriétés utiles ---
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def excel_key(self):
        """Raccourci : clé Excel du client associé."""
        return self.client.excel_key if self.client else None

    def __repr__(self):
        return f"<User {self.id} — {self.email} ({self.role})>"


class FicheReception(db.Model):
    """
    Archive d'une fiche de réception topographique générée.
    Le fichier HTML est stocké sur R2 ; on garde ici les métadonnées.
    """
    __tablename__ = "fiches_reception"

    id             = db.Column(db.Integer, primary_key=True)
    client_id      = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    r2_key         = db.Column(db.String(300), nullable=False)
    projet         = db.Column(db.String(255), nullable=True)
    section        = db.Column(db.String(255), nullable=True)
    date_reception = db.Column(db.String(50),  nullable=True)
    operateur      = db.Column(db.String(120), nullable=True)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    client = db.relationship("Client", backref=db.backref("fiches", lazy="dynamic"))
    user   = db.relationship("User",   backref=db.backref("fiches", lazy="dynamic"))

    def __repr__(self):
        return f"<FicheReception {self.id} — {self.projet}>"


# ── Modèles V2 PRO ────────────────────────────────────────────────────────────

class Projet(db.Model):
    """
    Projet collaboratif V2 — appartient à un Client PRO.
    Regroupe des Portions et des MembreProjet (MDC + Entreprise).
    """
    __tablename__ = "projets"

    id               = db.Column(db.Integer, primary_key=True)
    client_id        = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    nom              = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text, nullable=True)
    # Clé R2 des cotes théoriques au niveau projet (peut être overridé par portion)
    excel_key        = db.Column(db.String(255), nullable=True)
    pk_debut         = db.Column(db.String(50), nullable=True)
    pk_fin           = db.Column(db.String(50), nullable=True)
    tolerance_defaut = db.Column(db.Float, nullable=True)   # en cm
    # Plan du projet : "solo" (flux V1 classique) | "pro" (workflow collaboratif MDC/Entreprise)
    plan             = db.Column(db.String(20), nullable=False, default="solo")
    actif            = db.Column(db.Boolean, default=True, nullable=False)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    client   = db.relationship("Client", backref=db.backref("projets", lazy="dynamic"))
    portions = db.relationship("Portion", back_populates="projet", lazy="dynamic",
                               cascade="all, delete-orphan")
    membres  = db.relationship("MembreProjet", back_populates="projet", lazy="dynamic",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Projet {self.id} — {self.nom}>"


class Portion(db.Model):
    """
    Tronçon d'un Projet (ex: "Tronçon Nord", "Échangeur Est").
    Chaque DemandeReception sera liée à une Portion, pas directement au Projet.
    """
    __tablename__ = "portions"

    id                  = db.Column(db.Integer, primary_key=True)
    projet_id           = db.Column(db.Integer, db.ForeignKey("projets.id"), nullable=False)
    nom                 = db.Column(db.String(200), nullable=False)
    pk_debut            = db.Column(db.String(50), nullable=True)
    pk_fin              = db.Column(db.String(50), nullable=True)
    # Clé R2 propre à cette portion (override excel_key du Projet parent si renseigné)
    excel_key           = db.Column(db.String(255), nullable=True)
    # Si True, cette portion a ses propres membres (override les membres du Projet)
    membres_specifiques = db.Column(db.Boolean, default=False, nullable=False)
    # Tracé GPS optionnel — format { "type": "linestring", "points": [{pk, lat, lng}] }
    coordonnees_gps     = db.Column(db.JSON, nullable=True)
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projet = db.relationship("Projet", back_populates="portions")

    def __repr__(self):
        return f"<Portion {self.id} — {self.nom} ({self.pk_debut} → {self.pk_fin})>"


class MembreProjet(db.Model):
    """
    Association User ↔ Projet avec rôle métier (mdc | entreprise).
    L'email_notif peut différer de user.email (ex: boîte partagée d'équipe).
    """
    __tablename__ = "membres_projet"

    id            = db.Column(db.Integer, primary_key=True)
    projet_id     = db.Column(db.Integer, db.ForeignKey("projets.id"), nullable=False)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role          = db.Column(db.String(20), nullable=False)   # "mdc" | "entreprise"
    email_notif   = db.Column(db.String(150), nullable=True)   # email de notification dédié
    nom_affichage = db.Column(db.String(200), nullable=True)   # ex: "Bureau de contrôle CEREMA"
    actif         = db.Column(db.Boolean, default=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projet = db.relationship("Projet", back_populates="membres")
    user   = db.relationship("User", backref=db.backref("memberships", lazy="dynamic"))

    # Un utilisateur ne peut appartenir qu'une seule fois à un projet donné
    __table_args__ = (
        db.UniqueConstraint("projet_id", "user_id", name="uq_membre_projet_user"),
    )

    def __repr__(self):
        return f"<MembreProjet projet={self.projet_id} user={self.user_id} role={self.role}>"
