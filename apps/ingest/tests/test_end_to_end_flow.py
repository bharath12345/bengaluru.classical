import base64
import json

import pytest
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse

from apps.ingest.models import RawIngest, Submission
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


@override_settings(INBOUND_EMAIL_SECRET="e2e-secret")
def test_end_to_end_form_submission_and_email_ingest(client: Client, mocker):
    mocker.patch("apps.web.views.check_rate_limit", return_value=True)

    Source.objects.get_or_create(name="Public submission form", defaults={"type": Source.Type.FORM})
    Source.objects.get_or_create(name="Forwarded email", defaults={"type": Source.Type.EMAIL})

    form_response = client.post(
        reverse("web:submit"),
        data={"title": "E2E Concert", "genre": "karnatic", "submitter_contact": "e2e@test.com"},
    )
    assert form_response.status_code == 302
    assert Submission.objects.count() == 1
    assert len(mail.outbox) == 1

    raw_mime = "From: forward@example.com\r\nSubject: Concert\r\n\r\nBody"
    email_payload = {
        "secret": "e2e-secret",
        "raw_mime": raw_mime,
        "attachments": [
            {"name": "poster.jpg", "content_base64": base64.b64encode(b"poster-bytes").decode()}
        ],
    }
    email_response = client.post(
        reverse("ingest:inbound_email"),
        data=json.dumps(email_payload),
        content_type="application/json",
    )
    assert email_response.status_code == 201

    assert RawIngest.objects.count() == 3
    form_ingest = RawIngest.objects.filter(source__type=Source.Type.FORM).first()
    email_ingest = RawIngest.objects.filter(
        source__type=Source.Type.EMAIL, content_type="message/rfc822"
    ).first()
    assert form_ingest is not None
    assert email_ingest is not None
