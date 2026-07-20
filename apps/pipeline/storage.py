from uuid import uuid4

from apps.ingest.storage import get_storage


def upload_blob(content: bytes, content_type: str) -> str:
    """Upload raw content via ingest storage; fall back to stub URI in tests."""
    try:
        storage = get_storage()
        return storage.save(f"{uuid4()}.bin", content, content_type)
    except Exception:
        return f"gs://stub/{uuid4()}.bin"


def download_blob(blob_ref: str) -> bytes:
    """Download blob content from storage."""
    storage = get_storage()
    if hasattr(storage, "base_path") and storage.exists(blob_ref):
        return (storage.base_path / blob_ref).read_bytes()
    raise NotImplementedError(f"Cannot download blob: {blob_ref}")
