"""Object storage abstraction: Google Cloud Storage in production, local folder in development."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Storage(Protocol):
    def upload(self, key: str, data: bytes, content_type: str) -> None: ...

    def signed_url(self, key: str, minutes: int) -> str: ...


class LocalStorage:
    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def signed_url(self, key: str, minutes: int) -> str:
        # Served by the /local-files static mount in app.main (development only)
        return f"/local-files/{key}"


class GCSStorage:
    def __init__(self, bucket_name: str) -> None:
        import google.auth
        from google.cloud import storage

        self._credentials, project = google.auth.default()
        self.client = storage.Client(credentials=self._credentials, project=project)
        self.bucket = self.client.bucket(bucket_name)

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        blob = self.bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)

    def signed_url(self, key: str, minutes: int) -> str:
        """V4 signed URL.

        Cloud Run credentials have no private key, so signing goes through the IAM
        signBlob API. That is why the runtime service account holds
        roles/iam.serviceAccountTokenCreator on itself (see infra/terraform/main.tf).
        """
        from google.auth.transport.requests import Request

        if not self._credentials.valid:
            self._credentials.refresh(Request())
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=minutes),
            method="GET",
            service_account_email=self._credentials.service_account_email,
            access_token=self._credentials.token,
        )


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.gcs_bucket:
        return GCSStorage(settings.gcs_bucket)
    return LocalStorage(settings.local_upload_dir)
