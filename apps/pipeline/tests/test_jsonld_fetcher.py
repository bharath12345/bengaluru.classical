import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.fetchers.jsonld import JSONLDFetcher
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_jsonld_fetcher_extracts_event():
    with open(FIXTURE_DIR / "sample_jsonld.html", "rb") as f:
        html_content = f.read()

    source = SourceFactory(type=Source.Type.JSONLD, url="https://example.com/events/")

    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = html_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetcher = JSONLDFetcher()
        results = fetcher.fetch(source)

    assert len(results) == 1
    assert results[0]["content_type"] == "application/ld+json"
    data = json.loads(results[0]["content"])
    assert data["@type"] == "Event"
    assert data["name"] == "Hindustani Vocal Recital"
