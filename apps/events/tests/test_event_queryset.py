from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.factories import EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_published_filters_only_published():
    EventFactory(status=Event.Status.PUBLISHED)
    EventFactory(status=Event.Status.REVIEW)
    EventFactory(status=Event.Status.REJECTED)
    assert Event.objects.published().count() == 1


def test_upcoming_filters_published_and_future():
    now = timezone.now()
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1))
    EventFactory(status=Event.Status.REVIEW, start_at=now + timedelta(days=2))
    assert Event.objects.upcoming().count() == 1


def test_past_filters_published_and_past():
    now = timezone.now()
    EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1))
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    EventFactory(status=Event.Status.REVIEW, start_at=now - timedelta(days=2))
    assert Event.objects.past().count() == 1


def test_upcoming_ordered_asc():
    now = timezone.now()
    e2 = EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=2))
    e1 = EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    upcoming = list(Event.objects.upcoming())
    assert upcoming == [e1, e2]


def test_past_ordered_desc():
    now = timezone.now()
    e1 = EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=1))
    e2 = EventFactory(status=Event.Status.PUBLISHED, start_at=now - timedelta(days=2))
    past = list(Event.objects.past())
    assert past == [e1, e2]


def test_manager_methods_are_chainable():
    now = timezone.now()
    EventFactory(
        status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1), genre=Event.Genre.KARNATIC
    )
    EventFactory(
        status=Event.Status.PUBLISHED,
        start_at=now + timedelta(days=2),
        genre=Event.Genre.HINDUSTANI,
    )
    karnatic = Event.objects.upcoming().filter(genre=Event.Genre.KARNATIC)
    assert karnatic.count() == 1
