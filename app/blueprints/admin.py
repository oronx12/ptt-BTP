# app/blueprints/admin.py
"""
Panel d'administration — accessible uniquement au rôle 'admin' (toi).
Permet de :
  - Lister / créer / désactiver des clients
  - Créer des comptes utilisateurs et les associer à un client
  - Uploader le fichier Excel modèle d'un client (stockage local pour l'instant)
"""
from functools import wraps
from pathlib import Path

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_required, current_user

from .. import db
from ..models import Client, User, Projet, MembreProjet
from ..services.r2_service import upload_excel as r2_upload_excel

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _get_available_excels(base_dir: Path) -> list:
    """Liste tous les .xlsx disponibles pour test admin (data/, data/clients/, data/modeles_recepta/)."""
    result = []
    for subdir in ["data", "data/clients", "data/modeles_recepta"]:
        d = base_dir / subdir
        if d.exists():
            for f in sorted(d.glob("*.xlsx")):
                if not f.name.startswith("~$"):
                    rel = str(f.relative_to(base_dir)).replace("\\", "/")
                    result.append({"rel": rel, "name": f.name, "dir": subdir})
    return result

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


def pro_required(f):
    """Décorateur : réservé aux utilisateurs avec profil='pro' (et aux admins)."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.is_admin:
            return f(*args, **kwargs)
        if current_user.profil != "pro":
            flash("Cette fonctionnalité nécessite un profil PRO.", "warning")
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
    projets = Projet.query.order_by(Projet.created_at.desc()).all()
    base_dir = Path(current_app.root_path).parent
    available_excels = _get_available_excels(base_dir)
    current_test = session.get("admin_test_excel", "")
    current_test_name = Path(current_test).name if current_test else ""
    model_fallback_name = current_app.config["MODEL_EXCEL"].name
    return render_template(
        "admin/dashboard.html",
        clients=clients, users=users, projets=projets,
        available_excels=available_excels,
        current_test_excel=current_test,
        current_test_excel_name=current_test_name,
        model_fallback_name=model_fallback_name,
    )


@admin_bp.route("/set-test-excel", methods=["POST"])
@admin_required
def set_test_excel():
    """Sélectionne un fichier Excel local pour tester la réception en tant qu'admin."""
    base_dir = Path(current_app.root_path).parent
    rel_path = request.form.get("excel_path", "").strip()

    if rel_path:
        candidate = (base_dir / rel_path).resolve()
        # Sécurité : s'assurer que le fichier est bien dans base_dir
        if not str(candidate).startswith(str(base_dir.resolve())):
            flash("Chemin non autorisé.", "danger")
            return redirect(url_for("admin.dashboard"))
        if candidate.suffix not in (".xlsx", ".xls") or not candidate.exists():
            flash("Fichier introuvable.", "danger")
            return redirect(url_for("admin.dashboard"))
        session["admin_test_excel"] = str(candidate)
        flash(f"Fichier de test actif : {candidate.name}", "success")
    else:
        session.pop("admin_test_excel", None)
        flash("Fichier de test réinitialisé (fallback par défaut).", "info")

    return redirect(url_for("admin.dashboard"))


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


@admin_bp.route("/clients/<int:client_id>/toggle-plan", methods=["POST"])
@admin_required
def toggle_plan(client_id):
    """Bascule le plan d'un client entre 'solo' et 'pro'."""
    client = db.get_or_404(Client, client_id)
    client.plan = "pro" if client.plan == "solo" else "solo"
    db.session.commit()
    flash(f"Client « {client.nom} » basculé en plan {client.plan.upper()}.", "success")
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
        profil    = request.form.get("profil", "solo")
        client_id = request.form.get("client_id") or None

        if not email or not nom or not password:
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template("admin/user_form.html", clients=clients)

        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return render_template("admin/user_form.html", clients=clients)

        user = User(
            email=email, nom=nom, role=role, profil=profil,
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
        profil      = request.form.get("profil", "solo")
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
        user.profil    = profil
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


@admin_bp.route("/utilisateurs/<int:user_id>/toggle-profil", methods=["POST"])
@admin_required
def toggle_profil(user_id):
    user = db.get_or_404(User, user_id)
    user.profil = "pro" if user.profil == "solo" else "solo"
    db.session.commit()
    flash(f"Profil de « {user.nom} » basculé en {user.profil.upper()}.", "success")
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


# ── Gestion projets V2 PRO ───────────────────────────────────────────────────

@admin_bp.route("/projets/")
@admin_required
def liste_projets():
    client_id = request.args.get("client_id", type=int)
    if client_id:
        client  = db.get_or_404(Client, client_id)
        projets = Projet.query.filter_by(client_id=client_id).order_by(Projet.created_at.desc()).all()
    else:
        client  = None
        projets = Projet.query.order_by(Projet.created_at.desc()).all()
    return render_template("admin/projets_liste.html", projets=projets, client=client)


@admin_bp.route("/projets/nouveau", methods=["GET", "POST"])
@admin_required
def nouveau_projet():
    clients_pro = Client.query.filter_by(plan="pro", actif=True).order_by(Client.nom).all()
    if request.method == "POST":
        client_id     = request.form.get("client_id", type=int)
        nom           = request.form.get("nom", "").strip()
        description   = request.form.get("description", "").strip()
        pk_debut      = request.form.get("pk_debut", "").strip()
        pk_fin        = request.form.get("pk_fin", "").strip()
        tolerance_str = request.form.get("tolerance_defaut", "").strip()

        if not nom or not client_id:
            flash("Le nom et le client sont obligatoires.", "danger")
            return render_template("admin/projet_form.html", clients_pro=clients_pro)

        projet = Projet(
            client_id=client_id,
            nom=nom,
            description=description or None,
            pk_debut=pk_debut or None,
            pk_fin=pk_fin or None,
            tolerance_defaut=float(tolerance_str) if tolerance_str else None,
        )
        db.session.add(projet)
        db.session.commit()
        flash(f"Projet « {nom} » créé.", "success")
        return redirect(url_for("admin.detail_projet", projet_id=projet.id))

    preselect = request.args.get("client_id", type=int)
    return render_template("admin/projet_form.html", clients_pro=clients_pro, preselect=preselect)


@admin_bp.route("/projets/<int:projet_id>")
@admin_required
def detail_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    # Candidats : users PRO du même client (seuls les PRO peuvent rejoindre un projet PRO)
    users_client = (User.query
                    .filter_by(client_id=projet.client_id, actif=True, role="client", profil="pro")
                    .order_by(User.nom).all()) if projet.plan == "pro" else []
    membres      = list(projet.membres)
    membres_ids  = {m.user_id for m in membres}
    nb_mdc       = sum(1 for m in membres if m.role == "mdc")
    nb_entreprise = sum(1 for m in membres if m.role == "entreprise")
    return render_template("admin/projet_detail.html",
                           projet=projet,
                           users_client=users_client,
                           membres_ids=membres_ids,
                           nb_mdc=nb_mdc,
                           nb_entreprise=nb_entreprise,
                           MAX_MEMBRES=5)


@admin_bp.route("/projets/<int:projet_id>/toggle", methods=["POST"])
@admin_required
def toggle_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    projet.actif = not projet.actif
    db.session.commit()
    etat = "activé" if projet.actif else "désactivé"
    flash(f"Projet « {projet.nom} » {etat}.", "info")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/toggle-plan", methods=["POST"])
@admin_required
def toggle_plan_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    if projet.plan == "pro" and projet.membres.count() > 0:
        flash("Impossible de repasser en SOLO : retirez d'abord les membres du projet.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))
    projet.plan = "pro" if projet.plan == "solo" else "solo"
    db.session.commit()
    flash(f"Projet « {projet.nom} » basculé en {projet.plan.upper()}.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/membres/ajouter", methods=["POST"])
@admin_required
def ajouter_membre(projet_id):
    projet  = db.get_or_404(Projet, projet_id)
    user_id = request.form.get("user_id", type=int)
    role    = request.form.get("role", "")
    email_notif   = request.form.get("email_notif", "").strip()
    nom_affichage = request.form.get("nom_affichage", "").strip()

    if not user_id or role not in ("mdc", "entreprise"):
        flash("Utilisateur et rôle (mdc / entreprise) obligatoires.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    user = db.get_or_404(User, user_id)

    if user.profil != "pro":
        flash("Seuls les utilisateurs au profil PRO peuvent rejoindre un projet PRO.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    nb_role = MembreProjet.query.filter_by(projet_id=projet_id, role=role).count()
    if nb_role >= 5:
        flash(f"Limite atteinte : maximum 5 membres {role.upper()} par projet.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    if MembreProjet.query.filter_by(projet_id=projet_id, user_id=user_id).first():
        flash("Cet utilisateur est déjà membre du projet.", "warning")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))
    membre = MembreProjet(
        projet_id=projet_id,
        user_id=user_id,
        role=role,
        email_notif=email_notif or user.email,
        nom_affichage=nom_affichage or user.nom,
    )
    db.session.add(membre)
    db.session.commit()
    flash(f"« {user.nom} » ajouté en tant que {role}.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/membres/<int:membre_id>/supprimer", methods=["POST"])
@admin_required
def supprimer_membre(projet_id, membre_id):
    membre = db.get_or_404(MembreProjet, membre_id)
    nom = membre.user.nom
    db.session.delete(membre)
    db.session.commit()
    flash(f"Membre « {nom} » retiré du projet.", "info")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))
