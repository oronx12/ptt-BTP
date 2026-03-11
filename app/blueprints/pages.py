# app/blueprints/pages.py
"""
Blueprint des routes de pages HTML.
Toutes les pages sont protégées par @login_required.
"""
from flask import Blueprint, render_template
from flask_login import login_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
@login_required
def home():
    """Page d'accueil — choix du pipeline de travail."""
    return render_template("home.html")


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
