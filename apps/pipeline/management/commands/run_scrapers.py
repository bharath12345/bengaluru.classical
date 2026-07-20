from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ingest.models import RawIngest
from apps.pipeline.fetchers.base import FetcherRegistry
from apps.pipeline.storage import upload_blob
from apps.sources.models import Source


class Command(BaseCommand):
    help = "Run scrapers for all active sources (Cloud Run Job entrypoint)."

    def handle(self, *args, **options):
        sources = Source.objects.filter(active=True)
        self.stdout.write(f"Running scrapers for {sources.count()} active sources...")

        for source in sources:
            self.stdout.write(f"Processing source: {source.name} [{source.type}]")

            fetcher = FetcherRegistry.get_fetcher(source)
            if not fetcher:
                self.stdout.write(self.style.WARNING(f"  No fetcher registered for {source.type}"))
                continue

            try:
                results = fetcher.fetch(source)
                now = timezone.now()

                for result in results:
                    blob_ref = upload_blob(result["content"], result["content_type"])
                    RawIngest.objects.create(
                        source=source,
                        blob_ref=blob_ref,
                        content_type=result["content_type"],
                        fetched_at=now,
                    )
                    self.stdout.write(f"  Created RawIngest: {blob_ref}")

                source.mark_seen(now)
                self.stdout.write(self.style.SUCCESS(f"  Success: {len(results)} artifacts"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))
                source.health_status = Source.Health.FAILING
                source.save(update_fields=["health_status", "updated_at"])
