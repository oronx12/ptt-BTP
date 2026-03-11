# app/services/r2_service.py
"""
Service Cloudflare R2 (compatible S3) via boto3.
Fournit upload et download des fichiers Excel modèles des clients.
"""
import os
import boto3
from botocore.exceptions import ClientError


def _get_client():
    """Crée et retourne un client boto3 connecté à Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("R2_ENDPOINT"),
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def upload_excel(file_bytes: bytes, r2_key: str) -> None:
    """
    Upload un fichier Excel (bytes) vers R2 sous la clé r2_key.
    Exemple : upload_excel(data, "clients/3/modele.xlsx")
    Lève une exception boto3 en cas d'échec.
    """
    bucket = os.environ.get("R2_BUCKET", "ptt-btp-models")
    client = _get_client()
    client.put_object(
        Bucket=bucket,
        Key=r2_key,
        Body=file_bytes,
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def upload_fiche(content: bytes, r2_key: str) -> None:
    """Upload une fiche de réception (HTML) vers R2."""
    bucket = os.environ.get("R2_BUCKET", "ptt-btp-models")
    client = _get_client()
    client.put_object(
        Bucket=bucket,
        Key=r2_key,
        Body=content,
        ContentType="text/html; charset=utf-8",
    )


def generate_presigned_url(r2_key: str, expires_in: int = 3600) -> str:
    """Génère une URL signée temporaire (1h) pour accéder à un fichier R2."""
    bucket = os.environ.get("R2_BUCKET", "ptt-btp-models")
    client = _get_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": r2_key},
        ExpiresIn=expires_in,
    )


def download_excel(r2_key: str) -> bytes:
    """
    Télécharge un fichier Excel depuis R2 et retourne son contenu en bytes.
    Lève FileNotFoundError si la clé n'existe pas dans le bucket.
    """
    bucket = os.environ.get("R2_BUCKET", "ptt-btp-models")
    client = _get_client()
    try:
        response = client.get_object(Bucket=bucket, Key=r2_key)
        return response["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            raise FileNotFoundError(f"Fichier R2 introuvable : {r2_key}") from e
        raise
