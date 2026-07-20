from django.db import models
from django.utils import timezone

from apps.core.models import Artist, City, Series, TimeStampedModel, Venue


class Event(TimeStampedModel):
    class Genre(models.TextChoices):
        KARNATIC = "karnatic", "Karnatic"
        HINDUSTANI = "hindustani", "Hindustani"

    class Status(models.TextChoices):
        REVIEW = "review", "In review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    genre = models.CharField(max_length=20, choices=Genre.choices)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="events")
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    source_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    poster = models.ImageField(upload_to="posters/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REVIEW)
    confidence = models.FloatField(default=0.0)
    series = models.ForeignKey(
        Series, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    dedup_key = models.CharField(max_length=200, blank=True, db_index=True)
    artists = models.ManyToManyField(Artist, through="EventArtist", related_name="events")

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["genre", "start_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_at:%Y-%m-%d})"

    @property
    def is_upcoming(self):
        return self.start_at >= timezone.now()


class EventArtist(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_artists")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="event_artists")
    role = models.CharField(max_length=80)

    class Meta:
        unique_together = ("event", "artist", "role")

    def __str__(self):
        return f"{self.artist} — {self.role}"
