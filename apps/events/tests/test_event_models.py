from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.factories import EventArtistFactory, EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_event_defaults():
    event = EventFactory()
    assert event.status == Event.Status.REVIEW
    assert event.is_free is True
    assert event.currency == "INR"
    assert event.confidence == 0.0


def test_event_genre_choices():
    event = EventFactory(genre=Event.Genre.HINDUSTANI)
    assert event.genre == "hindustani"


def test_event_is_upcoming_true_for_future():
    event = EventFactory(start_at=timezone.now() + timedelta(days=3))
    assert event.is_upcoming is True


def test_event_is_upcoming_false_for_past():
    event = EventFactory(start_at=timezone.now() - timedelta(days=3))
    assert event.is_upcoming is False


def test_event_str_includes_title():
    event = EventFactory(title="Vidwan Concert")
    assert "Vidwan Concert" in str(event)


def test_event_artist_roles():
    event = EventFactory()
    EventArtistFactory(event=event, role="vocal")
    EventArtistFactory(event=event, role="mridangam")
    roles = sorted(ea.role for ea in event.event_artists.all())
    assert roles == ["mridangam", "vocal"]
    assert event.artists.count() == 2


def test_dedup_key_is_indexed():
    field = Event._meta.get_field("dedup_key")
    assert field.db_index is True
