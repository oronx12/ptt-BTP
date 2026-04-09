# app/blueprints/pro/projets.py
"""
Blueprint PRO — Gestion des projets collaboratifs (V2).
Accessible uniquement aux clients plan='pro' et aux admins.
"""
from flask import Blueprint, render_template
from flask_login import current_user

from ..admin import pro_required
from ...models import Projet, MembreProjet

pro_projets_bp = Blueprint("pro_projets", __name__, url_prefix="/pro/projets")


@pro_projets_bp.route("/")
@pro_required
def liste_projets():
    """Liste les projets auxquels l'utilisateur connecté appartient."""
    if current_user.is_admin:
        # Admin voit tout
        projets = [(p, "admin") for p in Projet.query.order_by(Projet.created_at.desc()).all()]
    else:
        # Utilisateur PRO : projets où il est MembreProjet
        memberships = (MembreProjet.query
                       .filter_by(user_id=current_user.id, actif=True)
                       .all())
        projets = [(m.projet, m.role) for m in memberships if m.projet.actif]

    return render_template("pro/projets_liste.html", projets=projets)
