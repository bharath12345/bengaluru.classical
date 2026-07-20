from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from apps.events.models import Event, EventArtist
from apps.ingest.models import RawIngest
from apps.pipeline.confidence import compute_confidence
from apps.pipeline.dedup import (
    compute_dedup_key,
    find_duplicate_event,
    find_or_create_artist,
    find_or_create_venue,
)


def extract_candidate(raw_ingest: RawIngest) -> dict:
    """
    Extract structured candidate dict from RawIngest.
    Stub — real Gemini extraction is wired via extractors; tests mock this.
    """
    raise NotImplementedError("Real extraction via Gemini deferred to per-fetcher logic")


class Command(BaseCommand):
    help = "Process pending RawIngest rows: extract, dedup, gate, publish."

    def handle(self, *args, **options):
        pending = RawIngest.objects.filter(processed=RawIngest.State.PENDING)
        self.stdout.write(f"Processing {pending.count()} pending RawIngest rows...")

        for raw in pending:
            self.stdout.write(f"Processing RawIngest #{raw.id} from {raw.source.name}")

            try:
                candidate = extract_candidate(raw)

                city = raw.source.city
                if city is None:
                    from apps.core.models import City

                    city = City.objects.filter(slug="bengaluru").first()
                    if city is None:
                        raise ValueError("No city available for event")

                venue = find_or_create_venue(candidate["venue_name"], city)
                artist_names = candidate.get("artist_names", [])
                artists = [find_or_create_artist(name) for name in artist_names]

                date_str = candidate["start_at"][:10]
                dedup_key = compute_dedup_key(date_str, venue.name, artist_names)

                existing = find_duplicate_event(dedup_key)
                dedup_collision = existing is not None

                confidence, status = compute_confidence(candidate, raw.source, dedup_collision)

                if existing:
                    self.stdout.write(f"  Duplicate detected: {existing.id}")
                    event = existing
                else:
                    slug = slugify(candidate["title"]) or "event"
                    base_slug = slug
                    counter = 1
                    while Event.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1

                    start_at = parse_datetime(candidate["start_at"])
                    if start_at is None:
                        start_at = datetime.fromisoformat(candidate["start_at"])
                    if timezone.is_naive(start_at):
                        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())

                    event = Event.objects.create(
                        title=candidate["title"],
                        slug=slug,
                        genre=candidate["genre"],
                        start_at=start_at,
                        venue=venue,
                        city=city,
                        source_url=candidate.get("source_url", raw.source.url or ""),
                        description=candidate.get("description", ""),
                        status=status,
                        confidence=confidence,
                        dedup_key=dedup_key,
                    )

                    for artist in artists:
                        EventArtist.objects.create(
                            event=event,
                            artist=artist,
                            role=candidate.get("role", "performer"),
                        )

                    self.stdout.write(
                        self.style.SUCCESS(f"  Created Event #{event.id}: {event.title}")
                    )

                raw.processed = RawIngest.State.PROCESSED
                raw.event = event
                raw.save(update_fields=["processed", "event", "updated_at"])

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))
                raw.processed = RawIngest.State.FAILED
                raw.save(update_fields=["processed", "updated_at"])
