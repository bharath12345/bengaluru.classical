import factory
from django.utils import timezone

from apps.ingest.models import RawIngest, Submission
from apps.sources.factories import SourceFactory


class RawIngestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RawIngest

    source = factory.SubFactory(SourceFactory)
    blob_ref = factory.Sequence(lambda n: f"gs://blr-classical/raw/{n}.bin")
    fetched_at = factory.LazyFunction(timezone.now)


class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    raw_ingest = factory.SubFactory(RawIngestFactory)
