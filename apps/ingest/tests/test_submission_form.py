import pytest

from apps.ingest.forms import SubmissionForm

pytestmark = pytest.mark.django_db


def test_submission_form_requires_poster_or_title():
    form = SubmissionForm(data={})
    assert not form.is_valid()
    assert "either a poster image or event details" in str(form.errors)


def test_submission_form_honeypot_rejects_spam():
    form = SubmissionForm(data={"title": "Concert", "honeypot": "bot-value"})
    assert not form.is_valid()
    assert "Spam detected" in str(form.errors)


def test_submission_form_valid_with_title():
    form = SubmissionForm(data={"title": "Vidwan Concert", "genre": "karnatic"})
    assert form.is_valid()
