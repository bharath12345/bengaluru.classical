from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.factories import SeriesFactory
from apps.events.factories import EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_end_to_end_flow(client: Client):
    now = timezone.now()
    series = SeriesFactory(slug="ramanavami")
    upcoming = EventFactory(
        status=Event.Status.PUBLISHED,
        start_at=now + timedelta(days=1),
        slug="upcoming-concert",
        series=series,
    )
    past = EventFactory(
        status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1), slug="past-concert"
    )

    response = client.get(reverse("web:event_list"))
    assert response.status_code == 200
    assert upcoming.title in response.content.decode()

    response = client.get(reverse("web:event_detail", args=[upcoming.slug]))
    assert response.status_code == 200
    assert "application/ld+json" in response.content.decode()

    response = client.get(reverse("web:archive"))
    assert response.status_code == 200
    assert past.title in response.content.decode()

    response = client.get(reverse("web:series_detail", args=[series.slug]))
    assert response.status_code == 200
    assert series.name in response.content.decode()

    response = client.get(reverse("web:ics_feed"))
    assert response.status_code == 200
    assert b"BEGIN:VCALENDAR" in response.content

    response = client.get("/sitemap-upcoming.xml")
    assert upcoming.slug in response.content.decode()
