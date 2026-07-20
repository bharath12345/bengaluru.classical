import json

import httpx
from bs4 import BeautifulSoup

from apps.pipeline.fetchers.base import Fetcher, FetcherRegistry
from apps.sources.models import Source


class JSONLDFetcher(Fetcher):
    """Fetches HTML and extracts embedded schema.org/Event JSON-LD blocks."""

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")
        scripts = soup.find_all("script", type="application/ld+json")

        results = []
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") == "Event":
                    results.append(
                        {
                            "content": json.dumps(data).encode("utf-8"),
                            "content_type": "application/ld+json",
                            "url": source.url,
                        }
                    )
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            results.append(
                                {
                                    "content": json.dumps(item).encode("utf-8"),
                                    "content_type": "application/ld+json",
                                    "url": source.url,
                                }
                            )
            except (json.JSONDecodeError, TypeError):
                continue

        return results


FetcherRegistry.register(Source.Type.JSONLD, "", JSONLDFetcher)
