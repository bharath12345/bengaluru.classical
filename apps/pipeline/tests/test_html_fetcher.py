from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.fetchers.html import HTMLFetcher
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_html_fetcher_extracts_text():
    with open(FIXTURE_DIR / "sample_html.html", "rb") as f:
        html_content = f.read()

    source = SourceFactory(type=Source.Type.HTML, url="https://example.com/schedule")

    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = html_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetcher = HTMLFetcher()
        results = fetcher.fetch(source)

    assert len(results) == 1
    assert results[0]["content_type"] == "text/plain"
    text = results[0]["content"].decode("utf-8")
    assert "Vidwan Concert" in text
    assert "var x" not in text
