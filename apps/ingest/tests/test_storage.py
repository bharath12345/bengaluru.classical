import tempfile
from pathlib import Path

import pytest
from django.test import override_settings

from apps.ingest.storage import GCSBackend, LocalBackend, get_storage

pytestmark = pytest.mark.django_db


@override_settings(RAW_STORAGE_BACKEND="local")
def test_get_storage_returns_local_backend():
    backend = get_storage()
    assert isinstance(backend, LocalBackend)


@override_settings(RAW_STORAGE_BACKEND="gcs")
def test_get_storage_returns_gcs_backend():
    backend = get_storage()
    assert isinstance(backend, GCSBackend)


def test_local_backend_save_and_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(base_path=Path(tmpdir))
        content = b"test poster data"
        blob_ref = backend.save("poster.jpg", content, "image/jpeg")
        assert blob_ref.startswith("raw/")
        assert backend.exists(blob_ref)
        full_path = Path(tmpdir) / blob_ref
        assert full_path.read_bytes() == content


def test_local_backend_get_url():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(base_path=Path(tmpdir))
        blob_ref = backend.save("test.bin", b"data", "application/octet-stream")
        url = backend.get_url(blob_ref)
        assert blob_ref in url


def test_gcs_backend_instantiates_without_error():
    backend = GCSBackend(bucket_name="fake-bucket")
    assert backend.bucket_name == "fake-bucket"
