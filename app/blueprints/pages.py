# app/blueprints/pages.py
"""
Blueprint des routes de pages HTML.
Toutes les pages sont protégées par @login_required.
"""
from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user

pages_bp = Blueprint("pages", __name__)


def _resolve_role(projet_id: int) -> str | None:
    """Rôle du user courant sur ce projet (mdc | entreprise | admin | None)."""
    if current_user.is_admin:
        return "admin"
    from ..models import MembreProjet, UserClient, ClientProjet
    # V3 direct
    mp = MembreProjet.query.filter_by(projet_id=projet_id, user_id=current_user.id).first()
    if mp:
        return {"controleur": "mdc", "travaux": "entreprise", "observateur": "mdc"}.get(mp.role, mp.role)
    # V2 legacy
    cp_entries = ClientProjet.query.filter_by(projet_id=projet_id).all()
    role_by_client = {cp.client_id: cp.role for cp in cp_entries}
    if not role_by_client:
        return None
    uc = UserClient.query.filter(
        UserClient.user_id == current_user.id,
        UserClient.client_id.in_(list(role_by_client.keys()))
    ).first()
    return role_by_client.get(uc.client_id) if uc else None


@pages_bp.route("/")
def home():
    """Page d'entrée — redirige les utilisateurs connectés vers leur espace."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        from ..models import UserClient, MembreProjet
        has_projet = (
            UserClient.query.filter_by(user_id=current_user.id).first()
            or MembreProjet.query.filter_by(user_id=current_user.id).first()
        )
        if has_projet:
            return redirect(url_for("pro_projets.liste_projets"))
        return render_template("home.html")
    return render_template("intro.html")


@pages_bp.route("/landing")
def landing():
    """Page marketing complète (landing page)."""
    return render_template("landing.html")


@pages_bp.route("/editeur")
@login_required
def editeur():
    """Phase 1 — Éditeur de profil en travers."""
    return render_template("index.html")


@pages_bp.route("/points-kilometriques")
@login_required
def points_kilometriques():
    """Phase 2 — Gestion des points kilométriques."""
    return render_template("points_kilometriques.html")


@pages_bp.route("/reception")
@login_required
def reception():
    """
    Réception topographique — contexte projet optionnel.

    Query params :
      projet_id  (int)  — projet concerné
      demande_id (int)  — demande de réception (mode PRO ET→MDC)
      pro        (0|1)  — flag mode partenariat (héritage redirect reception_mdc)
    """
    from ..models import Projet, DemandeReception

    projet_id     = request.args.get("projet_id",  type=int)
    demande_id    = request.args.get("demande_id", type=int)
    is_simulation = request.args.get("simulation", "0") == "1"

    projet  = None
    demande = None
    role    = "mdc"   # défaut : autonome MDC

    if projet_id:
        projet = Projet.query.get(projet_id)
        if projet:
            role = _resolve_role(projet_id) or "mdc"

    if demande_id:
        demande = DemandeReception.query.get(demande_id)
        # Si la demande porte un projet_id et qu'on n'a pas encore de projet
        if demande and not projet:
            projet = demande.projet
            if projet:
                role = _resolve_role(projet.id) or "mdc"

    return render_template(
        "reception_topographique.html",
        projet=projet,
        demande=demande,
        user_role=role,
        is_simulation=is_simulation,
    )


@pages_bp.route("/historique")
@login_required
def historique():
    """Historique des fiches de réception archivées."""
    return render_template("historique.html")
