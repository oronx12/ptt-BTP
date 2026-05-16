# app/blueprints/pages.py
"""
Blueprint des routes de pages HTML.
Toutes les pages sont protégées par @login_required.
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

pages_bp = Blueprint("pages", __name__)


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
    """Phase 3 — Réception topographique."""
    return render_template("reception_topographique.html")


@pages_bp.route("/historique")
@login_required
def historique():
    """Historique des fiches de réception archivées."""
    return render_template("historique.html")
