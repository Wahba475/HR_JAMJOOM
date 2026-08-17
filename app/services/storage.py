"""Save/read CV PDFs against Neon Object Storage (S3-compatible).

Swap this file later for a different backend — nothing outside it changes,
callers only ever deal in storage_path strings.
"""

import os

import boto3

from app.config import BUCKET_NAME

# Endpoint + credentials come from env (standard boto3 var names), picked
# up automatically. Region needs an explicit pass — matches Neon's own docs.
_client = boto3.client("s3", region_name=os.environ["AWS_REGION"])


def _key(run_id: str, candidate_id: str) -> str:
    return f"cv-uploads/{run_id}/{candidate_id}.pdf"


def save_cv(run_id: str, candidate_id: str, file_bytes: bytes) -> str:
    """Upload one CV PDF, return its storage path (the S3 key)."""
    key = _key(run_id, candidate_id)
    _client.put_object(Bucket=BUCKET_NAME, Key=key, Body=file_bytes, ContentType="application/pdf")
    return key


def read_cv(storage_path: str) -> bytes:
    """Fetch one CV PDF's bytes back out."""
    obj = _client.get_object(Bucket=BUCKET_NAME, Key=storage_path)
    return obj["Body"].read()


def get_view_url(storage_path: str, expires_in: int = 3600) -> str:
    """Presigned URL for the results page's View/Download buttons."""
    return _client.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET_NAME, "Key": storage_path}, ExpiresIn=expires_in
    )
