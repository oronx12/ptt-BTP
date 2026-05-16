# app/models.py
"""
Modèles de base de données SQLAlchemy — V3.

Architecture :
  Client      → une entreprise (MDC ou ET selon le projet)
  User        → un acteur affilié à 1..N clients via UserClient
  Projet      → un fichier Excel + plan solo|pro
  UserClient  → many-to-many User ↔ Client
  ClientProjet → Client ↔ Projet avec rôle mdc|entreprise
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


# ── Clients (entreprises) ──────────────────────────────────────────────────────

class Client(db.Model):
    """Entreprise cliente : MDC ou ET selon le projet auquel elle est associée."""
    __tablename__ = "clients"

    id           = db.Column(db.Integer, primary_key=True)
    nom          = db.Column(db.String(120), nullable=False)
    projet_label = db.Column(db.String(200), nullable=True)
    excel_key    = db.Column(db.String(255), nullable=True)  # legacy V1
    plan         = db.Column(db.String(20), nullable=False, default="solo", server_default="solo")  # solo | pro
    actif        = db.Column(db.Boolean, default=True, nullable=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relations
    user_links   = db.relationship("UserClient",   back_populates="client",
                                   cascade="all, delete-orphan", lazy="dynamic")
    projet_links = db.relationship("ClientProjet", back_populates="client",
                                   cascade="all, delete-orphan", lazy="dynamic")

    @property
    def users(self):
        """Liste des utilisateurs affiliés à ce client."""
        return [uc.user for uc in self.user_links.all()]

    @property
    def projet(self):
        """Le projet associé à ce client (1-to-1 via Projet.client_id)."""
        return Projet.query.filter_by(client_id=self.id).first()

    @property
    def operateurs_mdc(self):
        return [uc for uc in self.user_links.all() if uc.role == "mdc"]

    @property
    def operateurs_et(self):
        return [uc for uc in self.user_links.all() if uc.role == "entreprise"]

    def __repr__(self):
        return f"<Client {self.id} — {self.nom} [{self.plan}]>"


# ── Utilisateurs (acteurs) ────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    """Acteur physique — affilié à 1..N clients via UserClient."""
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nom           = db.Column(db.String(120), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="client")  # admin | client
    actif         = db.Column(db.Boolean, default=True, nullable=False)
    photo_url     = db.Column(db.String(500), nullable=True)   # URL ou clé R2 de l'avatar
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login    = db.Column(db.DateTime, nullable=True)

    # Relations
    client_links = db.relationship("UserClient", back_populates="user",
                                   cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def clients(self):
        """Liste des clients (entreprises) auxquels cet acteur est affilié."""
        return [uc.client for uc in self.client_links.all()]

    @property
    def excel_key(self):
        """Rétrocompat V1 : Excel du premier client associé."""
        uc = self.client_links.first()
        return uc.client.excel_key if uc else None

    def __repr__(self):
        return f"<User {self.id} — {self.email} ({self.role})>"


# ── Association User ↔ Client ─────────────────────────────────────────────────

class UserClient(db.Model):
    """Affiliation d'un acteur à un client avec son rôle sur le projet."""
    __tablename__ = "user_clients"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
    client_id  = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    # mdc = opérateur de contrôle | entreprise = opérateur de travaux (PRO uniquement)
    role       = db.Column(db.String(20), nullable=False, default="mdc", server_default="mdc")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user   = db.relationship("User",   back_populates="client_links")
    client = db.relationship("Client", back_populates="user_links")

    __table_args__ = (
        db.UniqueConstraint("user_id", "client_id", name="uq_user_client"),
    )

    def __repr__(self):
        return f"<UserClient user={self.user_id} client={self.client_id} role={self.role}>"


# ── Fiches de réception (V1 legacy) ──────────────────────────────────────────

class FicheReception(db.Model):
    """Archive d'une fiche générée — stockée sur R2."""
    __tablename__ = "fiches_reception"

    id              = db.Column(db.Integer, primary_key=True)
    client_id       = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"),   nullable=True)
    r2_key          = db.Column(db.String(300), nullable=False)
    projet          = db.Column(db.String(255), nullable=True)
    section         = db.Column(db.String(255), nullable=True)
    date_reception  = db.Column(db.String(50),  nullable=True)
    operateur       = db.Column(db.String(120), nullable=True)
    statut_verdict  = db.Column(db.String(20),  nullable=True)  # validee | non_validee | a_reprendre
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    client = db.relationship("Client", backref=db.backref("fiches", lazy="dynamic"))
    user   = db.relationship("User",   backref=db.backref("fiches", lazy="dynamic"))

    def __repr__(self):
        return f"<FicheReception {self.id} — {self.projet}>"


# ── Projets V2 ────────────────────────────────────────────────────────────────

class Projet(db.Model):
    """
    Projet de réception = un fichier Excel + plan solo|pro.
    SOLO : 1 client MDC uniquement.
    PRO  : 1 client MDC + 1 client ET.
    """
    __tablename__ = "projets"

    id               = db.Column(db.Integer, primary_key=True)
    nom              = db.Column(db.String(200), nullable=False)
    intitule         = db.Column(db.String(500), nullable=True)   # titre officiel complet
    description      = db.Column(db.Text, nullable=True)
    excel_key        = db.Column(db.String(255), nullable=True)
    pk_debut         = db.Column(db.String(50), nullable=True)
    pk_fin           = db.Column(db.String(50), nullable=True)
    tolerance_defaut = db.Column(db.Float, nullable=True)
    plan             = db.Column(db.String(20), nullable=False, default="solo")  # solo | pro
    actif            = db.Column(db.Boolean, default=True, nullable=False)
    coordonnees_gps  = db.Column(db.JSON, nullable=True)
    logo_mdc_url     = db.Column(db.String(500), nullable=True)   # URL R2 logo MDC
    logo_et_url      = db.Column(db.String(500), nullable=True)   # URL R2 logo ET
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Rétrocompat V1 : client_id gardé nullable pour les anciens projets
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)

    # Relations
    client_links = db.relationship("ClientProjet", back_populates="projet",
                                   cascade="all, delete-orphan", lazy="dynamic")
    membres      = db.relationship("MembreProjet", back_populates="projet",
                                   cascade="all, delete-orphan", lazy="dynamic")
    portions     = db.relationship("Portion", back_populates="projet", lazy="dynamic",
                                   cascade="all, delete-orphan")

    @property
    def mdc(self):
        """Retourne le ClientProjet MDC, ou None."""
        return self.client_links.filter_by(role="mdc").first()

    @property
    def et(self):
        """Retourne le ClientProjet ET, ou None."""
        return self.client_links.filter_by(role="entreprise").first()

    @property
    def mode_label(self):
        return "PARTENARIAT" if self.plan == "pro" else "AUTONOME"

    @property
    def membres_controleurs(self):
        return self.membres.filter_by(role="controleur").all()

    @property
    def membres_travaux(self):
        return self.membres.filter_by(role="travaux").all()

    def __repr__(self):
        return f"<Projet {self.id} — {self.nom} [{self.plan}]>"


# ── Association Client ↔ Projet ───────────────────────────────────────────────

class ClientProjet(db.Model):
    """Association d'un client à un projet avec son rôle (mdc | entreprise)."""
    __tablename__ = "clients_projets"

    id         = db.Column(db.Integer, primary_key=True)
    client_id  = db.Column(db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    projet_id  = db.Column(db.Integer, db.ForeignKey("projets.id", ondelete="CASCADE"), nullable=False)
    role       = db.Column(db.String(20), nullable=False)  # "mdc" | "entreprise"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    client = db.relationship("Client", back_populates="projet_links")
    projet = db.relationship("Projet", back_populates="client_links")

    __table_args__ = (
        db.UniqueConstraint("client_id", "projet_id", name="uq_client_projet"),
    )

    def __repr__(self):
        return f"<ClientProjet client={self.client_id} projet={self.projet_id} role={self.role}>"


# ── Membres de projet (V3 direct) ────────────────────────────────────────────

class MembreProjet(db.Model):
    """
    Affectation directe d'un opérateur à un projet.
    Remplace la chaîne User → UserClient → Client → ClientProjet → Projet.
    Role : 'controleur' (MDC) | 'travaux' (ET) | 'observateur'
    entreprise_id : optionnel — pour afficher le logo/nom de l'entreprise représentée.
    """
    __tablename__ = "membres_projets"

    id            = db.Column(db.Integer, primary_key=True)
    projet_id     = db.Column(db.Integer, db.ForeignKey("projets.id",  ondelete="CASCADE"), nullable=False)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="controleur")
    entreprise_id = db.Column(db.Integer, db.ForeignKey("clients.id",  ondelete="SET NULL"), nullable=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projet     = db.relationship("Projet",  back_populates="membres")
    user       = db.relationship("User",    backref=db.backref("projet_memberships", lazy="dynamic"))
    entreprise = db.relationship("Client",  backref=db.backref("membres_projets",    lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("projet_id", "user_id", name="uq_membre_projet"),
    )

    @property
    def role_label(self):
        return {"controleur": "Bureau de Contrôle", "travaux": "Entreprise de Travaux",
                "observateur": "Observateur"}.get(self.role, self.role)

    def __repr__(self):
        return f"<MembreProjet projet={self.projet_id} user={self.user_id} role={self.role}>"


# ── Portions ──────────────────────────────────────────────────────────────────

class Portion(db.Model):
    __tablename__ = "portions"

    id                  = db.Column(db.Integer, primary_key=True)
    projet_id           = db.Column(db.Integer, db.ForeignKey("projets.id"), nullable=False)
    nom                 = db.Column(db.String(200), nullable=False)
    pk_debut            = db.Column(db.String(50), nullable=True)
    pk_fin              = db.Column(db.String(50), nullable=True)
    excel_key           = db.Column(db.String(255), nullable=True)
    membres_specifiques = db.Column(db.Boolean, default=False, nullable=False)
    coordonnees_gps     = db.Column(db.JSON, nullable=True)
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projet = db.relationship("Projet", back_populates="portions")

    def __repr__(self):
        return f"<Portion {self.id} — {self.nom}>"


# ── Demandes de réception V2 ──────────────────────────────────────────────────

class DemandeReception(db.Model):
    """Demande formelle ET → MDC. Workflow : en_attente → accusee → acceptee/refusee → cloturee"""
    __tablename__ = "demandes_reception"

    STATUTS = ("en_attente", "accusee", "acceptee", "refusee", "cloturee")

    id              = db.Column(db.Integer, primary_key=True)
    numero          = db.Column(db.String(20), unique=True, nullable=False)
    projet_id       = db.Column(db.Integer, db.ForeignKey("projets.id"), nullable=False)
    demandeur_id    = db.Column(db.Integer, db.ForeignKey("users.id"),   nullable=False)
    pk_debut        = db.Column(db.String(50), nullable=False)
    pk_fin          = db.Column(db.String(50), nullable=False)
    pks_list        = db.Column(db.JSON, nullable=True)   # liste ordonnée des PK sélectionnés
    parties         = db.Column(db.JSON, nullable=True)
    mode            = db.Column(db.String(20), nullable=True, default="assainissement")
    tolerance       = db.Column(db.Float, nullable=True, default=2.0)
    meteo           = db.Column(db.String(200), nullable=True)
    date_souhaitee  = db.Column(db.Date, nullable=True)
    heure_souhaitee = db.Column(db.String(10), nullable=True)
    observations    = db.Column(db.Text, nullable=True)
    statut           = db.Column(db.String(20), nullable=False, default="en_attente")
    statut_reception = db.Column(db.String(20), nullable=True)   # validee | non_validee | a_reprendre
    motif_refus      = db.Column(db.Text, nullable=True)
    accuse_at        = db.Column(db.DateTime, nullable=True)
    accepte_at       = db.Column(db.DateTime, nullable=True)
    cloture_at       = db.Column(db.DateTime, nullable=True)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    fiche_id         = db.Column(db.Integer, db.ForeignKey("fiches_reception.id"), nullable=True)

    projet    = db.relationship("Projet",         backref=db.backref("demandes", lazy="dynamic"))
    demandeur = db.relationship("User",            backref=db.backref("demandes_soumises", lazy="dynamic"))
    fiche     = db.relationship("FicheReception",  backref=db.backref("demande", uselist=False))

    @classmethod
    def generate_numero(cls) -> str:
        year   = datetime.now(timezone.utc).year
        prefix = f"DR-{year}-"
        last   = (cls.query.filter(cls.numero.like(f"{prefix}%"))
                  .order_by(cls.numero.desc()).first())
        n = int(last.numero.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{n:03d}"

    @property
    def statut_label(self) -> str:
        labels = {
            "en_attente": "En attente", "accusee": "Accusé de réception",
            "acceptee": "Acceptée", "refusee": "Refusée", "cloturee": "Clôturée",
        }
        return labels.get(self.statut, self.statut)

    @property
    def statut_reception_label(self) -> str:
        labels = {
            "validee":     "Validée",
            "non_validee": "Non validée",
            "a_reprendre": "À reprendre",
        }
        return labels.get(self.statut_reception, "—") if self.statut_reception else "—"

    def __repr__(self):
        return f"<DemandeReception {self.numero} [{self.statut}]>"
