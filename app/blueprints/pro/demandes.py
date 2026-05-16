# app/blueprints/pro/demandes.py
"""Blueprint PRO — Demandes de réception."""
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import current_user

from ..admin import pro_required
from ... import db
from ...models import DemandeReception, Projet, UserClient, ClientProjet, MembreProjet

pro_demandes_bp = Blueprint("pro_demandes", __name__, url_prefix="/pro/demandes")

# Correspondance rôles V2 ↔ V3
_V3_ROLE = {"entreprise": ["travaux"], "mdc": ["controleur", "observateur"]}
_V3_TO_V2 = {"controleur": "mdc", "travaux": "entreprise", "observateur": "mdc"}


def _get_user_role(projet_id: int) -> str | None:
    """Rôle du user sur ce projet — V3 MembreProjet en priorité, puis V2 UserClient."""
    if current_user.is_admin:
        return "admin"
    # V3 direct
    mp = MembreProjet.query.filter_by(projet_id=projet_id, user_id=current_user.id).first()
    if mp:
        return _V3_TO_V2.get(mp.role, mp.role)
    # V2 UserClient → ClientProjet
    cp_entries = ClientProjet.query.filter_by(projet_id=projet_id).all()
    role_by_client = {cp.client_id: cp.role for cp in cp_entries}
    if not role_by_client:
        return None
    uc = UserClient.query.filter(
        UserClient.user_id == current_user.id,
        UserClient.client_id.in_(list(role_by_client.keys()))
    ).first()
    return role_by_client.get(uc.client_id) if uc else None


def _get_user_projets(role: str) -> list:
    """Projets où le user a le rôle donné — V3 MembreProjet + V2 UserClient."""
    projet_ids: set[int] = set()

    # V3 direct
    for v3_role in _V3_ROLE.get(role, []):
        for mp in MembreProjet.query.filter_by(user_id=current_user.id, role=v3_role).all():
            projet_ids.add(mp.projet_id)

    # V2 UserClient → ClientProjet
    ucs = UserClient.query.filter_by(user_id=current_user.id).all()
    client_ids = [uc.client_id for uc in ucs]
    if client_ids:
        for cp in ClientProjet.query.filter(
            ClientProjet.client_id.in_(client_ids),
            ClientProjet.role == role
        ).all():
            projet_ids.add(cp.projet_id)

    if not projet_ids:
        return []
    return Projet.query.filter(
        Projet.id.in_(list(projet_ids)), Projet.actif == True
    ).all()


def _get_user_projet_ids(role: str) -> list[int]:
    return [p.id for p in _get_user_projets(role)]


# ── Liste ─────────────────────────────────────────────────────────────────────

@pro_demandes_bp.route("/")
@pro_required
def liste_demandes():
    if current_user.is_admin:
        demandes_et  = DemandeReception.query.order_by(DemandeReception.created_at.desc()).all()
        demandes_mdc = []
        has_et_role  = False
    else:
        et_projets = _get_user_projets("entreprise")
        mdc_ids    = _get_user_projet_ids("mdc")
        has_et_role = bool(et_projets)

        demandes_et = (DemandeReception.query
                       .filter(DemandeReception.demandeur_id == current_user.id)
                       .order_by(DemandeReception.created_at.desc()).all())

        demandes_mdc = (DemandeReception.query
                        .filter(DemandeReception.projet_id.in_(mdc_ids))
                        .filter(DemandeReception.statut.in_(["en_attente", "accusee", "acceptee"]))
                        .order_by(DemandeReception.created_at.desc()).all())

    return render_template("pro/demandes_liste.html",
                           demandes_et=demandes_et,
                           demandes_mdc=demandes_mdc,
                           has_et_role=has_et_role)


# ── Nouvelle demande ──────────────────────────────────────────────────────────

@pro_demandes_bp.route("/nouvelle", methods=["GET", "POST"])
@pro_required
def nouvelle_demande():
    if current_user.is_admin:
        projets_et = Projet.query.filter_by(actif=True).all()
    else:
        projets_et = _get_user_projets("entreprise")

    if not projets_et:
        flash("Vous n'êtes pas Entreprise sur aucun projet actif.", "warning")
        return redirect(url_for("pro_projets.liste_projets"))

    if request.method == "POST":
        import json as _json
        projet_id      = request.form.get("projet_id", type=int)
        pk_debut       = request.form.get("pk_debut", "").strip()
        pk_fin         = request.form.get("pk_fin", "").strip()
        date_souhaitee = request.form.get("date_souhaitee", "").strip()
        heure          = request.form.get("heure_souhaitee", "").strip()
        observations   = request.form.get("observations", "").strip()
        mode           = request.form.get("mode", "assainissement").strip()
        tolerance      = request.form.get("tolerance", type=float) or 2.0
        meteo          = request.form.get("meteo", "").strip()

        # parties — supporte deux formats :
        #   legacy     : [{sheet, col}, ...]
        #   paramétrique : [{key, label, groupe}, ...]
        parties_raw = request.form.get("parties", "").strip()
        try:
            parties = _json.loads(parties_raw) if parties_raw else None
        except Exception:
            parties = None

        # pks_list — liste ordonnée des PK sélectionnés (format paramétrique)
        pks_raw = request.form.get("pks_list", "").strip()
        try:
            pks_list = _json.loads(pks_raw) if pks_raw else None
        except Exception:
            pks_list = None

        if not projet_id or not pk_debut or not pk_fin:
            flash("Projet, PK début et PK fin sont obligatoires.", "danger")
            return render_template("pro/demande_form.html", projets_et=projets_et)

        role = _get_user_role(projet_id)
        if role not in ("entreprise", "admin"):
            flash("Vous n'êtes pas Entreprise sur ce projet.", "danger")
            return render_template("pro/demande_form.html", projets_et=projets_et)

        demande = DemandeReception(
            numero=DemandeReception.generate_numero(),
            projet_id=projet_id,
            demandeur_id=current_user.id,
            pk_debut=pk_debut,
            pk_fin=pk_fin,
            pks_list=pks_list,
            mode=mode,
            tolerance=tolerance,
            meteo=meteo or None,
            date_souhaitee=datetime.strptime(date_souhaitee, "%Y-%m-%d").date()
                           if date_souhaitee else None,
            heure_souhaitee=heure or None,
            observations=observations or None,
            parties=parties,
        )
        db.session.add(demande)
        db.session.commit()
        flash(f"Demande {demande.numero} soumise.", "success")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande.id))

    return render_template("pro/demande_form.html", projets_et=projets_et)


# ── Détail ────────────────────────────────────────────────────────────────────

@pro_demandes_bp.route("/<int:demande_id>")
@pro_required
def detail_demande(demande_id):
    demande = DemandeReception.query.get_or_404(demande_id)
    role    = _get_user_role(demande.projet_id)
    if role is None and demande.demandeur_id != current_user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for("pro_demandes.liste_demandes"))
    return render_template("pro/demande_detail.html", demande=demande, role=role)


# ── Actions MDC ───────────────────────────────────────────────────────────────

@pro_demandes_bp.route("/<int:demande_id>/accuser", methods=["POST"])
@pro_required
def accuser_reception(demande_id):
    demande = DemandeReception.query.get_or_404(demande_id)
    if _get_user_role(demande.projet_id) not in ("mdc", "admin"):
        flash("Action réservée à la MDC.", "danger")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    if demande.statut != "en_attente":
        flash("Cette demande n'est plus en attente.", "warning")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    demande.statut    = "accusee"
    demande.accuse_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"Accusé de réception enregistré pour {demande.numero}.", "success")
    return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))


@pro_demandes_bp.route("/<int:demande_id>/accepter", methods=["POST"])
@pro_required
def accepter_demande(demande_id):
    demande = DemandeReception.query.get_or_404(demande_id)
    if _get_user_role(demande.projet_id) not in ("mdc", "admin"):
        flash("Action réservée à la MDC.", "danger")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    if demande.statut != "accusee":
        flash("La demande doit être accusée avant d'être acceptée.", "warning")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    demande.statut     = "acceptee"
    demande.accepte_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"Demande {demande.numero} acceptée.", "success")
    return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))


@pro_demandes_bp.route("/<int:demande_id>/refuser", methods=["POST"])
@pro_required
def refuser_demande(demande_id):
    demande = DemandeReception.query.get_or_404(demande_id)
    if _get_user_role(demande.projet_id) not in ("mdc", "admin"):
        flash("Action réservée à la MDC.", "danger")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    if demande.statut not in ("en_attente", "accusee"):
        flash("Cette demande ne peut plus être refusée.", "warning")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    motif = request.form.get("motif_refus", "").strip()
    if not motif:
        flash("Le motif de refus est obligatoire.", "danger")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    demande.statut      = "refusee"
    demande.motif_refus = motif
    db.session.commit()
    flash(f"Demande {demande.numero} refusée.", "info")
    return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))


# ── Verdict de réception (MDC uniquement) ────────────────────────────────────

@pro_demandes_bp.route("/<int:demande_id>/verdict", methods=["POST"])
@pro_required
def verdict_demande(demande_id):
    """
    MDC enregistre le verdict après la réception topographique.
    Statuts possibles : validee | non_validee | a_reprendre.
    Passe la demande en 'cloturee' avec horodatage.
    """
    demande = DemandeReception.query.get_or_404(demande_id)
    if _get_user_role(demande.projet_id) not in ("mdc", "admin"):
        flash("Action réservée à la Mission de Contrôle.", "danger")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))
    if demande.statut != "acceptee":
        flash("La demande doit être acceptée pour enregistrer un verdict.", "warning")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))

    statut_rec = request.form.get("statut_reception", "").strip()
    if statut_rec not in ("validee", "non_validee", "a_reprendre"):
        flash("Verdict invalide.", "danger")
        return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))

    labels = {"validee": "Validée ✓", "non_validee": "Non validée ✗", "a_reprendre": "À reprendre ↩"}
    demande.statut_reception = statut_rec
    demande.statut           = "cloturee"
    demande.cloture_at       = datetime.now(timezone.utc)
    db.session.commit()

    flash(f"Verdict enregistré : {labels[statut_rec]}.", "success")
    return redirect(url_for("pro_demandes.detail_demande", demande_id=demande_id))


# ── Historique des réceptions clôturées ──────────────────────────────────────

@pro_demandes_bp.route("/historique/")
@pro_required
def historique_receptions():
    """Toutes les demandes clôturées visibles par l'utilisateur."""
    if current_user.is_admin:
        demandes = (DemandeReception.query
                    .filter_by(statut="cloturee")
                    .order_by(DemandeReception.cloture_at.desc()).all())
    else:
        mdc_ids = _get_user_projet_ids("mdc")
        demandes_mdc = (DemandeReception.query
                        .filter(DemandeReception.projet_id.in_(mdc_ids),
                                DemandeReception.statut == "cloturee")
                        .order_by(DemandeReception.cloture_at.desc()).all()) if mdc_ids else []
        demandes_et = (DemandeReception.query
                       .filter_by(demandeur_id=current_user.id, statut="cloturee")
                       .order_by(DemandeReception.cloture_at.desc()).all())
        # Fusionner sans doublons
        seen, demandes = set(), []
        for d in demandes_mdc + demandes_et:
            if d.id not in seen:
                seen.add(d.id)
                demandes.append(d)
        demandes.sort(key=lambda x: x.cloture_at or x.created_at, reverse=True)

    # Est-ce que l'utilisateur a le rôle MDC sur au moins un projet ?
    is_mdc = current_user.is_admin or bool(_get_user_projet_ids("mdc"))

    return render_template("pro/historique_receptions.html", demandes=demandes, is_mdc=is_mdc)


# ── Endpoint JSON — paramètres de la demande (pour pré-remplir la réception) ──

@pro_demandes_bp.route("/<int:demande_id>/params")
@pro_required
def params_demande(demande_id):
    """Retourne les paramètres de paramétrage saisis par ET, pour pré-remplir la réception MDC."""
    demande = DemandeReception.query.get_or_404(demande_id)
    role = _get_user_role(demande.projet_id)
    if role not in ("mdc", "admin"):
        return jsonify({"error": "Accès refusé."}), 403
    from ...services.r2_service import generate_presigned_url
    logo_mdc = None
    logo_et  = None
    if demande.projet:
        if demande.projet.logo_mdc_url:
            try: logo_mdc = generate_presigned_url(demande.projet.logo_mdc_url, 3600)
            except Exception: pass
        if demande.projet.logo_et_url:
            try: logo_et  = generate_presigned_url(demande.projet.logo_et_url, 3600)
            except Exception: pass

    return jsonify({
        "pk_debut":     demande.pk_debut,
        "pk_fin":       demande.pk_fin,
        "pks_list":     demande.pks_list or [],
        "mode":         demande.mode or "assainissement",
        "tolerance":    demande.tolerance or 2.0,
        "meteo":        demande.meteo or "",
        "parties":      demande.parties or [],
        "projet_id":    demande.projet_id,
        "logo_mdc_url": logo_mdc,
        "logo_et_url":  logo_et,
    })
