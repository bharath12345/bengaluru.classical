from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.events.factories import EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_ics_feed_returns_icalendar_content(client: Client):
    EventFactory(status=Event.Status.PUBLISHED, start_at=timezone.now() + timedelta(days=1))
    response = client.get(reverse("web:ics_feed"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/calendar; charset=utf-8"
    assert b"BEGIN:VCALENDAR" in response.content
    assert b"BEGIN:VEVENT" in response.content


def test_ics_feed_filters_by_genre(client: Client):
    now = timezone.now()
    EventFactory(
        status=Event.Status.PUBLISHED,
        start_at=now + timedelta(days=1),
        genre=Event.Genre.KARNATIC,
        title="Karnatic Concert",
    )
    EventFactory(
        status=Event.Status.PUBLISHED,
        start_at=now + timedelta(days=2),
        genre=Event.Genre.HINDUSTANI,
        title="Hindustani Concert",
    )

    response = client.get(reverse("web:ics_feed"), {"genre": "karnatic"})
    content = response.content.decode()
    assert "Karnatic Concert" in content
    assert "Hindustani Concert" not in content


def test_ics_feed_includes_only_upcoming_published(client: Client):
    now = timezone.now()
    upcoming = EventFactory(
        status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1), title="Upcoming"
    )
    EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1), title="Past")
    EventFactory(status=Event.Status.REVIEW, start_at=now + timedelta(days=2), title="Review")

    response = client.get(reverse("web:ics_feed"))
    content = response.content.decode()
    assert upcoming.title in content
    assert "Past" not in content
    assert "Review" not in content
