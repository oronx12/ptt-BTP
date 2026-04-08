# app/blueprints/admin.py
"""
Panel d'administration — accessible uniquement au rôle 'admin' (toi).
Permet de :
  - Lister / créer / désactiver des clients
  - Créer des comptes utilisateurs et les associer à un client
  - Uploader le fichier Excel modèle d'un client (stockage local pour l'instant)
"""
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from .. import db
from ..models import Client, User
from ..services.r2_service import upload_excel as r2_upload_excel

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_EXTENSIONS = {"xlsx", "xls"}


def admin_required(f):
    """Décorateur : réservé aux utilisateurs avec role='admin'."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Accès réservé à l'administrateur.", "danger")
            return redirect(url_for("pages.home"))
        return f(*args, **kwargs)
    return decorated


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Dashboard admin ─────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    clients = Client.query.order_by(Client.created_at.desc()).all()
    users   = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/dashboard.html", clients=clients, users=users)


# ── Gestion clients ──────────────────────────────────────────────────────────

@admin_bp.route("/clients/nouveau", methods=["GET", "POST"])
@admin_required
def nouveau_client():
    if request.method == "POST":
        nom    = request.form.get("nom", "").strip()
        label  = request.form.get("projet_label", "").strip()
        if not nom:
            flash("Le nom du client est obligatoire.", "danger")
            return render_template("admin/client_form.html")

        client = Client(nom=nom, projet_label=label)
        db.session.add(client)
        db.session.commit()
        flash(f"Client « {nom} » créé (ID {client.id}).", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/client_form.html")


@admin_bp.route("/clients/<int:client_id>/excel", methods=["POST"])
@admin_required
def upload_excel(client_id):
    """Upload du fichier Excel modèle pour un client donné."""
    client = db.get_or_404(Client, client_id)

    if "excel_file" not in request.files:
        flash("Aucun fichier sélectionné.", "danger")
        return redirect(url_for("admin.dashboard"))

    f = request.files["excel_file"]
    if not f.filename or not _allowed_file(f.filename):
        flash("Format non supporté. Utilisez un fichier .xlsx ou .xls.", "danger")
        return redirect(url_for("admin.dashboard"))

    r2_key = f"data/clients/{client_id}/modele.xlsx"
    try:
        r2_upload_excel(f.read(), r2_key)
    except Exception as e:
        flash(f"Erreur upload R2 : {e}", "danger")
        return redirect(url_for("admin.dashboard"))

    client.excel_key = r2_key
    db.session.commit()
    flash(f"Fichier Excel uploadé pour « {client.nom} » (R2).", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/modifier", methods=["GET", "POST"])
@admin_required
def modifier_client(client_id):
    client = db.get_or_404(Client, client_id)
    if request.method == "POST":
        nom   = request.form.get("nom", "").strip()
        label = request.form.get("projet_label", "").strip()
        if not nom:
            flash("Le nom du client est obligatoire.", "danger")
            return render_template("admin/client_form.html", client=client)
        client.nom          = nom
        client.projet_label = label
        db.session.commit()
        flash(f"Client « {nom} » mis à jour.", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/client_form.html", client=client)


@admin_bp.route("/clients/<int:client_id>/toggle", methods=["POST"])
@admin_required
def toggle_client(client_id):
    client = db.get_or_404(Client, client_id)
    client.actif = not client.actif
    db.session.commit()
    etat = "activé" if client.actif else "désactivé"
    flash(f"Client « {client.nom} » {etat}.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/supprimer", methods=["POST"])
@admin_required
def supprimer_client(client_id):
    client = db.get_or_404(Client, client_id)
    nb_users = client.users.count()
    if nb_users > 0:
        flash(
            f"Impossible de supprimer « {client.nom} » : "
            f"{nb_users} utilisateur(s) y sont rattachés. "
            f"Supprimez-les ou réaffectez-les d'abord.",
            "danger"
        )
        return redirect(url_for("admin.dashboard"))
    nom = client.nom
    db.session.delete(client)
    db.session.commit()
    flash(f"Client « {nom} » supprimé définitivement.", "info")
    return redirect(url_for("admin.dashboard"))


# ── Gestion utilisateurs ─────────────────────────────────────────────────────

@admin_bp.route("/utilisateurs/nouveau", methods=["GET", "POST"])
@admin_required
def nouvel_utilisateur():
    clients = Client.query.order_by(Client.nom).all()

    if request.method == "POST":
        email     = request.form.get("email", "").strip().lower()
        nom       = request.form.get("nom", "").strip()
        password  = request.form.get("password", "")
        role      = request.form.get("role", "client")
        client_id = request.form.get("client_id") or None

        if not email or not nom or not password:
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template("admin/user_form.html", clients=clients)

        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return render_template("admin/user_form.html", clients=clients)

        user = User(
            email=email, nom=nom, role=role,
            client_id=int(client_id) if client_id else None
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f"Utilisateur « {email} » créé.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/user_form.html", clients=clients)


@admin_bp.route("/utilisateurs/<int:user_id>/modifier", methods=["GET", "POST"])
@admin_required
def modifier_utilisateur(user_id):
    user    = db.get_or_404(User, user_id)
    clients = Client.query.order_by(Client.nom).all()

    if request.method == "POST":
        nom         = request.form.get("nom", "").strip()
        email       = request.form.get("email", "").strip().lower()
        role        = request.form.get("role", "client")
        client_id   = request.form.get("client_id") or None
        new_password = request.form.get("password", "").strip()

        if not nom or not email:
            flash("Nom et email sont obligatoires.", "danger")
            return render_template("admin/user_form.html", user=user, clients=clients)

        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash("Cet email est déjà utilisé par un autre utilisateur.", "danger")
            return render_template("admin/user_form.html", user=user, clients=clients)

        user.nom       = nom
        user.email     = email
        user.role      = role
        user.client_id = int(client_id) if client_id else None
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash(f"Utilisateur « {nom} » mis à jour.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/user_form.html", user=user, clients=clients)


@admin_bp.route("/utilisateurs/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_utilisateur(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas vous désactiver vous-même.", "danger")
        return redirect(url_for("admin.dashboard"))
    user.actif = not user.actif
    db.session.commit()
    etat = "activé" if user.actif else "désactivé"
    flash(f"Utilisateur « {user.nom} » {etat}.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/utilisateurs/<int:user_id>/supprimer", methods=["POST"])
@admin_required
def supprimer_utilisateur(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for("admin.dashboard"))
    nom = user.nom
    db.session.delete(user)
    db.session.commit()
    flash(f"Utilisateur « {nom} » supprimé définitivement.", "info")
    return redirect(url_for("admin.dashboard"))
