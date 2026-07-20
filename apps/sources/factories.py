import factory

from apps.core.factories import CityFactory
from apps.sources.models import Source


class SourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Source

    name = factory.Sequence(lambda n: f"Source {n}")
    type = Source.Type.HTML
    city = factory.SubFactory(CityFactory)
