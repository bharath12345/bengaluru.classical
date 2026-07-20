import pytest

from apps.pipeline.storage import upload_blob

pytestmark = pytest.mark.django_db


def test_upload_blob_returns_ref():
    blob_ref = upload_blob(b"test content", "text/plain")
    assert blob_ref  # local path or gs://stub
