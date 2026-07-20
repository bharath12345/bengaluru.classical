import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse

from apps.ingest.models import RawIngest, Submission
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_submit_form_get_renders(client: Client):
    response = client.get(reverse("web:submit"))
    assert response.status_code == 200
    assert "Submit an Event" in response.content.decode()


def test_submit_form_post_creates_rawingest_and_submission(client: Client, mocker):
    mocker.patch("apps.web.views.check_rate_limit", return_value=True)
    Source.objects.get_or_create(name="Public submission form", defaults={"type": Source.Type.FORM})

    response = client.post(
        reverse("web:submit"),
        data={
            "title": "Test Concert",
            "genre": "karnatic",
            "submitter_contact": "test@example.com",
        },
    )
    assert response.status_code == 302
    assert RawIngest.objects.count() == 1
    assert Submission.objects.count() == 1
    assert len(mail.outbox) == 1
    assert "New submission" in mail.outbox[0].subject


def test_submit_form_rate_limited(client: Client, mocker):
    mocker.patch("apps.web.views.check_rate_limit", return_value=False)
    response = client.post(reverse("web:submit"), data={"title": "Concert"})
    assert response.status_code == 429
    assert "Too many requests" in response.content.decode()
