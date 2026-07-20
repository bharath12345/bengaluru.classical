from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.fetchers.ics import ICSFetcher
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_ics_fetcher_parses_ical_feed():
    with open(FIXTURE_DIR / "sample.ics", "rb") as f:
        ics_content = f.read()

    source = SourceFactory(type=Source.Type.FEED, url="https://example.com/calendar.ics")

    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = ics_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetcher = ICSFetcher()
        results = fetcher.fetch(source)

    assert len(results) == 1
    assert results[0]["content_type"] == "text/calendar"
    assert b"VCALENDAR" in results[0]["content"]
