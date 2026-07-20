import httpx

from apps.pipeline.fetchers.base import Fetcher, FetcherRegistry
from apps.sources.models import Source


class ICSFetcher(Fetcher):
    """Fetches and returns raw iCal/.ics feed content."""

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return [
            {
                "content": response.content,
                "content_type": "text/calendar",
                "url": source.url,
            }
        ]


FetcherRegistry.register(Source.Type.FEED, "", ICSFetcher)
