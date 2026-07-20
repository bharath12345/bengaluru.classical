import pytest
from django.utils import timezone

from apps.ingest.factories import RawIngestFactory, SubmissionFactory
from apps.ingest.models import RawIngest

pytestmark = pytest.mark.django_db


def test_raw_ingest_defaults():
    raw = RawIngestFactory()
    assert raw.processed == RawIngest.State.PENDING
    assert raw.event is None
    assert raw.source_id is not None


def test_raw_ingest_str_includes_source():
    raw = RawIngestFactory()
    assert str(raw.source) in str(raw)


def test_submission_links_to_raw_ingest():
    raw = RawIngestFactory()
    submission = SubmissionFactory(raw_ingest=raw)
    assert submission.raw_ingest_id == raw.id
    assert submission.spam_score == 0.0


def test_raw_ingest_fetched_at_is_timezone_aware():
    raw = RawIngestFactory(fetched_at=timezone.now())
    assert timezone.is_aware(raw.fetched_at)
