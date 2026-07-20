import httpx

from apps.pipeline.fetchers.base import Fetcher, FetcherRegistry
from apps.sources.models import Source


class APIFetcher(Fetcher):
    """Fetches open API/JSON endpoints and stores the raw response."""

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/json").split(";")[0]
        return [
            {
                "content": response.content,
                "content_type": content_type,
                "url": source.url,
            }
        ]


FetcherRegistry.register(Source.Type.API, "", APIFetcher)
