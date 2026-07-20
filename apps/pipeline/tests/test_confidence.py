import pytest

from apps.events.models import Event
from apps.pipeline.confidence import compute_confidence
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_high_confidence_feed_all_fields_no_collision():
    source = SourceFactory(type=Source.Type.FEED)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert confidence >= 0.8
    assert status == Event.Status.PUBLISHED


def test_low_confidence_html_source():
    source = SourceFactory(type=Source.Type.HTML)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert confidence < 0.8
    assert status == Event.Status.REVIEW


def test_low_confidence_missing_required_field():
    source = SourceFactory(type=Source.Type.FEED)
    candidate = {"title": "Concert", "genre": "karnatic"}
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert status == Event.Status.REVIEW


def test_low_confidence_dedup_collision():
    source = SourceFactory(type=Source.Type.FEED)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=True)
    assert status == Event.Status.REVIEW


def test_low_confidence_poster_or_form():
    source = SourceFactory(type=Source.Type.FORM)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert status == Event.Status.REVIEW
