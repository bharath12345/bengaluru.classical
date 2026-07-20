import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings


class BaseStorageBackend(ABC):
    """Abstract storage backend for raw ingest artifacts."""

    @abstractmethod
    def save(self, name: str, content: bytes, content_type: str) -> str:
        """Save content and return a blob_ref (opaque identifier)."""

    @abstractmethod
    def exists(self, blob_ref: str) -> bool:
        """Check if the blob_ref exists."""

    @abstractmethod
    def get_url(self, blob_ref: str) -> str:
        """Return a URL (signed or file://) for the blob."""


class LocalBackend(BaseStorageBackend):
    """Local filesystem backend for dev/test."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(settings.MEDIA_ROOT)

    def save(self, name: str, content: bytes, content_type: str) -> str:
        now = datetime.now()
        hash_prefix = hashlib.sha256(content).hexdigest()[:8]
        safe_name = Path(name).name
        rel_path = (
            Path("raw") / f"{now.year:04d}" / f"{now.month:02d}" / f"{hash_prefix}-{safe_name}"
        )
        full_path = self.base_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return str(rel_path)

    def exists(self, blob_ref: str) -> bool:
        return (self.base_path / blob_ref).exists()

    def get_url(self, blob_ref: str) -> str:
        return f"{settings.MEDIA_URL}{blob_ref}"


class GCSBackend(BaseStorageBackend):
    """Google Cloud Storage backend for prod."""

    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name or settings.RAW_STORAGE_GCS_BUCKET
        self._client = None
        self._bucket = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import storage

            self._client = storage.Client()
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def save(self, name: str, content: bytes, content_type: str) -> str:
        now = datetime.now()
        hash_prefix = hashlib.sha256(content).hexdigest()[:8]
        safe_name = Path(name).name
        blob_path = f"raw/{now.year:04d}/{now.month:02d}/{hash_prefix}-{safe_name}"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{self.bucket_name}/{blob_path}"

    def exists(self, blob_ref: str) -> bool:
        if not blob_ref.startswith(f"gs://{self.bucket_name}/"):
            return False
        path = blob_ref.replace(f"gs://{self.bucket_name}/", "")
        return self.bucket.blob(path).exists()

    def get_url(self, blob_ref: str) -> str:
        path = blob_ref.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        return blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")


def get_storage() -> BaseStorageBackend:
    """Return the configured storage backend."""
    backend = settings.RAW_STORAGE_BACKEND
    if backend == "local":
        return LocalBackend()
    if backend == "gcs":
        return GCSBackend()
    raise ValueError(f"Unknown RAW_STORAGE_BACKEND: {backend}")
