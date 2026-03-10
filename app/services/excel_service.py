# app/services/excel_service.py
"""
Service de lecture et parsing du fichier Excel modèle.
Isolé de Flask — peut être utilisé et testé indépendamment.
Accepte indifféremment un Path local ou des bytes (contenu R2).
"""
from pathlib import Path
from io import BytesIO
import pandas as pd
import openpyxl


def _to_file_like(source):
    """Normalise une source Path ou bytes en objet file-like pour pandas/openpyxl."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Fichier Excel introuvable : {path}")
        return path
    # bytes ou BytesIO
    if isinstance(source, bytes):
        return BytesIO(source)
    return source  # déjà file-like


def get_sheet_names(source) -> list[str]:
    """Retourne la liste des onglets du fichier Excel."""
    file_like = _to_file_like(source)
    wb = openpyxl.load_workbook(file_like, read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


def get_sheet_data(source, sheet_name: str) -> dict:
    """
    Lit un onglet Excel et retourne un dict structuré :
    {
        pk_column: str,
        pks: list,
        cote_columns: list[str],
        all_columns: list[str],
        data: list[dict]
    }
    Lève ValueError si la colonne PK est introuvable.
    """
    file_like = _to_file_like(source)
    df = pd.read_excel(file_like, sheet_name=sheet_name)

    # Nettoyage NaN / NaT
    df = df.replace({pd.NA: None, pd.NaT: None})
    df = df.where(pd.notnull(df), None)

    columns = df.columns.tolist()

    # Détection colonne PK
    pk_column = next(
        (col for col in columns
         if "PK" in str(col).upper() or "KILOMETRIQUE" in str(col).upper()),
        None,
    )
    if pk_column is None:
        raise ValueError("Colonne PK introuvable dans l'onglet (cherche 'PK' ou 'KILOMETRIQUE')")

    # PK non vides
    pks = [pk for pk in df[pk_column].tolist() if pk is not None and str(pk).strip() != ""]

    # Colonnes de côtes = toutes les colonnes numériques sauf PK
    cote_columns = [
        col for col in columns
        if col != pk_column and pd.api.types.is_numeric_dtype(df[col])
    ]

    # Sérialisation sûre (NaN / Inf → None)
    clean_records = []
    for record in df.to_dict(orient="records"):
        clean = {}
        for key, value in record.items():
            if value is None:
                clean[key] = None
            elif isinstance(value, float):
                if value != value or value in (float("inf"), float("-inf")):
                    clean[key] = None
                else:
                    clean[key] = value
            elif isinstance(value, int):
                clean[key] = value
            else:
                clean[key] = str(value)
        clean_records.append(clean)

    return {
        "pk_column": pk_column,
        "pks": pks,
        "cote_columns": cote_columns,
        "all_columns": columns,
        "data": clean_records,
    }
