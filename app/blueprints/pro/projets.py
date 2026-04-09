# app/blueprints/pro/projets.py
"""
Blueprint PRO — Gestion des projets collaboratifs (V2).
Accessible uniquement aux clients plan='pro' et aux admins.
"""
from flask import Blueprint, jsonify
from flask_login import current_user

from ..admin import pro_required
from ...models import Projet

pro_projets_bp = Blueprint("pro_projets", __name__, url_prefix="/pro/projets")


@pro_projets_bp.route("/")
@pro_required
def liste_projets():
    """Liste les projets V2 du client connecté (stub — template à venir)."""
    if current_user.is_admin:
        projets = Projet.query.order_by(Projet.created_at.desc()).all()
    else:
        projets = Projet.query.filter_by(
            client_id=current_user.client_id, actif=True
        ).order_by(Projet.created_at.desc()).all()

    return jsonify([
        {"id": p.id, "nom": p.nom, "pk_debut": p.pk_debut, "pk_fin": p.pk_fin}
        for p in projets
    ])
