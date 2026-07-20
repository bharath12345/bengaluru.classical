from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.factories import ArtistFactory, VenueFactory
from apps.events.factories import EventArtistFactory, EventFactory
from apps.events.models import Event
from apps.mcp.schemas import SearchEventsInput
from apps.mcp.server import get_event, list_artists, list_venues, search_events

pytestmark = pytest.mark.django_db


def test_search_events_returns_only_published():
    EventFactory(status=Event.Status.PUBLISHED, title="Published Concert")
    EventFactory(status=Event.Status.REVIEW, title="Review Concert")
    EventFactory(status=Event.Status.REJECTED, title="Rejected Concert")

    results = search_events(SearchEventsInput())
    assert len(results) == 1
    assert results[0].title == "Published Concert"


def test_search_events_filters_by_genre():
    EventFactory(status=Event.Status.PUBLISHED, genre=Event.Genre.KARNATIC)
    EventFactory(status=Event.Status.PUBLISHED, genre=Event.Genre.HINDUSTANI)

    results = search_events(SearchEventsInput(genre="karnatic"))
    assert len(results) == 1
    assert results[0].genre == "karnatic"


def test_search_events_filters_by_date_range():
    now = timezone.now()
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=10))

    start = (now + timedelta(days=1)).date().isoformat()
    end = (now + timedelta(days=5)).date().isoformat()
    results = search_events(SearchEventsInput(date_range=f"{start}:{end}"))
    assert len(results) == 1


def test_search_events_filters_by_venue_name():
    venue1 = VenueFactory(name="Chowdiah Hall")
    venue2 = VenueFactory(name="Sri Rama Mandira")
    EventFactory(status=Event.Status.PUBLISHED, venue=venue1)
    EventFactory(status=Event.Status.PUBLISHED, venue=venue2)

    results = search_events(SearchEventsInput(venue="Chowdiah"))
    assert len(results) == 1
    assert results[0].venue == "Chowdiah Hall"


def test_search_events_filters_by_artist_name():
    artist1 = ArtistFactory(name="T. M. Krishna")
    artist2 = ArtistFactory(name="Bombay Jayashri")
    event1 = EventFactory(status=Event.Status.PUBLISHED)
    event2 = EventFactory(status=Event.Status.PUBLISHED)
    EventArtistFactory(event=event1, artist=artist1, role="vocal")
    EventArtistFactory(event=event2, artist=artist2, role="vocal")

    results = search_events(SearchEventsInput(artist="Krishna"))
    assert len(results) == 1
    assert results[0].artists[0]["name"] == "T. M. Krishna"


def test_search_events_filters_by_area():
    venue1 = VenueFactory(area="Jayanagar")
    venue2 = VenueFactory(area="Vyalikaval")
    EventFactory(status=Event.Status.PUBLISHED, venue=venue1)
    EventFactory(status=Event.Status.PUBLISHED, venue=venue2)

    results = search_events(SearchEventsInput(area="Jayanagar"))
    assert len(results) == 1
    assert results[0].area == "Jayanagar"


def test_get_event_returns_published_event():
    event = EventFactory(status=Event.Status.PUBLISHED, title="Concert")
    result = get_event(event.id)
    assert result is not None
    assert result.title == "Concert"


def test_get_event_returns_none_for_unpublished():
    event = EventFactory(status=Event.Status.REVIEW, title="Review Concert")
    result = get_event(event.id)
    assert result is None


def test_get_event_returns_none_for_nonexistent():
    result = get_event(99999)
    assert result is None


def test_list_venues_returns_all_venues():
    VenueFactory(name="Venue A")
    VenueFactory(name="Venue B")
    results = list_venues()
    assert len(results) == 2
    assert results[0].name in ["Venue A", "Venue B"]


def test_list_artists_returns_all_artists():
    ArtistFactory(name="Artist A")
    ArtistFactory(name="Artist B")
    results = list_artists()
    assert len(results) == 2
    assert results[0].name in ["Artist A", "Artist B"]
