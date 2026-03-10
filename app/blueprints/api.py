# app/blueprints/api.py
"""
Blueprint des routes API (JSON / binaire).
Délègue la logique métier aux services.
"""
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, Response, send_file
from flask_login import login_required, current_user

from ..services.excel_service import get_sheet_names, get_sheet_data
from ..services.r2_service import download_excel
from ..services.pdf_service import (
    WEASYPRINT_AVAILABLE,
    build_template_context,
    render_fiche_html,
    make_pdf_bytes,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _get_excel_source():
    """
    Retourne la source Excel du client connecté :
    - Si le client a une clé R2 → télécharge les bytes depuis R2.
    - Sinon → retourne le Path du fichier modèle par défaut.
    """
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

@api_bp.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    """
    Génère la fiche de réception.
    Retourne un PDF (WeasyPrint) ou du HTML (fallback impression navigateur).
    """
    try:
        data = request.get_json(force=True)
        context = build_template_context(data)
        html_content = render_fiche_html(context)

        if WEASYPRINT_AVAILABLE:
            pdf_bytes = make_pdf_bytes(html_content, request.host_url)
            filename = f"Fiche_Reception_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        # Fallback : HTML pour impression navigateur
        return Response(html_content, mimetype="text/html; charset=utf-8")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/preview-pdf", methods=["POST"])
def preview_pdf():
    """
    Retourne toujours du HTML (pour window.print() côté navigateur).
    Même logique que generate_pdf, sans la branche WeasyPrint.
    """
    try:
        data = request.get_json(force=True)
        context = build_template_context(data)
        html_content = render_fiche_html(context)
        return Response(html_content, mimetype="text/html; charset=utf-8")
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
