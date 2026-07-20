import pytest

from apps.core.factories import ArtistFactory, CityFactory, SeriesFactory, VenueFactory

pytestmark = pytest.mark.django_db


def test_city_str_and_slug_unique():
    city = CityFactory(name="Bengaluru", slug="bengaluru")
    assert str(city) == "Bengaluru"
    with pytest.raises(Exception):
        CityFactory(slug="bengaluru")


def test_venue_belongs_to_city_and_str():
    venue = VenueFactory(name="Chowdiah Memorial Hall")
    assert str(venue) == "Chowdiah Memorial Hall"
    assert venue.city_id is not None


def test_artist_alt_names_defaults_to_list():
    artist = ArtistFactory(name="T. M. Krishna", alt_names=[])
    assert artist.alt_names == []
    artist2 = ArtistFactory()
    assert isinstance(artist2.alt_names, list)


def test_series_belongs_to_city_and_str():
    series = SeriesFactory(name="Ramanavami Festival")
    assert str(series) == "Ramanavami Festival"
    assert series.city_id is not None


def test_timestamps_are_populated():
    city = CityFactory()
    assert city.created_at is not None
    assert city.updated_at is not None
