import pytest
from django.test import Client

from apps.core.factories import SeriesFactory
from apps.events.factories import EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_sitemap_index_returns_xml(client: Client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert b"<sitemapindex" in response.content


def test_sitemap_upcoming_includes_published_events(client: Client):
    from datetime import timedelta

    from django.utils import timezone

    event = EventFactory(
        status=Event.Status.PUBLISHED,
        slug="test-event",
        start_at=timezone.now() + timedelta(days=1),
    )
    response = client.get("/sitemap-upcoming.xml")
    content = response.content.decode()
    assert response.status_code == 200
    assert event.slug in content


def test_sitemap_series_includes_all_series(client: Client):
    series = SeriesFactory(slug="test-series")
    response = client.get("/sitemap-series.xml")
    content = response.content.decode()
    assert response.status_code == 200
    assert series.slug in content
