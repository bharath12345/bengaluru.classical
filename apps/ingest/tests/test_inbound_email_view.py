import base64
import json

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from apps.ingest.models import RawIngest
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_inbound_email_view_rejects_missing_secret(client: Client):
    response = client.post(
        reverse("ingest:inbound_email"),
        data=json.dumps({"raw_mime": "test"}),
        content_type="application/json",
    )
    assert response.status_code == 401


@override_settings(INBOUND_EMAIL_SECRET="test-secret")
def test_inbound_email_view_accepts_valid_post(client: Client):
    Source.objects.get_or_create(name="Forwarded email", defaults={"type": Source.Type.EMAIL})

    raw_mime = "From: test@example.com\r\nSubject: Concert poster\r\n\r\nBody text"
    payload = {
        "secret": "test-secret",
        "raw_mime": raw_mime,
        "attachments": [
            {
                "name": "poster.jpg",
                "content_base64": base64.b64encode(b"fake-image-data").decode(),
            }
        ],
    }
    response = client.post(
        reverse("ingest:inbound_email"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert RawIngest.objects.count() == 2


@override_settings(INBOUND_EMAIL_SECRET="test-secret")
def test_inbound_email_view_rejects_wrong_secret(client: Client):
    payload = {"secret": "wrong", "raw_mime": "test"}
    response = client.post(
        reverse("ingest:inbound_email"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 401
