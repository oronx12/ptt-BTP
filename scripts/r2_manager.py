# r2_manager.py
"""
Utilitaire CLI pour gérer les fichiers Excel dans Cloudflare R2.

Usage :
    python r2_manager.py list                              # Lister tous les fichiers
    python r2_manager.py upload <fichier.xlsx> <client_id> # Uploader pour un client
    python r2_manager.py download <client_id> [dest.xlsx]  # Télécharger vers local
    python r2_manager.py delete <client_id>                # Supprimer le modèle d'un client
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from app.services.r2_service import _get_client, upload_excel, download_excel
import os

BUCKET = os.environ.get("R2_BUCKET", "ptt-btp-models")


def cmd_list():
    """Liste tous les fichiers dans le bucket R2."""
    client = _get_client()
    response = client.list_objects_v2(Bucket=BUCKET)
    files = response.get("Contents", [])
    if not files:
        print("Bucket vide.")
        return
    print(f"Fichiers dans [{BUCKET}] :")
    for obj in sorted(files, key=lambda x: x["Key"]):
        size_kb = obj["Size"] / 1024
        print(f"  {obj['Key']:55s}  {size_kb:7.1f} Ko")
    print(f"\n{len(files)} fichier(s).")


def cmd_upload(local_path: str, client_id: str):
    """Upload un fichier Excel local vers R2 pour un client donné."""
    path = Path(local_path)
    if not path.exists():
        print(f"Erreur : fichier introuvable → {path}")
        sys.exit(1)
    r2_key = f"data/clients/{client_id}/modele.xlsx"
    print(f"Upload de {path.name} → R2:{r2_key} ...")
    upload_excel(path.read_bytes(), r2_key)
    print("Upload réussi !")
    print(f"N'oublie pas de mettre à jour excel_key du client {client_id} en base :")
    print(f"  UPDATE client SET excel_key='{r2_key}' WHERE id={client_id};")


def cmd_download(client_id: str, dest: str = None):
    """Télécharge le modèle Excel d'un client depuis R2."""
    r2_key = f"data/clients/{client_id}/modele.xlsx"
    dest_path = Path(dest) if dest else Path(f"modele_client_{client_id}.xlsx")
    print(f"Download R2:{r2_key} → {dest_path} ...")
    try:
        data = download_excel(r2_key)
        dest_path.write_bytes(data)
        print(f"Téléchargé : {dest_path}  ({len(data) / 1024:.1f} Ko)")
    except FileNotFoundError as e:
        print(f"Erreur : {e}")
        sys.exit(1)


def cmd_delete(client_id: str):
    """Supprime le modèle Excel d'un client dans R2."""
    r2_key = f"data/clients/{client_id}/modele.xlsx"
    confirm = input(f"Supprimer R2:{r2_key} ? (oui/non) : ").strip().lower()
    if confirm != "oui":
        print("Annulé.")
        return
    client = _get_client()
    client.delete_object(Bucket=BUCKET, Key=r2_key)
    print("Fichier supprimé.")


COMMANDS = {
    "list": (cmd_list, 0),
    "upload": (cmd_upload, 2),
    "download": (cmd_download, 1),
    "delete": (cmd_delete, 1),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0)

    cmd_name = sys.argv[1]
    func, min_args = COMMANDS[cmd_name]
    args = sys.argv[2:]

    if len(args) < min_args:
        print(f"Erreur : '{cmd_name}' attend {min_args} argument(s).")
        print(__doc__)
        sys.exit(1)

    func(*args)
