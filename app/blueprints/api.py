# app/blueprints/api.py
"""
Blueprint des routes API (JSON / binaire).
Délègue la logique métier aux services.
"""
import re
import base64
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, Response, send_file
from flask_login import login_required, current_user

from ..services.excel_service import get_sheet_names, get_sheet_data
from ..services.r2_service import download_excel, upload_fiche, generate_presigned_url
from ..services.pdf_service import (
    WEASYPRINT_AVAILABLE,
    build_template_context,
    render_fiche_html,
    make_pdf_bytes,
    make_pdf_bytes_any,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _get_excel_source():
    """
    Retourne la source Excel du client connecté :
    - Si le projet du client a une clé R2 → télécharge les bytes depuis R2.
    - Sinon → retourne le Path du fichier modèle par défaut.
    """
    from ..models import Projet, UserClient

    if current_user.is_authenticated and not current_user.is_admin:
        uc = UserClient.query.filter_by(user_id=current_user.id).first()
        if uc:
            projet = Projet.query.filter_by(client_id=uc.client_id).first()
            if projet and projet.excel_key:
                try:
                    return download_excel(projet.excel_key)
                except FileNotFoundError:
                    pass
    return current_app.config["MODEL_EXCEL"]


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

@api_bp.route("/excel/sheets", methods=["GET"])
@login_required
def excel_sheets():
    """Retourne la liste des onglets du fichier Excel du client connecté."""
    try:
        sheets = get_sheet_names(_get_excel_source())
        return jsonify({"sheets": sheets})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/pro/projets/<int:projet_id>/pks", methods=["GET"])
@login_required
def get_projet_pks(projet_id):
    """Retourne la liste triée des PK disponibles dans l'Excel d'un projet."""
    from ..models import Projet, UserClient

    projet = Projet.query.get_or_404(projet_id)

    if not current_user.is_admin:
        if not projet.client_id:
            return jsonify({"error": "Accès refusé"}), 403
        acces = UserClient.query.filter_by(
            user_id=current_user.id, client_id=projet.client_id
        ).first()
        if not acces:
            return jsonify({"error": "Accès refusé"}), 403

    if not projet.excel_key:
        return jsonify({"error": "Aucun fichier Excel associé à ce projet"}), 404

    try:
        excel_bytes = download_excel(projet.excel_key)
        sheets = get_sheet_names(excel_bytes)
        all_pks = set()
        for sheet in sheets:
            try:
                data = get_sheet_data(excel_bytes, sheet)
                all_pks.update(str(pk) for pk in data["pks"] if pk is not None)
            except Exception:
                pass
        return jsonify({"pks": sorted(all_pks, key=str)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/pro/projets/<int:projet_id>/sheets", methods=["GET"])
@login_required
def get_projet_sheets(projet_id):
    """Retourne tous les onglets + données côtes théoriques d'un projet."""
    from ..models import Projet, UserClient

    projet = Projet.query.get_or_404(projet_id)

    if not current_user.is_admin:
        if not projet.client_id:
            return jsonify({"error": "Accès refusé"}), 403
        acces = UserClient.query.filter_by(
            user_id=current_user.id, client_id=projet.client_id
        ).first()
        if not acces:
            return jsonify({"error": "Accès refusé"}), 403

    if not projet.excel_key:
        return jsonify({"error": "Aucun fichier Excel associé à ce projet"}), 404

    try:
        excel_bytes = download_excel(projet.excel_key)
        sheets = get_sheet_names(excel_bytes)
        result = {}
        for sheet in sheets:
            try:
                result[sheet] = get_sheet_data(excel_bytes, sheet)
            except Exception as e:
                result[sheet] = {"error": str(e)}
        return jsonify({"sheets": result, "sheet_names": sheets})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Helpers accès projet V3 ───────────────────────────────────────────────────

def _acces_projet(projet_id: int):
    """
    Vérifie l'accès au projet.
    Retourne (projet, None) si OK, (projet, response_403) sinon.
    Priorité : MembreProjet direct (V3) → UserClient+ClientProjet (V2).
    """
    from ..models import Projet, ClientProjet, UserClient, MembreProjet
    projet = Projet.query.get_or_404(projet_id)
    if current_user.is_admin:
        return projet, None
    # V3 direct
    if MembreProjet.query.filter_by(projet_id=projet_id, user_id=current_user.id).first():
        return projet, None
    # V2 UserClient → ClientProjet
    cp_entries  = ClientProjet.query.filter_by(projet_id=projet_id).all()
    client_ids  = [cp.client_id for cp in cp_entries]
    if client_ids:
        uc = UserClient.query.filter(
            UserClient.user_id == current_user.id,
            UserClient.client_id.in_(client_ids)
        ).first()
        if uc:
            return projet, None
    return projet, (jsonify({"error": "Accès refusé"}), 403)


# ── Config projet (format paramétrique) ──────────────────────────────────────

@api_bp.route("/pro/projets/<int:projet_id>/config", methods=["GET"])
@login_required
def get_projet_config(projet_id):
    """
    Retourne la config parsée du projet :
      { format, pks, elements, pk_debut, pk_fin, tolerance }
    format = 'parametric' si l'Excel a un profil en long AXE_
           = 'legacy'     si l'Excel a des onglets Cote_Gauche/Cote_Droit
    """
    from ..services.excel_service import parse_modele_config
    from ..services.calculation_service import elements_disponibles

    projet, err = _acces_projet(projet_id)
    if err:
        return err

    if not projet.excel_key:
        return jsonify({"error": "Aucun fichier Excel associé à ce projet"}), 404

    # Logos présignés (non bloquants)
    logo_mdc = None
    logo_et  = None
    if projet.logo_mdc_url:
        try: logo_mdc = generate_presigned_url(projet.logo_mdc_url, 3600)
        except Exception: pass
    if projet.logo_et_url:
        try: logo_et  = generate_presigned_url(projet.logo_et_url,  3600)
        except Exception: pass

    try:
        excel_bytes = download_excel(projet.excel_key)
        config      = parse_modele_config(excel_bytes)

        profil = config.get('profil_long', [])
        if profil:
            # Format paramétrique
            pks  = [p['pk'] for p in profil]
            elts = elements_disponibles(config)

            # Extra info pour le flux de paramétrage (Type → PK → Sections → Parties)
            pk_m_map      = {p['pk']: p['pk_m'] for p in profil}
            secs_raw      = config.get('sections', {})
            sections_info = {
                grp: [{'pk_debut_m': s.get('pk_debut_m', 0),
                       'pk_fin_m':   s.get('pk_fin_m')}
                      for s in secs]
                for grp, secs in secs_raw.items()
            }
            has_ter   = bool(secs_raw.get('AXE'))
            has_ass_g = bool(secs_raw.get('ASG') and
                             (config.get('ass_long_g') or config.get('ass_long')))
            has_ass_d = bool(secs_raw.get('ASD') and
                             (config.get('ass_long_d') or config.get('ass_long')))

            # Sections de profil en travers (TER_PROFIL_TYPE) — pour l'étape "Parties"
            from collections import OrderedDict
            ter_raw = config.get('ter_points', [])
            _sec_map = OrderedDict()
            for pt in ter_raw:
                deb  = pt.get('pk_debut_m')
                fin  = pt.get('pk_fin_m')
                k    = (deb, fin)
                if k not in _sec_map:
                    _sec_map[k] = {'pk_debut_m': deb, 'pk_fin_m': fin, 'g': [], 'd': []}
                side = 'g' if 'G' in str(pt.get('cote', '')).upper() else 'd'
                _sec_map[k][side].append({
                    'label':      pt.get('label') or f"{side.upper()}{len(_sec_map[k][side])+1}",
                    'dist_axe_m': pt.get('dist_axe_m'),
                    'pente_pct':  pt.get('pente_pct'),
                    'ordre':      pt.get('ordre'),
                })
            profil_sections = list(_sec_map.values())

            return jsonify({
                'format':          'parametric',
                'pks':             pks,
                'elements':        elts,
                'pk_debut':        projet.pk_debut or (pks[0] if pks else None),
                'pk_fin':          projet.pk_fin   or (pks[-1] if pks else None),
                'tolerance':       projet.tolerance_defaut or 2.0,
                'errors':          config.get('errors', []),
                'logo_mdc_url':    logo_mdc,
                'logo_et_url':     logo_et,
                'pk_m_map':        pk_m_map,
                'sections_info':   sections_info,
                'has_ter':         has_ter,
                'has_ass_g':       has_ass_g,
                'has_ass_d':       has_ass_d,
                'profil_sections': profil_sections,
            })
        else:
            # Pas de profil en long → fallback legacy (onglets Cote_*)
            sheets_data = get_sheet_names(excel_bytes)
            legacy_sheets = [s for s in sheets_data
                             if 'COTE' in s.upper() or 'GAUCH' in s.upper()
                             or 'DROIT' in s.upper()]
            # Calculer les PK communs à tous les onglets legacy
            all_pks: list[set] = []
            for s in legacy_sheets:
                try:
                    sd = get_sheet_data(excel_bytes, s)
                    all_pks.append(set(str(p) for p in sd['pks']))
                except Exception:
                    pass
            common = sorted(
                set.intersection(*all_pks) if all_pks else set(),
                key=str
            )
            return jsonify({
                'format':    'legacy',
                'pks':       common,
                'sheet_names': legacy_sheets,
                'pk_debut':  projet.pk_debut or (common[0] if common else None),
                'pk_fin':    projet.pk_fin   or (common[-1] if common else None),
                'tolerance': projet.tolerance_defaut or 2.0,
                'logo_mdc_url': logo_mdc,
                'logo_et_url':  logo_et,
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── SVG profil en travers (Feature 5) ────────────────────────────────────────

@api_bp.route("/projets/<int:projet_id>/section-svg", methods=["GET"])
@login_required
def get_section_svg(projet_id):
    """Retourne le SVG du profil en travers type du projet."""
    from ..models import Projet, MembreProjet
    from ..services.excel_service import parse_modele_config
    from ..services.visualization_service import generate_section_svg

    projet = Projet.query.get_or_404(projet_id)
    if not current_user.is_admin:
        from ..models import ClientProjet, UserClient
        is_membre = MembreProjet.query.filter_by(
            projet_id=projet_id, user_id=current_user.id).first()
        if not is_membre:
            cp_entries = ClientProjet.query.filter_by(projet_id=projet_id).all()
            client_ids = [cp.client_id for cp in cp_entries]
            uc = UserClient.query.filter(
                UserClient.user_id == current_user.id,
                UserClient.client_id.in_(client_ids)
            ).first() if client_ids else None
            if not uc:
                return jsonify({"error": "Accès refusé"}), 403

    if not projet.excel_key:
        return jsonify({"available": False, "svg": None})
    try:
        config = parse_modele_config(download_excel(projet.excel_key))
        svg    = generate_section_svg(config)
        return jsonify({"available": True, "svg": svg})
    except Exception as e:
        return jsonify({"available": False, "svg": None, "error": str(e)})


# ── Côtes théoriques (format paramétrique) ────────────────────────────────────

@api_bp.route("/pro/projets/<int:projet_id>/cotes", methods=["POST"])
@login_required
def get_projet_cotes(projet_id):
    """
    Calcule les côtes théoriques pour une liste de PK.
    Corps JSON : { "pks": ["1+000", "1+050", ...] }
    Réponse    : { "cotes_by_pk": { "1+000": [{key, label, cote, groupe}] } }
    """
    from ..services.excel_service import parse_modele_config
    from ..services.calculation_service import cotes_pour_pk

    projet, err = _acces_projet(projet_id)
    if err:
        return err

    body = request.get_json(silent=True) or {}
    pks  = body.get('pks', [])
    if not pks:
        return jsonify({"error": "Liste de PK vide"}), 400

    if not projet.excel_key:
        return jsonify({"error": "Aucun fichier Excel associé à ce projet"}), 404

    try:
        excel_bytes  = download_excel(projet.excel_key)
        config       = parse_modele_config(excel_bytes)
        cotes_by_pk  = {}
        for pk in pks:
            cotes_by_pk[pk] = cotes_pour_pk(pk, config)
        return jsonify({"cotes_by_pk": cotes_by_pk})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/pro/projets/<int:projet_id>/demandes", methods=["GET"])
@login_required
def get_projet_demandes(projet_id):
    """
    Retourne les demandes d'un projet avec leur verdict de réception,
    pour coloriser les tronçons sur la carte.
    """
    from ..models import Projet, UserClient, DemandeReception

    projet = Projet.query.get_or_404(projet_id)
    if not current_user.is_admin:
        if not projet.client_id:
            return jsonify({"error": "Accès refusé"}), 403
        acces = UserClient.query.filter_by(
            user_id=current_user.id, client_id=projet.client_id
        ).first()
        if not acces:
            return jsonify({"error": "Accès refusé"}), 403

    demandes = DemandeReception.query.filter_by(projet_id=projet_id).all()
    return jsonify({
        "demandes": [
            {
                "id":               d.id,
                "numero":           d.numero,
                "pk_debut":         d.pk_debut,
                "pk_fin":           d.pk_fin,
                "statut":           d.statut,
                "statut_reception": d.statut_reception,
                "projet_nom":       projet.nom,
                "cloture_at":       d.cloture_at.isoformat() if d.cloture_at else None,
            }
            for d in demandes
        ]
    })


@api_bp.route("/pro/projets/<int:projet_id>/spatialisation", methods=["GET"])
@login_required
def get_spatialisation(projet_id):
    """
    Retourne les données de spatialisation du projet depuis les onglets Excel
    GEO_COORDONNEES (coordonnées UTM Zone 31N de l'axe principal) et
    GEO_AXES_PARALLELES (axes parallèles à l'axe par section avec distance).
    """
    import pandas as pd
    from io import BytesIO
    from ..models import Projet, UserClient, MembreProjet

    projet = Projet.query.get_or_404(projet_id)

    if not current_user.is_admin:
        has_access = MembreProjet.query.filter_by(
            projet_id=projet_id, user_id=current_user.id
        ).first() is not None
        if not has_access and projet.client_id:
            has_access = UserClient.query.filter_by(
                user_id=current_user.id, client_id=projet.client_id
            ).first() is not None
        if not has_access:
            return jsonify({"error": "Accès refusé"}), 403

    excel_bytes = None
    excel_path  = None
    if projet.excel_key:
        try:
            excel_bytes = download_excel(projet.excel_key)
        except Exception:
            pass

    if excel_bytes is None:
        src = _get_excel_source()
        if isinstance(src, (str, Path)):
            excel_path = Path(src)
        else:
            excel_bytes = bytes(src)

    def make_source():
        return BytesIO(excel_bytes) if excel_bytes else excel_path

    def safe_float(v):
        try:
            f = float(v)
            return f if f == f else None
        except (TypeError, ValueError):
            return None

    def is_empty(v):
        return v is None or str(v).strip() in ("", "nan", "None", "NaT")

    # ── Lire GEO_COORDONNEES ─────────────────────────────────────────────────
    # Structure : row 1 = titre, row 2 = headers (PK, XY_X, XY_Y, XY_Z, XY_Cap_deg), row 3+ = données
    pks_data   = []
    has_coords = False
    try:
        df_pk = pd.read_excel(make_source(), sheet_name="GEO_COORDONNEES", header=1)
        for _, row in df_pk.iterrows():
            pk_v = row.iloc[0] if len(row) > 0 else None
            if is_empty(pk_v):
                continue
            # Ignorer lignes de commentaire (texte long, pas un PK)
            if isinstance(pk_v, str) and len(pk_v) > 20:
                continue
            pks_data.append({
                "pk":  str(pk_v),
                "x":   safe_float(row.iloc[1]) if len(row) > 1 else None,  # UTM 31N — Easting
                "y":   safe_float(row.iloc[2]) if len(row) > 2 else None,  # UTM 31N — Northing
                "z":   safe_float(row.iloc[3]) if len(row) > 3 else None,  # Cote NGF axe
                "cap": safe_float(row.iloc[4]) if len(row) > 4 else None,  # Azimut depuis Nord (°)
            })
        has_coords = len(pks_data) > 0
    except Exception:
        pass

    # ── Lire GEO_AXES_PARALLELES ─────────────────────────────────────────────
    # Structure : row 1 = titre, row 2 = headers
    # (Num, PK_debut, PK_fin, XY_Label, XY_Cote, XY_Dist_m, XY_Description), row 3+ = données
    paralleles_data = []
    try:
        df_par = pd.read_excel(make_source(), sheet_name="GEO_AXES_PARALLELES", header=1)
        for _, row in df_par.iterrows():
            num_v = row.iloc[0] if len(row) > 0 else None
            if is_empty(num_v):
                continue
            # Ignorer lignes d'instruction (texte long en colonne Num)
            if isinstance(num_v, str) and len(num_v) > 20:
                continue
            label_v = row.iloc[3] if len(row) > 3 else None
            if is_empty(label_v):
                continue
            dist_v = safe_float(row.iloc[5]) if len(row) > 5 else None
            if dist_v is None:
                continue
            cote_v = str(row.iloc[4]).strip().upper() if len(row) > 4 and not is_empty(row.iloc[4]) else "D"
            desc_v = row.iloc[6] if len(row) > 6 and not is_empty(row.iloc[6]) else label_v
            paralleles_data.append({
                "label":       str(label_v),
                "cote":        cote_v,           # "G" ou "D"
                "dist_m":      dist_v,           # distance perpendiculaire positive (m)
                "pk_debut":    str(row.iloc[1]) if len(row) > 1 and not is_empty(row.iloc[1]) else "",
                "pk_fin":      str(row.iloc[2]) if len(row) > 2 and not is_empty(row.iloc[2]) else "",
                "description": str(desc_v),
            })
    except Exception:
        pass

    return jsonify({
        "available":   has_coords,
        "pks":         pks_data,
        "paralleles":  paralleles_data,
    })


@api_bp.route("/excel/data/<sheet_name>", methods=["GET"])
@login_required
def excel_data(sheet_name):
    """Retourne les données d'un onglet Excel du client connecté."""
    try:
        data = get_sheet_data(_get_excel_source(), sheet_name)
        return jsonify(data)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _enrich_data_with_projet(data: dict) -> None:
    """
    Enrichit le dict PDF avec intitule et URLs présignées des logos (MDC / ET).
    Non critique : silencieux si projet introuvable.
    """
    try:
        from ..models import Projet, UserClient, DemandeReception

        projet = None
        demande_id = data.get("demande_id")
        if demande_id:
            d = DemandeReception.query.get(int(demande_id))
            if d:
                projet = d.projet

        if projet is None and current_user.is_authenticated and not current_user.is_admin:
            uc = UserClient.query.filter_by(user_id=current_user.id).first()
            if uc:
                projet = Projet.query.filter_by(client_id=uc.client_id).first()

        if projet:
            if projet.intitule and not data.get("intitule"):
                data["intitule"] = projet.intitule
            if projet.logo_mdc_url:
                try:
                    data["logo_mdc_url"] = generate_presigned_url(projet.logo_mdc_url, 3600)
                except Exception:
                    pass
            if projet.logo_et_url:
                try:
                    data["logo_et_url"] = generate_presigned_url(projet.logo_et_url, 3600)
                except Exception:
                    pass
    except Exception:
        pass


def _archive_fiche(data: dict, html_content: str, demande_id: int = None) -> None:
    """
    Archive la fiche HTML dans R2 et enregistre les métadonnées en base.
    Si demande_id est fourni, lie la fiche à la DemandeReception correspondante.
    Non critique : les erreurs sont silencieuses pour ne pas bloquer le téléchargement.
    """
    try:
        from ..models import FicheReception, UserClient, DemandeReception
        from .. import db as _db

        if not current_user.is_authenticated or current_user.is_admin:
            return
        uc = UserClient.query.filter_by(user_id=current_user.id).first()
        if not uc:
            return
        client_id = uc.client_id

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        r2_key = f"fiches/{client_id}/{ts}.html"
        upload_fiche(html_content.encode("utf-8"), r2_key)

        sv = data.get("statut_verdict")
        if sv not in ("validee", "non_validee", "a_reprendre"):
            sv = None

        fiche = FicheReception(
            client_id=client_id,
            user_id=current_user.id,
            r2_key=r2_key,
            projet=data.get("projet", ""),
            section=data.get("section", ""),
            date_reception=data.get("date", ""),
            operateur=data.get("operateur", ""),
            statut_verdict=sv,
        )
        _db.session.add(fiche)
        _db.session.flush()  # obtenir fiche.id avant le commit

        # Lier la fiche à la demande PRO si fournie
        if demande_id:
            demande = DemandeReception.query.get(demande_id)
            if demande:
                demande.fiche_id = fiche.id
                if sv:  # Propager le verdict sur la demande
                    demande.statut_reception = sv

        _db.session.commit()
    except Exception:
        pass  # archivage non critique


@api_bp.route("/generate-pdf", methods=["POST"])
@login_required
def generate_pdf():
    """
    Génère la fiche de réception et l'archive dans R2.
    Essaie xhtml2pdf (Render) puis WeasyPrint, fallback HTML si les deux échouent.
    """
    try:
        data = request.get_json(force=True)
        _enrich_data_with_projet(data)
        context = build_template_context(data)
        html_content = render_fiche_html(context)

        # Archivage automatique dans R2 (lier à la demande PRO si présent)
        demande_id = data.get("demande_id")
        _archive_fiche(data, html_content, demande_id=int(demande_id) if demande_id else None)

        try:
            pdf_bytes = make_pdf_bytes_any(html_content, request.host_url)
            filename = f"Fiche_Reception_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception:
            # Fallback : HTML pour impression navigateur si aucun moteur PDF dispo
            return Response(html_content, mimetype="text/html; charset=utf-8")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/preview-pdf", methods=["POST"])
@login_required
def preview_pdf():
    """
    Retourne toujours du HTML (pour window.print() côté navigateur).
    """
    try:
        data = request.get_json(force=True)
        _enrich_data_with_projet(data)
        context = build_template_context(data)
        html_content = render_fiche_html(context)
        return Response(html_content, mimetype="text/html; charset=utf-8")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Historique des fiches
# ---------------------------------------------------------------------------

@api_bp.route("/fiches", methods=["GET"])
@login_required
def list_fiches():
    """Liste les fiches archivées — toutes si admin, sinon celles du client connecté."""
    from ..models import FicheReception, UserClient
    if current_user.is_admin:
        fiches = FicheReception.query.order_by(FicheReception.created_at.desc()).limit(200).all()
    else:
        uc = UserClient.query.filter_by(user_id=current_user.id).first()
        client_id = uc.client_id if uc else None
        fiches = (FicheReception.query
                  .filter_by(client_id=client_id)
                  .order_by(FicheReception.created_at.desc())
                  .limit(50).all())

    return jsonify([{
        "id":             f.id,
        "projet":         f.projet or "—",
        "section":        f.section or "—",
        "date_reception": f.date_reception or "—",
        "operateur":      f.operateur or "—",
        "created_at":     f.created_at.strftime("%d/%m/%Y %H:%M") if f.created_at else "—",
        "client_nom":     f.client.nom if f.client else "—",
    } for f in fiches])


@api_bp.route("/fiches/<int:fiche_id>/url", methods=["GET"])
@login_required
def fiche_url(fiche_id):
    """Génère une URL signée (1h) pour télécharger/consulter une fiche archivée."""
    from ..models import FicheReception
    from .. import db
    fiche = db.get_or_404(FicheReception, fiche_id)

    if not current_user.is_admin:
        from ..models import UserClient
        uc = UserClient.query.filter_by(user_id=current_user.id).first()
        if not uc or fiche.client_id != uc.client_id:
            return jsonify({"error": "Accès refusé."}), 403

    url = generate_presigned_url(fiche.r2_key)
    return jsonify({"url": url})


# ---------------------------------------------------------------------------
# Envoi de fiche par email
# ---------------------------------------------------------------------------

@api_bp.route("/send-fiche-email", methods=["POST"])
@login_required
def send_fiche_email():
    """
    Génère la fiche HTML puis l'envoie par email aux parties prenantes.
    Corps JSON attendu :
      {
        "fiche_data": { ...même structure que generate-pdf... },
        "destinataires": ["email1@ex.fr", "email2@ex.fr"],
        "message_perso": "Texte optionnel ajouté dans le corps du mail"
      }
    """
    try:
        import resend
        from flask import current_app

        body = request.get_json(force=True)
        fiche_data   = body.get("fiche_data", {})
        destinataires = body.get("destinataires", [])
        message_perso = body.get("message_perso", "").strip()

        # Validation minimale
        if not destinataires:
            return jsonify({"error": "Aucun destinataire fourni."}), 400

        destinataires_valides = [e.strip() for e in destinataires if "@" in e.strip()]
        if not destinataires_valides:
            return jsonify({"error": "Aucune adresse email valide."}), 400

        # Clé API Resend
        api_key = current_app.config.get("RESEND_API_KEY", "")
        if not api_key:
            return jsonify({"error": "Service email non configuré (RESEND_API_KEY manquant)."}), 503

        resend.api_key = api_key

        # Générer le HTML de la fiche
        context      = build_template_context(fiche_data)
        html_content = render_fiche_html(context)

        # Archiver dans R2 (silencieux si erreur)
        _archive_fiche(fiche_data, html_content)

        # Infos pour le mail
        projet  = fiche_data.get("projet", "Projet")
        date    = fiche_data.get("date", "")
        section = fiche_data.get("section", "")
        operateur = fiche_data.get("operateur", "")

        # Calcul conformité pour résumé
        total, conformes, non_conformes = 0, 0, 0
        for st in fiche_data.get("stations", []):
            for row in st.get("rows", []):
                if row.get("is_interpolated"):
                    continue
                total += 1
                if row.get("ecart_status") == "ok":
                    conformes += 1
                else:
                    non_conformes += 1
        pct = round(conformes / total * 100, 1) if total > 0 else 0
        statut_label = "✅ Conforme" if pct >= 95 else ("⚠️ Partiellement conforme" if pct >= 80 else "❌ Non conforme")

        mail_from = current_app.config.get("MAIL_FROM", "OPTILAB <noreply@ptt-btp.fr>")
        sujet     = f"Fiche de réception — {projet} | {section} — {date}"

        # Corps email HTML
        intro = f"<p style='margin:0 0 12px;'>{message_perso}</p>" if message_perso else ""
        corps_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#1e293b;">
            <div style="background:linear-gradient(135deg,#0f2744,#1d4ed8);padding:24px 28px;border-radius:8px 8px 0 0;">
                <div style="color:white;font-size:20px;font-weight:800;letter-spacing:0.5px;">OPTILAB</div>
                <div style="color:rgba(255,255,255,0.75);font-size:13px;margin-top:4px;">Fiche de Réception Topographique</div>
            </div>
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;">
                {intro}
                <p style="margin:0 0 20px;font-size:14px;color:#475569;">
                    Veuillez trouver ci-joint la fiche de réception topographique générée le <strong>{date}</strong>.
                </p>
                <div style="background:white;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin-bottom:20px;">
                    <table style="width:100%;font-size:13px;border-collapse:collapse;">
                        <tr><td style="padding:5px 0;color:#94a3b8;width:130px;">Projet</td><td style="padding:5px 0;font-weight:700;">{projet}</td></tr>
                        <tr><td style="padding:5px 0;color:#94a3b8;">Section</td><td style="padding:5px 0;font-weight:700;">{section or "—"}</td></tr>
                        <tr><td style="padding:5px 0;color:#94a3b8;">Opérateur</td><td style="padding:5px 0;font-weight:700;">{operateur or "—"}</td></tr>
                        <tr><td style="padding:5px 0;color:#94a3b8;">Date contrôle</td><td style="padding:5px 0;font-weight:700;">{date}</td></tr>
                        <tr><td style="padding:5px 0;color:#94a3b8;">Résultat</td>
                            <td style="padding:5px 0;font-weight:700;">
                                <span style="background:{"#dcfce7" if pct >= 95 else ("#fefce8" if pct >= 80 else "#fee2e2")};
                                             color:{"#15803d" if pct >= 95 else ("#b45309" if pct >= 80 else "#b91c1c")};
                                             padding:3px 10px;border-radius:20px;font-size:12px;">
                                    {statut_label} — {pct}%
                                </span>
                            </td>
                        </tr>
                        <tr><td style="padding:5px 0;color:#94a3b8;">Points mesurés</td><td style="padding:5px 0;">{total} ({conformes} conformes / {non_conformes} hors tolérance)</td></tr>
                    </table>
                </div>
                <p style="font-size:12px;color:#94a3b8;margin:0;">
                    La fiche complète est jointe à cet email au format PDF.<br>
                    Ce document est officiel — à conserver pendant la durée légale des travaux.
                </p>
            </div>
            <div style="background:#f1f5f9;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;padding:12px 28px;font-size:11px;color:#94a3b8;text-align:center;">
                OPTILAB — Système de Réception Topographique &nbsp;·&nbsp; Envoyé automatiquement
            </div>
        </div>
        """

        base_name = f"Fiche_Reception_{projet.replace(' ','_')}_{date.replace('/','').replace('-','')}"
        nom_pdf   = base_name + ".pdf"

        # Générer le PDF — obligatoire, on retourne une erreur si ça échoue
        pdf_bytes = make_pdf_bytes_any(html_content, request.host_url)

        # Resend attend le contenu en base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        attachments = [
            {
                "filename": nom_pdf,
                "content":  pdf_b64,
            }
        ]

        params = {
            "from":        mail_from,
            "to":          destinataires_valides,
            "subject":     sujet,
            "html":        corps_html,
            "attachments": attachments,
        }

        resend.Emails.send(params)

        return jsonify({
            "success": True,
            "message": f"Fiche envoyée à {len(destinataires_valides)} destinataire(s).",
            "destinataires": destinataires_valides,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Téléchargement sécurisé
# ---------------------------------------------------------------------------

# Seuls les noms de fichiers sans chemin (pas de / ni de \) sont autorisés.
_SAFE_FILENAME = re.compile(r'^[\w\-. ]+$')


@api_bp.route("/download/<filename>")
def download_file(filename):
    """
    Télécharge un fichier depuis le répertoire temporaire.
    Protégé contre le path traversal : seul le nom de fichier (sans chemin) est accepté.
    """
    if not _SAFE_FILENAME.match(filename):
        return jsonify({"error": "Nom de fichier invalide."}), 400

    tmp_dir: Path = current_app.config["TEMP_DIR"]
    file_path = tmp_dir / filename

    if not file_path.exists():
        return jsonify({"error": "Fichier introuvable."}), 404

    return send_file(str(file_path.resolve()), as_attachment=True)
