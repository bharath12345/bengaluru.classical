from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.core.factories import CityFactory
from apps.events.models import Event
from apps.ingest.factories import RawIngestFactory
from apps.ingest.models import RawIngest
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_process_raw_ingests_creates_event_from_candidate():
    city = CityFactory(slug="bengaluru")
    source = SourceFactory(type=Source.Type.FEED, city=city)
    raw = RawIngestFactory(source=source, processed=RawIngest.State.PENDING)

    candidate = {
        "title": "Karnatic Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00+05:30",
        "venue_name": "Test Hall",
        "artist_names": ["Artist A"],
    }

    with patch(
        "apps.pipeline.management.commands.process_raw_ingests.extract_candidate"
    ) as mock_extract:
        mock_extract.return_value = candidate
        call_command("process_raw_ingests")

    assert Event.objects.count() == 1
    event = Event.objects.first()
    assert event.title == "Karnatic Concert"
    assert event.status == Event.Status.PUBLISHED
    assert event.venue.name == "Test Hall"

    raw.refresh_from_db()
    assert raw.processed == RawIngest.State.PROCESSED
    assert raw.event_id == event.id


def test_process_raw_ingests_skips_already_processed():
    RawIngestFactory(processed=RawIngest.State.PROCESSED)

    with patch(
        "apps.pipeline.management.commands.process_raw_ingests.extract_candidate"
    ) as mock_extract:
        call_command("process_raw_ingests")
        mock_extract.assert_not_called()


def test_process_raw_ingests_sets_failed_on_error():
    raw = RawIngestFactory(processed=RawIngest.State.PENDING)

    with patch(
        "apps.pipeline.management.commands.process_raw_ingests.extract_candidate"
    ) as mock_extract:
        mock_extract.side_effect = Exception("Extraction failed")
        call_command("process_raw_ingests")

    raw.refresh_from_db()
    assert raw.processed == RawIngest.State.FAILED
