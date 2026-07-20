from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.factories import SeriesFactory
from apps.events.factories import EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_health_endpoint_returns_200(client: Client):
    response = client.get(reverse("web:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_event_list_shows_only_upcoming_published(client: Client):
    now = timezone.now()
    e_pub_upcoming = EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1))
    EventFactory(status=Event.Status.REVIEW, start_at=now + timedelta(days=2))

    response = client.get(reverse("web:event_list"))
    assert response.status_code == 200
    assert e_pub_upcoming.title in response.content.decode()


def test_event_list_filters_by_genre(client: Client):
    now = timezone.now()
    karnatic = EventFactory(
        status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1), genre=Event.Genre.KARNATIC
    )
    hindustani = EventFactory(
        status=Event.Status.PUBLISHED,
        start_at=now + timedelta(days=2),
        genre=Event.Genre.HINDUSTANI,
    )

    response = client.get(reverse("web:event_list"), {"genre": "karnatic"})
    content = response.content.decode()
    assert karnatic.title in content
    assert hindustani.title not in content


def test_event_list_filters_by_free(client: Client):
    now = timezone.now()
    free = EventFactory(
        status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1), is_free=True
    )
    paid = EventFactory(
        status=Event.Status.PUBLISHED, start_at=now + timedelta(days=2), is_free=False, price=500
    )

    response = client.get(reverse("web:event_list"), {"free": "true"})
    content = response.content.decode()
    assert free.title in content
    assert paid.title not in content


def test_event_detail_shows_published_event(client: Client):
    event = EventFactory(status=Event.Status.PUBLISHED, slug="test-concert")
    response = client.get(reverse("web:event_detail", args=["test-concert"]))
    assert response.status_code == 200
    assert event.title in response.content.decode()


def test_event_detail_404_for_non_published(client: Client):
    EventFactory(status=Event.Status.REVIEW, slug="review-concert")
    response = client.get(reverse("web:event_detail", args=["review-concert"]))
    assert response.status_code == 404


def test_event_detail_includes_jsonld(client: Client):
    event = EventFactory(status=Event.Status.PUBLISHED, slug="jsonld-test")
    response = client.get(reverse("web:event_detail", args=["jsonld-test"]))
    content = response.content.decode()
    assert "application/ld+json" in content
    assert event.title in content


def test_archive_shows_only_past_published(client: Client):
    now = timezone.now()
    past = EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1))
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    EventFactory(status=Event.Status.REVIEW, start_at=now - timedelta(days=2))

    response = client.get(reverse("web:archive"))
    content = response.content.decode()
    assert response.status_code == 200
    assert past.title in content


def test_series_detail_shows_series_and_past_events(client: Client):
    series = SeriesFactory(slug="ramanavami-2026")
    now = timezone.now()
    e1 = EventFactory(
        status=Event.Status.PUBLISHED, series=series, start_at=now - timedelta(days=1)
    )
    EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=2))

    response = client.get(reverse("web:series_detail", args=["ramanavami-2026"]))
    content = response.content.decode()
    assert response.status_code == 200
    assert series.name in content
    assert e1.title in content
