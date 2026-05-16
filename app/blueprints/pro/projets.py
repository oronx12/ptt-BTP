# app/blueprints/pro/projets.py
"""Blueprint PRO — Tableau de bord Projets (ET | MDC)."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from sqlalchemy import func

from ..admin import pro_required
from ...models import Projet, UserClient, ClientProjet, MembreProjet
from ...services.r2_service import generate_presigned_url

pro_projets_bp = Blueprint("pro_projets", __name__, url_prefix="/pro/projets")


def _get_role(projet_id: int) -> str | None:
    """
    Rôle du user sur ce projet.
    Priorité : MembreProjet (V3 direct) → ClientProjet+UserClient (V2 legacy).
    """
    if current_user.is_admin:
        return "admin"
    # V3 direct
    mp = MembreProjet.query.filter_by(projet_id=projet_id, user_id=current_user.id).first()
    if mp:
        # Normaliser : 'controleur' → 'mdc', 'travaux' → 'entreprise' pour compat V2
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


@pro_projets_bp.route("/")
@pro_required
def liste_projets():
    from ...models import DemandeReception, MembreProjet as MP
    from ... import db as _db

    ROLE_MAP = {"controleur": "mdc", "travaux": "entreprise", "observateur": "mdc"}

    if current_user.is_admin:
        all_p = Projet.query.filter_by(actif=True).order_by(Projet.created_at.desc()).all()
        projets = [(p, "admin") for p in all_p]
    else:
        role_by_projet: dict[int, str] = {}

        # V2 path: UserClient → ClientProjet
        ucs = UserClient.query.filter_by(user_id=current_user.id).all()
        client_ids = [uc.client_id for uc in ucs]
        if client_ids:
            for cp in ClientProjet.query.filter(ClientProjet.client_id.in_(client_ids)).all():
                role_by_projet.setdefault(cp.projet_id, cp.role)

        # V3 path: MembreProjet direct
        for mp in MP.query.filter_by(user_id=current_user.id).all():
            role_by_projet.setdefault(mp.projet_id, ROLE_MAP.get(mp.role, mp.role))

        projet_ids = list(role_by_projet.keys())
        projets_raw = Projet.query.filter(
            Projet.id.in_(projet_ids), Projet.actif == True
        ).order_by(Projet.created_at.desc()).all()
        projets = [(p, role_by_projet[p.id]) for p in projets_raw]

    et_projets  = [(p, r) for p, r in projets if r == "entreprise"]
    mdc_projets = [(p, r) for p, r in projets if r in ("mdc", "admin")]

    # Compteurs de demandes en attente par projet MDC
    mdc_ids = [p.id for p, _ in mdc_projets]
    if mdc_ids:
        rows = (_db.session.query(DemandeReception.projet_id, func.count(DemandeReception.id))
                .filter(DemandeReception.projet_id.in_(mdc_ids),
                        DemandeReception.statut.in_(["en_attente", "accusee"]))
                .group_by(DemandeReception.projet_id).all())
        pending_by_projet = dict(rows)
    else:
        pending_by_projet = {}

    pending_count = sum(pending_by_projet.values())

    et_demandes_count = (
        DemandeReception.query.filter_by(demandeur_id=current_user.id)
        .with_entities(func.count(DemandeReception.id)).scalar()
    ) if not current_user.is_admin else 0

    return render_template(
        "pro/projets_liste.html",
        projets=projets,
        et_projets=et_projets,
        mdc_projets=mdc_projets,
        pending_by_projet=pending_by_projet,
        pending_count=pending_count,
        et_demandes_count=et_demandes_count,
    )


@pro_projets_bp.route("/<int:projet_id>")
@pro_required
def projet_hub(projet_id):
    """Page d'accueil d'un projet — toutes les actions disponibles."""
    from ...models import DemandeReception
    from ... import db as _db

    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role is None:
        flash("Accès refusé.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))

    pending_count = 0
    if role in ("mdc", "admin"):
        pending_count = (
            DemandeReception.query
            .filter_by(projet_id=projet_id)
            .filter(DemandeReception.statut.in_(["en_attente", "accusee"]))
            .count()
        )

    return render_template(
        "pro/projet_hub.html",
        projet=projet,
        role=role,
        pending_count=pending_count,
    )


@pro_projets_bp.route("/<int:projet_id>/top-reception")
@pro_required
def top_reception(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role is None:
        flash("Accès refusé.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))
    if not projet.excel_key:
        flash("Pas de fichier Excel associé à ce projet.", "warning")
        return redirect(url_for("pro_projets.liste_projets"))
    return render_template("pro/top_reception.html", projet=projet, role=role)


@pro_projets_bp.route("/<int:projet_id>/simulation")
@pro_required
def simulation(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role is None:
        flash("Accès refusé.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))
    if not projet.excel_key:
        flash("Pas de fichier Excel associé à ce projet.", "warning")
        return redirect(url_for("pro_projets.liste_projets"))
    return render_template("pro/simulation.html", projet=projet, role=role)


@pro_projets_bp.route("/<int:projet_id>/reception-mdc")
@pro_required
def reception_mdc(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role not in ("mdc", "admin", "entreprise"):
        flash("Accès refusé.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))
    if not projet.excel_key:
        flash("Pas de fichier Excel associé à ce projet.", "warning")
        return redirect(url_for("pro_projets.liste_projets"))
    # Rediriger vers la page de réception unifiée (modèle paramétrique + PDF officiel)
    pk_debut   = request.args.get("pk_debut", "")
    pk_fin     = request.args.get("pk_fin", "")
    demande_id = request.args.get("demande_id", "")
    qs = f"?pro=1&projet_id={projet_id}"
    if pk_debut:   qs += f"&pk_debut={pk_debut}"
    if pk_fin:     qs += f"&pk_fin={pk_fin}"
    if demande_id: qs += f"&demande_id={demande_id}"
    return redirect(f"/reception{qs}")


# ── Visualisation projet ─────────────────────────────────────────────────────

@pro_projets_bp.route("/<int:projet_id>/visualisation")
@pro_required
def visualisation(projet_id):
    from ...services.excel_service import parse_modele_config
    from ...services.visualization_service import build_projet_context, generate_section_svg
    from ...services.r2_service import download_excel

    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role is None:
        flash("Accès refusé.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))

    vis_ctx = None
    if projet.excel_key:
        try:
            excel_bytes = download_excel(projet.excel_key)
            config      = parse_modele_config(excel_bytes)
            vis_ctx     = build_projet_context(config)
        except Exception as e:
            flash(f"Analyse Excel : {e}", "warning")

    if vis_ctx is None:
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
                           role=role,
                           logo_mdc_url=logo_mdc_url,
                           logo_et_url=logo_et_url,
                           **vis_ctx)


# ── Carte de spatialisation (MDC / admin uniquement) ──────────────────────────

@pro_projets_bp.route("/<int:projet_id>/carte")
@pro_required
def carte_projet(projet_id):
    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role not in ("mdc", "admin"):
        flash("La carte est réservée à la Mission de Contrôle.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))
    return render_template("pro/carte.html", projet=projet, role=role)


@pro_projets_bp.route("/<int:projet_id>/rapport")
@pro_required
def rapport_receptions(projet_id):
    """Rapport imprimable des réceptions clôturées, filtrable par période."""
    from ...models import DemandeReception
    from datetime import datetime, timezone

    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role not in ("mdc", "admin"):
        flash("Le rapport est réservé à la Mission de Contrôle.", "danger")
        return redirect(url_for("pro_projets.liste_projets"))

    date_debut_str = request.args.get("date_debut", "").strip()
    date_fin_str   = request.args.get("date_fin",   "").strip()

    q = DemandeReception.query.filter_by(projet_id=projet_id, statut="cloturee")

    if date_debut_str:
        try:
            q = q.filter(DemandeReception.cloture_at >=
                         datetime.strptime(date_debut_str, "%Y-%m-%d"))
        except ValueError:
            date_debut_str = ""
    if date_fin_str:
        try:
            fin = datetime.strptime(date_fin_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59)
            q = q.filter(DemandeReception.cloture_at <= fin)
        except ValueError:
            date_fin_str = ""

    demandes = q.order_by(DemandeReception.cloture_at).all()
    nb_val = sum(1 for d in demandes if d.statut_reception == "validee")
    nb_nv  = sum(1 for d in demandes if d.statut_reception == "non_validee")
    nb_ar  = sum(1 for d in demandes if d.statut_reception == "a_reprendre")

    return render_template("pro/rapport_receptions.html",
                           projet=projet,
                           demandes=demandes,
                           nb_val=nb_val, nb_nv=nb_nv, nb_ar=nb_ar,
                           date_debut=date_debut_str,
                           date_fin=date_fin_str,
                           now=datetime.now(timezone.utc))


@pro_projets_bp.route("/<int:projet_id>/carte/save-gps", methods=["POST"])
@pro_required
def save_gps(projet_id):
    """Sauvegarde les coordonnées GPS du tracé (JSON)."""
    from ... import db
    projet = Projet.query.get_or_404(projet_id)
    role   = _get_role(projet_id)
    if role not in ("mdc", "admin"):
        return jsonify({"error": "Accès refusé."}), 403
    data = request.get_json(silent=True) or {}
    projet.coordonnees_gps = data.get("points")   # liste de {"pk","lat","lng"}
    db.session.commit()
    return jsonify({"ok": True, "nb_points": len(projet.coordonnees_gps or [])})
