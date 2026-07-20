import pytest

from apps.pipeline.fetchers.base import Fetcher, FetcherRegistry
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


class DummyFetcher(Fetcher):
    def fetch(self, source):
        return [{"content": b"dummy", "content_type": "text/plain", "url": source.url}]


def test_registry_get_fetcher_by_type():
    FetcherRegistry.register(Source.Type.SOCIAL, "dummy", DummyFetcher)
    source = SourceFactory(type=Source.Type.SOCIAL, scrape_method="dummy")
    fetcher = FetcherRegistry.get_fetcher(source)
    assert isinstance(fetcher, DummyFetcher)


def test_registry_returns_none_when_no_match():
    # Clear any accidental SOCIAL registration from other tests by using unique method
    source = SourceFactory(type=Source.Type.SOCIAL, scrape_method="unregistered-xyz")
    fetcher = FetcherRegistry.get_fetcher(source)
    assert fetcher is None
