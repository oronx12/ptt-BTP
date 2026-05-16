# app/blueprints/admin.py
"""
Panel d'administration RECEPTA — réservé au rôle 'admin'.
V3 : Projet = unité centrale. Client ↔ Projet via ClientProjet. User ↔ Client via UserClient.
"""
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from .. import db
from ..models import Client, User, Projet, UserClient, ClientProjet, MembreProjet
from ..services.r2_service import upload_excel as r2_upload_excel, upload_image as r2_upload_image, generate_presigned_url

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_EXTENSIONS       = {"xlsx", "xls"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

IMAGE_CONTENT_TYPES = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "gif": "image/gif", "webp": "image/webp",
}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# ── Helpers auto-fill Excel ──────────────────────────────────────────────────

def _find_gen_tolerance(gen: dict):
    """Cherche une valeur de tolérance dans le dict GEN_ de l'Excel."""
    for k, v in gen.items():
        if "TOL" in str(k).upper() and isinstance(v, (int, float)):
            return float(v)
    return None


def _autofill_projet_from_excel(projet, r2_key: str) -> bool:
    """Auto-remplit les champs vides du projet depuis les données Excel. Retourne True si modifié."""
    from ..services.excel_service import parse_modele_config
    from ..services.r2_service import download_excel
    changed = False
    try:
        config = parse_modele_config(download_excel(r2_key))
    except Exception:
        return False

    gen      = config.get("gen", {})
    profil   = config.get("profil_long", [])

    if not projet.pk_debut and profil:
        projet.pk_debut = profil[0]["pk"]
        changed = True
    if not projet.pk_fin and profil:
        projet.pk_fin = profil[-1]["pk"]
        changed = True
    if not projet.tolerance_defaut:
        tol = _find_gen_tolerance(gen)
        if tol is not None:
            projet.tolerance_defaut = tol
            changed = True
    if not projet.intitule:
        titre = gen.get("GEN_TITRE") or gen.get("GEN_NOM") or gen.get("TITRE")
        if titre:
            projet.intitule = str(titre)[:500]
            changed = True
    return changed


# ── Décorateurs ───────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Accès réservé à l'administrateur.", "danger")
            return redirect(url_for("pages.home"))
        return f(*args, **kwargs)
    return decorated


def pro_required(f):
    """Accès réservé aux acteurs affiliés à au moins un projet (V2 UserClient ou V3 MembreProjet)."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.is_admin:
            return f(*args, **kwargs)
        has_access = (
            UserClient.query.filter_by(user_id=current_user.id).first()
            or MembreProjet.query.filter_by(user_id=current_user.id).first()
        )
        if not has_access:
            flash("Accès réservé aux acteurs affiliés à un projet.", "warning")
            return redirect(url_for("pages.home"))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    clients     = Client.query.order_by(Client.created_at.desc()).all()
    users       = User.query.filter_by(role="client").order_by(User.created_at.desc()).all()
    users_admin = User.query.filter_by(role="admin").order_by(User.created_at.desc()).all()
    projets     = Projet.query.order_by(Projet.created_at.desc()).all()
    return render_template("admin/dashboard.html", clients=clients, users=users,
                           users_admin=users_admin, projets=projets)


# ── Projets ───────────────────────────────────────────────────────────────────

@admin_bp.route("/projets/nouveau", methods=["GET", "POST"])
@admin_required
def nouveau_projet():
    if request.method == "POST":
        nom           = request.form.get("nom", "").strip()
        intitule      = request.form.get("intitule", "").strip()
        description   = request.form.get("description", "").strip()
        pk_debut      = request.form.get("pk_debut", "").strip()
        pk_fin        = request.form.get("pk_fin", "").strip()
        tolerance_str = request.form.get("tolerance_defaut", "").strip()
        plan          = request.form.get("plan", "solo")

        if not nom:
            flash("Le nom du projet est obligatoire.", "danger")
            return render_template("admin/projet_form.html")

        projet = Projet(
            nom=nom,
            intitule=intitule or None,
            description=description or None,
            pk_debut=pk_debut or None,
            pk_fin=pk_fin or None,
            tolerance_defaut=float(tolerance_str) if tolerance_str else None,
            plan=plan if plan in ("solo", "pro") else "solo",
        )
        db.session.add(projet)
        db.session.commit()
        flash(f"Projet « {nom} » créé.", "success")
        return redirect(url_for("admin.detail_projet", projet_id=projet.id))

    return render_template("admin/projet_form.html")


@admin_bp.route("/projets/<int:projet_id>")
@admin_required
def detail_projet(projet_id):
    projet      = db.get_or_404(Projet, projet_id)
    mdc_link    = projet.client_links.filter_by(role="mdc").first()
    et_link     = projet.client_links.filter_by(role="entreprise").first()
    all_clients = Client.query.filter_by(actif=True).order_by(Client.nom).all()
    all_users   = User.query.filter_by(actif=True, role="client").order_by(User.nom).all()

    # Génère des URLs présignées pour les logos (1h — pour prévisualisation admin)
    logo_mdc_preview = None
    logo_et_preview  = None
    if projet.logo_mdc_url:
        try:
            logo_mdc_preview = generate_presigned_url(projet.logo_mdc_url, 3600)
        except Exception:
            pass
    if projet.logo_et_url:
        try:
            logo_et_preview = generate_presigned_url(projet.logo_et_url, 3600)
        except Exception:
            pass

    membres = projet.membres.all()

    return render_template("admin/projet_detail.html",
                           projet=projet,
                           mdc_link=mdc_link,
                           et_link=et_link,
                           all_clients=all_clients,
                           all_users=all_users,
                           membres=membres,
                           logo_mdc_preview=logo_mdc_preview,
                           logo_et_preview=logo_et_preview)


@admin_bp.route("/projets/<int:projet_id>/toggle", methods=["POST"])
@admin_required
def toggle_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    projet.actif = not projet.actif
    db.session.commit()
    flash(f"Projet « {projet.nom} » {'activé' if projet.actif else 'désactivé'}.", "info")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/editer", methods=["POST"])
@admin_required
def editer_projet(projet_id):
    """Mettre à jour les métadonnées textuelles d'un projet."""
    projet        = db.get_or_404(Projet, projet_id)
    nom           = request.form.get("nom", "").strip()
    intitule      = request.form.get("intitule", "").strip()
    description   = request.form.get("description", "").strip()
    pk_debut      = request.form.get("pk_debut", "").strip()
    pk_fin        = request.form.get("pk_fin", "").strip()
    tolerance_str = request.form.get("tolerance_defaut", "").strip()

    if not nom:
        flash("Le nom du projet est obligatoire.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    projet.nom              = nom
    projet.intitule         = intitule or None
    projet.description      = description or None
    projet.pk_debut         = pk_debut or None
    projet.pk_fin           = pk_fin or None
    projet.tolerance_defaut = float(tolerance_str) if tolerance_str else None
    db.session.commit()
    flash(f"Projet « {nom} » mis à jour.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/logo/<string:role>", methods=["POST"])
@admin_required
def upload_logo(projet_id, role):
    """Upload le logo MDC ou ET d'un projet vers R2."""
    if role not in ("mdc", "et"):
        flash("Rôle invalide.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    projet     = db.get_or_404(Projet, projet_id)
    file_field = f"logo_{role}"
    if file_field not in request.files:
        flash("Aucun fichier fourni.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    f = request.files[file_field]
    if not f.filename or not _allowed_image(f.filename):
        flash("Format non supporté (PNG/JPG/GIF/WEBP uniquement).", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    ext          = f.filename.rsplit(".", 1)[1].lower()
    r2_key       = f"data/projets/{projet_id}/logo_{role}.{ext}"
    content_type = IMAGE_CONTENT_TYPES.get(ext, "image/png")

    try:
        r2_upload_image(f.read(), r2_key, content_type)
    except Exception as e:
        flash(f"Erreur upload R2 : {e}", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    attr = "logo_mdc_url" if role == "mdc" else "logo_et_url"
    setattr(projet, attr, r2_key)
    db.session.commit()
    flash(f"Logo {'MDC' if role == 'mdc' else 'ET'} mis à jour.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/toggle-plan", methods=["POST"])
@admin_required
def toggle_plan_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    if projet.plan == "pro":
        # Passage SOLO : supprimer le lien ET s'il existe
        et = projet.client_links.filter_by(role="entreprise").first()
        if et:
            db.session.delete(et)
        projet.plan = "solo"
        flash(f"Projet « {projet.nom} » repassé en SOLO (lien ET supprimé).", "info")
    else:
        projet.plan = "pro"
        flash(f"Projet « {projet.nom} » passé en PRO.", "success")
    db.session.commit()
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/supprimer", methods=["POST"])
@admin_required
def supprimer_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    nom = projet.nom
    db.session.delete(projet)
    db.session.commit()
    flash(f"Projet « {nom} » supprimé.", "info")
    return redirect(url_for("admin.dashboard"))


# ── Visualisation projet ──────────────────────────────────────────────────────

@admin_bp.route("/projets/<int:projet_id>/visualisation")
@admin_required
def visualisation_projet(projet_id):
    from ..services.excel_service import parse_modele_config
    from ..services.visualization_service import build_projet_context
    from ..services.r2_service import download_excel

    projet = db.get_or_404(Projet, projet_id)

    vis_ctx = None
    if projet.excel_key:
        try:
            excel_bytes = download_excel(projet.excel_key)
            config      = parse_modele_config(excel_bytes)
            vis_ctx     = build_projet_context(config)
        except Exception as e:
            flash(f"Analyse Excel : {e}", "warning")

    if vis_ctx is None:
        from ..services.visualization_service import generate_section_svg
        import json
        vis_ctx = {
            'gen': {}, 'profil_long': [], 'chart_labels': '[]', 'chart_z': '[]',
            'longueur_m': None, 'n_pk': 0, 'n_axe_sections': 0,
            'n_asg_sections': 0, 'n_asd_sections': 0, 'n_ter_points': 0,
            'has_asg': False, 'has_asd': False, 'has_profil': False,
            'ter_labels': [], 'layers': [], 'axe_sections': [],
            'asg_sections': [], 'asd_sections': [],
            'section_svg': generate_section_svg({}),
            'errors': [], 'available_elements': {},
        }

    logo_mdc_url = None
    logo_et_url  = None
    if projet.logo_mdc_url:
        try:
            logo_mdc_url = generate_presigned_url(projet.logo_mdc_url, 3600)
        except Exception:
            pass
    if projet.logo_et_url:
        try:
            logo_et_url = generate_presigned_url(projet.logo_et_url, 3600)
        except Exception:
            pass

    return render_template("admin/projet_visualisation.html",
                           projet=projet,
                           logo_mdc_url=logo_mdc_url,
                           logo_et_url=logo_et_url,
                           **vis_ctx)


# ── Upload Excel projet ───────────────────────────────────────────────────────

@admin_bp.route("/projets/<int:projet_id>/excel", methods=["POST"])
@admin_required
def upload_excel_projet(projet_id):
    projet = db.get_or_404(Projet, projet_id)
    if "excel_file" not in request.files:
        flash("Aucun fichier.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))
    f = request.files["excel_file"]
    if not f.filename or not _allowed_file(f.filename):
        flash("Format non supporté (.xlsx/.xls uniquement).", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))
    r2_key = f"data/projets/{projet_id}/modele.xlsx"
    try:
        r2_upload_excel(f.read(), r2_key)
    except Exception as e:
        flash(f"Erreur upload R2 : {e}", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))
    projet.excel_key = r2_key
    db.session.commit()
    if _autofill_projet_from_excel(projet, r2_key):
        db.session.commit()
        flash(f"Excel du projet « {projet.nom} » mis à jour — champs auto-complétés depuis l'Excel.", "success")
    else:
        flash(f"Excel du projet « {projet.nom} » mis à jour.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


# ── Associations Client ↔ Projet ──────────────────────────────────────────────

@admin_bp.route("/projets/<int:projet_id>/clients/associer", methods=["POST"])
@admin_required
def associer_client(projet_id):
    projet    = db.get_or_404(Projet, projet_id)
    client_id = request.form.get("client_id", type=int)
    role      = request.form.get("role", "")

    if not client_id or role not in ("mdc", "entreprise"):
        flash("Client et rôle obligatoires.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    if role == "entreprise" and projet.plan == "solo":
        flash("Un projet SOLO ne peut avoir qu'un client MDC.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    # Vérifier qu'il n'y a pas déjà un client pour ce rôle
    existing = projet.client_links.filter_by(role=role).first()
    if existing:
        flash(f"Ce projet a déjà un client {role.upper()}. Retirez-le d'abord.", "warning")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    # Vérifier que ce client n'est pas déjà associé dans un autre rôle
    already = ClientProjet.query.filter_by(client_id=client_id, projet_id=projet_id).first()
    if already:
        flash("Ce client est déjà associé à ce projet.", "warning")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    cp = ClientProjet(client_id=client_id, projet_id=projet_id, role=role)
    db.session.add(cp)
    db.session.commit()
    client = db.get_or_404(Client, client_id)
    flash(f"Client « {client.nom} » associé au projet en tant que {role.upper()}.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/clients/<int:cp_id>/retirer", methods=["POST"])
@admin_required
def retirer_client(projet_id, cp_id):
    cp = db.get_or_404(ClientProjet, cp_id)
    nom = cp.client.nom
    db.session.delete(cp)
    db.session.commit()
    flash(f"Client « {nom} » retiré du projet.", "info")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


# ── Clients ───────────────────────────────────────────────────────────────────

@admin_bp.route("/clients/nouveau", methods=["POST"])
@admin_required
def nouveau_client():
    nom   = request.form.get("nom", "").strip()
    label = request.form.get("projet_label", "").strip()
    plan  = request.form.get("plan", "solo")
    if not nom:
        flash("Le nom est obligatoire.", "danger")
        return redirect(url_for("admin.dashboard"))
    client = Client(nom=nom, projet_label=label or None,
                    plan=plan if plan in ("solo", "pro") else "solo")
    db.session.add(client)
    db.session.commit()
    flash(f"Client « {nom} » créé.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/modifier", methods=["POST"])
@admin_required
def modifier_client(client_id):
    client = db.get_or_404(Client, client_id)
    nom   = request.form.get("nom", "").strip()
    label = request.form.get("projet_label", "").strip()
    if not nom:
        flash("Le nom est obligatoire.", "danger")
        return redirect(url_for("admin.dashboard"))
    client.nom          = nom
    client.projet_label = label or None
    db.session.commit()
    flash(f"Client « {nom} » mis à jour.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/toggle-plan", methods=["POST"])
@admin_required
def toggle_plan_client(client_id):
    client = db.get_or_404(Client, client_id)
    client.plan = "pro" if client.plan == "solo" else "solo"
    db.session.commit()
    flash(f"Client « {client.nom} » passé en {client.plan.upper()}.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/toggle", methods=["POST"])
@admin_required
def toggle_client(client_id):
    client = db.get_or_404(Client, client_id)
    client.actif = not client.actif
    db.session.commit()
    flash(f"Client « {client.nom} » {'activé' if client.actif else 'désactivé'}.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/supprimer", methods=["POST"])
@admin_required
def supprimer_client(client_id):
    client = db.get_or_404(Client, client_id)
    nom = client.nom
    db.session.delete(client)
    db.session.commit()
    flash(f"Client « {nom} » supprimé.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/projet", methods=["POST"])
@admin_required
def gerer_projet_client(client_id):
    """Créer ou mettre à jour le projet d'un client (1-to-1)."""
    client        = db.get_or_404(Client, client_id)
    nom           = request.form.get("nom", "").strip() or client.nom
    pk_debut      = request.form.get("pk_debut", "").strip()
    pk_fin        = request.form.get("pk_fin", "").strip()
    tol_str       = request.form.get("tolerance_defaut", "").strip()
    description   = request.form.get("description", "").strip()

    projet = Projet.query.filter_by(client_id=client_id).first()
    if projet is None:
        projet = Projet(client_id=client_id, plan=client.plan)
        db.session.add(projet)

    projet.nom              = nom
    projet.pk_debut         = pk_debut or None
    projet.pk_fin           = pk_fin or None
    projet.tolerance_defaut = float(tol_str) if tol_str else None
    projet.description      = description or None
    projet.plan             = client.plan  # synchronisé avec le client
    db.session.commit()
    flash(f"Projet « {nom} » mis à jour.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/projet/excel", methods=["POST"])
@admin_required
def upload_excel_projet_client(client_id):
    """Upload Excel R2 pour le projet du client."""
    client = db.get_or_404(Client, client_id)
    if "excel_file" not in request.files:
        flash("Aucun fichier.", "danger")
        return redirect(url_for("admin.dashboard"))
    f = request.files["excel_file"]
    if not f.filename or not _allowed_file(f.filename):
        flash("Format non supporté (.xlsx/.xls).", "danger")
        return redirect(url_for("admin.dashboard"))

    r2_key = f"data/clients/{client_id}/modele.xlsx"
    try:
        r2_upload_excel(f.read(), r2_key)
    except Exception as e:
        flash(f"Erreur upload R2 : {e}", "danger")
        return redirect(url_for("admin.dashboard"))

    # Assurer qu'un projet existe et y stocker la clé
    projet = Projet.query.filter_by(client_id=client_id).first()
    if projet is None:
        projet = Projet(client_id=client_id, nom=client.nom, plan=client.plan)
        db.session.add(projet)
    projet.excel_key = r2_key
    db.session.commit()
    if _autofill_projet_from_excel(projet, r2_key):
        db.session.commit()
    flash(f"Excel uploadé pour « {client.nom} ».", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/excel", methods=["POST"])
@admin_required
def upload_excel(client_id):
    """Alias legacy — redirige vers upload_excel_projet_client."""
    return upload_excel_projet_client(client_id)


# ── Acteurs (utilisateurs) ────────────────────────────────────────────────────

@admin_bp.route("/utilisateurs/nouveau", methods=["GET", "POST"])
@admin_required
def nouvel_utilisateur():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        nom      = request.form.get("nom", "").strip()
        password = request.form.get("password", "")
        role     = request.form.get("role", "client")

        if not email or not nom or not password:
            flash("Tous les champs sont obligatoires.", "danger")
            return render_template("admin/user_form.html")

        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return render_template("admin/user_form.html")

        photo_url = request.form.get("photo_url", "").strip() or None
        user = User(email=email, nom=nom, role=role, photo_url=photo_url)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f"Acteur « {nom} » créé.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/user_form.html")


@admin_bp.route("/utilisateurs/<int:user_id>/modifier", methods=["GET", "POST"])
@admin_required
def modifier_utilisateur(user_id):
    user = db.get_or_404(User, user_id)
    if request.method == "POST":
        nom          = request.form.get("nom", "").strip()
        email        = request.form.get("email", "").strip().lower()
        role         = request.form.get("role", "client")
        new_password = request.form.get("password", "").strip()

        if not nom or not email:
            flash("Nom et email obligatoires.", "danger")
            return render_template("admin/user_form.html", user=user)

        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash("Cet email est déjà utilisé.", "danger")
            return render_template("admin/user_form.html", user=user)

        photo_url = request.form.get("photo_url", "").strip() or None
        user.nom       = nom
        user.email     = email
        user.role      = role
        user.photo_url = photo_url
        if new_password:
            user.set_password(new_password)
        db.session.commit()
        flash(f"Acteur « {nom} » mis à jour.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/user_form.html", user=user)


@admin_bp.route("/utilisateurs/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_utilisateur(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas vous désactiver vous-même.", "danger")
        return redirect(url_for("admin.dashboard"))
    user.actif = not user.actif
    db.session.commit()
    flash(f"Acteur « {user.nom} » {'activé' if user.actif else 'désactivé'}.", "info")
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
    flash(f"Acteur « {nom} » supprimé.", "info")
    return redirect(url_for("admin.dashboard"))


# ── Affiliations Acteur ↔ Client ──────────────────────────────────────────────

@admin_bp.route("/clients/<int:client_id>/acteurs/associer", methods=["POST"])
@admin_required
def associer_acteur(client_id):
    """Associer un acteur existant à un client avec un rôle (mdc | entreprise)."""
    client  = db.get_or_404(Client, client_id)
    user_id = request.form.get("user_id", type=int)
    role    = request.form.get("role", "mdc")

    if role not in ("mdc", "entreprise"):
        role = "mdc"
    if role == "entreprise" and client.plan != "pro":
        flash("Le rôle Entreprise nécessite un client en mode PRO.", "warning")
        return redirect(url_for("admin.dashboard"))
    if not user_id:
        flash("Acteur obligatoire.", "danger")
        return redirect(url_for("admin.dashboard"))

    existing = UserClient.query.filter_by(user_id=user_id, client_id=client_id).first()
    if existing:
        if existing.role != role:
            existing.role = role
            db.session.commit()
            user = db.get_or_404(User, user_id)
            flash(f"Rôle de « {user.nom} » mis à jour → {role.upper()}.", "info")
        else:
            flash("Cet acteur est déjà affilié à ce client avec ce rôle.", "warning")
        return redirect(url_for("admin.dashboard"))

    user = db.get_or_404(User, user_id)
    uc = UserClient(user_id=user_id, client_id=client_id, role=role)
    db.session.add(uc)
    db.session.commit()
    flash(f"« {user.nom} » ajouté comme {role.upper()} sur « {client.nom} ».", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/acteurs/creer", methods=["POST"])
@admin_required
def creer_acteur(client_id):
    """Créer un nouvel acteur et l'affilier directement à un client."""
    client   = db.get_or_404(Client, client_id)
    nom      = request.form.get("nom", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not nom or not email or not password:
        flash("Nom, email et mot de passe sont obligatoires.", "danger")
        return redirect(url_for("admin.dashboard"))

    if User.query.filter_by(email=email).first():
        flash(f"L'email « {email} » est déjà utilisé.", "danger")
        return redirect(url_for("admin.dashboard"))

    user = User(email=email, nom=nom, role="client")
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # obtenir user.id

    uc = UserClient(user_id=user.id, client_id=client_id)
    db.session.add(uc)
    db.session.commit()
    flash(f"Acteur « {nom} » créé et affilié à « {client.nom} ».", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/clients/<int:client_id>/acteurs/<int:uc_id>/retirer", methods=["POST"])
@admin_required
def retirer_acteur(client_id, uc_id):
    """Retirer l'affiliation d'un acteur à un client."""
    uc = db.get_or_404(UserClient, uc_id)
    nom = uc.user.nom
    db.session.delete(uc)
    db.session.commit()
    flash(f"« {nom} » retiré du client.", "info")
    return redirect(url_for("admin.dashboard"))


# ── Membres de projet (V3 direct) ─────────────────────────────────────────────

@admin_bp.route("/projets/<int:projet_id>/membres/ajouter", methods=["POST"])
@admin_required
def ajouter_membre(projet_id):
    projet        = db.get_or_404(Projet, projet_id)
    user_id       = request.form.get("user_id", type=int)
    role          = request.form.get("role", "controleur")
    entreprise_id = request.form.get("entreprise_id", type=int)

    if not user_id or role not in ("controleur", "travaux", "observateur"):
        flash("Opérateur et rôle valide obligatoires.", "danger")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    existing = MembreProjet.query.filter_by(user_id=user_id, projet_id=projet_id).first()
    if existing:
        existing.role          = role
        existing.entreprise_id = entreprise_id or None
        db.session.commit()
        flash(f"Rôle de « {existing.user.nom} » mis à jour → {existing.role_label}.", "info")
        return redirect(url_for("admin.detail_projet", projet_id=projet_id))

    mp = MembreProjet(projet_id=projet_id, user_id=user_id, role=role,
                      entreprise_id=entreprise_id or None)
    db.session.add(mp)
    db.session.commit()
    user = db.get_or_404(User, user_id)
    flash(f"« {user.nom} » ajouté en tant que {mp.role_label}.", "success")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


@admin_bp.route("/projets/<int:projet_id>/membres/<int:membre_id>/retirer", methods=["POST"])
@admin_required
def retirer_membre(projet_id, membre_id):
    mp  = db.get_or_404(MembreProjet, membre_id)
    nom = mp.user.nom
    db.session.delete(mp)
    db.session.commit()
    flash(f"« {nom} » retiré du projet.", "info")
    return redirect(url_for("admin.detail_projet", projet_id=projet_id))


# ── Associations génériques UserClient (dashboard) ────────────────────────────

@admin_bp.route("/associations/ajouter", methods=["POST"])
@admin_required
def ajouter_association():
    """Associe un opérateur à une entreprise (UserClient). Redirige vers le referrer."""
    from flask import request as req
    user_id   = request.form.get("user_id", type=int)
    client_id = request.form.get("client_id", type=int)
    role      = request.form.get("role", "mdc")

    if not user_id or not client_id or role not in ("mdc", "entreprise"):
        flash("Opérateur, entreprise et rôle obligatoires.", "danger")
        return redirect(request.referrer or url_for("admin.dashboard"))

    existing = UserClient.query.filter_by(user_id=user_id, client_id=client_id).first()
    if existing:
        if existing.role != role:
            existing.role = role
            db.session.commit()
            flash("Rôle mis à jour.", "info")
        else:
            flash("Association déjà existante.", "warning")
        return redirect(request.referrer or url_for("admin.dashboard"))

    user   = db.get_or_404(User, user_id)
    client = db.get_or_404(Client, client_id)
    uc = UserClient(user_id=user_id, client_id=client_id, role=role)
    db.session.add(uc)
    db.session.commit()
    flash(f"« {user.nom} » associé à « {client.nom} ».", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/associations/<int:uc_id>/retirer", methods=["POST"])
@admin_required
def retirer_association(uc_id):
    """Supprime une association UserClient. Redirige vers le referrer."""
    uc = db.get_or_404(UserClient, uc_id)
    db.session.delete(uc)
    db.session.commit()
    flash("Association retirée.", "info")
    return redirect(request.referrer or url_for("admin.dashboard"))
