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
    - Si admin avec fichier de test sélectionné → retourne ce fichier local.
    - Si le client a une clé R2 → télécharge les bytes depuis R2.
    - Sinon → retourne le Path du fichier modèle par défaut.
    """
    from flask import session
    from pathlib import Path as _Path

    # Admin : fichier de test choisi depuis le panel admin
    if current_user.is_authenticated and current_user.is_admin:
        test_path = session.get("admin_test_excel")
        if test_path:
            p = _Path(test_path)
            if p.exists():
                return p

    if current_user.is_authenticated and current_user.client and current_user.excel_key:
        try:
            return download_excel(current_user.excel_key)
        except FileNotFoundError:
            pass  # fallback sur le fichier local
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

def _archive_fiche(data: dict, html_content: str) -> None:
    """
    Archive la fiche HTML dans R2 et enregistre les métadonnées en base.
    Non critique : les erreurs sont silencieuses pour ne pas bloquer le téléchargement.
    """
    if not (current_user.is_authenticated and current_user.client_id):
        return
    try:
        from ..models import FicheReception
        from .. import db as _db

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        r2_key = f"fiches/{current_user.client_id}/{ts}.html"
        upload_fiche(html_content.encode("utf-8"), r2_key)

        fiche = FicheReception(
            client_id=current_user.client_id,
            user_id=current_user.id,
            r2_key=r2_key,
            projet=data.get("projet", ""),
            section=data.get("section", ""),
            date_reception=data.get("date", ""),
            operateur=data.get("operateur", ""),
        )
        _db.session.add(fiche)
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
        context = build_template_context(data)
        html_content = render_fiche_html(context)

        # Archivage automatique dans R2
        _archive_fiche(data, html_content)

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
    from ..models import FicheReception
    if current_user.is_admin:
        fiches = FicheReception.query.order_by(FicheReception.created_at.desc()).limit(200).all()
    else:
        fiches = (FicheReception.query
                  .filter_by(client_id=current_user.client_id)
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

    if not current_user.is_admin and fiche.client_id != current_user.client_id:
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
