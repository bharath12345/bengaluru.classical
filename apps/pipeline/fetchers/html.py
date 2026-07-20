import httpx
from bs4 import BeautifulSoup

from apps.pipeline.fetchers.base import Fetcher, FetcherRegistry
from apps.sources.models import Source


class HTMLFetcher(Fetcher):
    """Fetches clean HTML and returns cleaned text for later LLM extraction."""

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return [
            {
                "content": text.encode("utf-8"),
                "content_type": "text/plain",
                "url": source.url,
            }
        ]


FetcherRegistry.register(Source.Type.HTML, "", HTMLFetcher)
