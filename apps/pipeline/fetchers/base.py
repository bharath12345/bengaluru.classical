from abc import ABC, abstractmethod


class Fetcher(ABC):
    """Base interface for all source fetchers."""

    @abstractmethod
    def fetch(self, source):
        """
        Fetch raw content from the given Source.
        Returns: list[dict] with keys content, content_type, url.
        """


class FetcherRegistry:
    """Singleton registry mapping (source.type, scrape_method) -> Fetcher class."""

    _registry = {}

    @classmethod
    def register(cls, source_type, scrape_method, fetcher_class):
        key = (source_type, scrape_method)
        cls._registry[key] = fetcher_class

    @classmethod
    def get_fetcher(cls, source):
        key = (source.type, source.scrape_method)
        fetcher_class = cls._registry.get(key)
        if fetcher_class is None:
            # Fall back to type with empty scrape_method
            fetcher_class = cls._registry.get((source.type, ""))
        return fetcher_class() if fetcher_class else None
