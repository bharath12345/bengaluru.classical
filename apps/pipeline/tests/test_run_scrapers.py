from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.ingest.models import RawIngest
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_run_scrapers_creates_raw_ingests():
    source = SourceFactory(type=Source.Type.FEED, active=True)

    with (
        patch(
            "apps.pipeline.management.commands.run_scrapers.FetcherRegistry.get_fetcher"
        ) as mock_get_fetcher,
        patch("apps.pipeline.management.commands.run_scrapers.upload_blob") as mock_upload,
    ):
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = [
            {"content": b"test", "content_type": "text/calendar", "url": source.url}
        ]
        mock_get_fetcher.return_value = mock_fetcher
        mock_upload.return_value = "gs://stub/123.bin"

        call_command("run_scrapers")

    assert RawIngest.objects.count() == 1
    raw = RawIngest.objects.first()
    assert raw.source_id == source.id
    assert raw.blob_ref == "gs://stub/123.bin"

    source.refresh_from_db()
    assert source.health_status == Source.Health.OK


def test_run_scrapers_skips_inactive_sources():
    SourceFactory(type=Source.Type.FEED, active=False)

    with patch(
        "apps.pipeline.management.commands.run_scrapers.FetcherRegistry.get_fetcher"
    ) as mock_get:
        mock_get.return_value = MagicMock()
        call_command("run_scrapers")
        mock_get.assert_not_called()
