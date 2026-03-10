# app/services/pdf_service.py
"""
Service de génération des fiches de réception PDF.
Gère WeasyPrint (natif) et le fallback HTML (impression navigateur).
"""
from flask import render_template, current_app

try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    current_app.logger.warning(
        "WeasyPrint non disponible — l'export PDF utilisera le fallback HTML."
    ) if False else None  # Pas de contexte app au import-time, log différé


def _compute_stats(stations: list) -> dict:
    """Calcule les statistiques de conformité à partir des stations."""
    total = conformes = non_conformes = 0
    for station in stations:
        for row in station.get("rows", []):
            if row.get("cote_mesuree") and row.get("cote_mesuree") != "-":
                total += 1
                if row.get("ecart_status") == "ok":
                    conformes += 1
                else:
                    non_conformes += 1
    percent = (conformes / total * 100) if total > 0 else 0
    return {
        "total_points": total,
        "points_conformes": conformes,
        "points_non_conformes": non_conformes,
        "conformes_percent": percent,
    }


def build_template_context(data: dict) -> dict:
    """
    Extrait tous les paramètres du dict JSON entrant et calcule les stats.
    Utilisé par generate_pdf ET preview_pdf pour éviter la duplication.
    """
    stations = data.get("stations", [])
    stats = _compute_stats(stations)

    return dict(
        projet=data.get("projet", ""),
        date=data.get("date", ""),
        operateur=data.get("operateur", ""),
        section=data.get("section", ""),
        meteo=data.get("meteo", ""),
        tolerance=data.get("tolerance", 2),
        mode=data.get("mode", "assainissement"),
        controleur_nom=data.get("controleur_nom", ""),
        controleur_fonction=data.get("controleur_fonction", ""),
        controleur_date=data.get("controleur_date", ""),
        entreprise_nom=data.get("entreprise_nom", ""),
        entreprise_societe=data.get("entreprise_societe", ""),
        entreprise_date=data.get("entreprise_date", ""),
        signature_controleur=data.get("signature_controleur"),
        signature_entreprise=data.get("signature_entreprise"),
        observations_generales=data.get("observations_generales", ""),
        stations=stations,
        **stats,
    )


def render_fiche_html(context: dict) -> str:
    """Rend le template HTML de la fiche de réception."""
    return render_template("pdf/fiche_reception.html", **context)


def make_pdf_bytes(html_content: str, base_url: str) -> bytes:
    """
    Convertit le HTML en PDF via WeasyPrint.
    Lève RuntimeError si WeasyPrint n'est pas disponible.
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint n'est pas installé.")
    return WeasyHTML(string=html_content, base_url=base_url).write_pdf()
