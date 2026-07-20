import pytest

from apps.core.factories import ArtistFactory, CityFactory, VenueFactory
from apps.events.factories import EventFactory
from apps.pipeline.dedup import (
    compute_dedup_key,
    find_duplicate_event,
    find_or_create_artist,
    find_or_create_venue,
    fuzzy_ratio,
)

pytestmark = pytest.mark.django_db


def test_compute_dedup_key():
    key = compute_dedup_key("2026-08-10", "City Hall", ["Artist A", "Artist B"])
    assert key == "20260810|city-hall|artist-a_artist-b"


def test_find_or_create_venue_exact_match():
    city = CityFactory()
    venue = VenueFactory(name="Chowdiah Hall", city=city)
    found = find_or_create_venue("Chowdiah Hall", city)
    assert found.id == venue.id


def test_find_or_create_venue_fuzzy_match():
    city = CityFactory()
    venue = VenueFactory(name="Chowdiah Memorial Hall", city=city)
    # Ensure names are similar enough
    assert fuzzy_ratio("Chowdiah Memorial Hall", "Chowdiah Memorial Hal") >= 0.85
    found = find_or_create_venue("Chowdiah Memorial Hal", city)
    assert found.id == venue.id


def test_find_or_create_venue_creates_when_no_match():
    city = CityFactory()
    VenueFactory(name="Hall A", city=city)
    new_venue = find_or_create_venue("Hall B", city)
    assert new_venue.name == "Hall B"


def test_find_or_create_artist_fuzzy_match():
    artist = ArtistFactory(name="T M Krishna")
    found = find_or_create_artist("T M Krishn")  # high ratio
    assert found.id == artist.id


def test_find_or_create_artist_alt_names_match():
    artist = ArtistFactory(name="Sanjay Subrahmanyan", alt_names=["Sanjay"])
    found = find_or_create_artist("Sanjay")
    assert found.id == artist.id


def test_find_duplicate_event_by_dedup_key():
    event = EventFactory(dedup_key="20260810|hall|artist")
    found = find_duplicate_event("20260810|hall|artist")
    assert found.id == event.id


def test_find_duplicate_event_returns_none_when_no_match():
    found = find_duplicate_event("nonexistent_key")
    assert found is None
