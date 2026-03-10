# app/blueprints/auth.py
"""Authentification : login / logout."""
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.home"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email, actif=True).first()

        if user and user.check_password(password):
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=remember)
            # Redirection vers la page demandée ou l'accueil
            next_page = request.args.get("next")
            return redirect(next_page or url_for("pages.home"))

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))
