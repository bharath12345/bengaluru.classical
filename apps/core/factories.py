import factory

from apps.core.models import Artist, City, Series, Venue


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f"City {n}")
    slug = factory.Sequence(lambda n: f"city-{n}")


class VenueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venue

    name = factory.Sequence(lambda n: f"Venue {n}")
    slug = factory.Sequence(lambda n: f"venue-{n}")
    city = factory.SubFactory(CityFactory)


class ArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Artist

    name = factory.Sequence(lambda n: f"Artist {n}")
    slug = factory.Sequence(lambda n: f"artist-{n}")
    alt_names = factory.LazyFunction(list)


class SeriesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Series

    name = factory.Sequence(lambda n: f"Series {n}")
    slug = factory.Sequence(lambda n: f"series-{n}")
    city = factory.SubFactory(CityFactory)
