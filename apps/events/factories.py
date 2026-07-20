import factory
from django.utils import timezone

from apps.core.factories import ArtistFactory, CityFactory, VenueFactory
from apps.events.models import Event, EventArtist


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    title = factory.Sequence(lambda n: f"Concert {n}")
    slug = factory.Sequence(lambda n: f"concert-{n}")
    genre = Event.Genre.KARNATIC
    start_at = factory.LazyFunction(timezone.now)
    venue = factory.SubFactory(VenueFactory)
    city = factory.SubFactory(CityFactory)


class EventArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventArtist

    event = factory.SubFactory(EventFactory)
    artist = factory.SubFactory(ArtistFactory)
    role = "vocal"
