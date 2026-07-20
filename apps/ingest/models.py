from django.db import models

from apps.core.models import TimeStampedModel
from apps.events.models import Event
from apps.sources.models import Source


class RawIngest(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="raw_ingests")
    blob_ref = models.CharField(max_length=500)
    content_type = models.CharField(max_length=120, blank=True)
    fetched_at = models.DateTimeField()
    processed = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    event = models.ForeignKey(
        Event, on_delete=models.SET_NULL, null=True, blank=True, related_name="raw_ingests"
    )

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self):
        return f"RawIngest from {self.source} @ {self.fetched_at:%Y-%m-%d %H:%M}"


class Submission(TimeStampedModel):
    raw_ingest = models.ForeignKey(
        RawIngest, on_delete=models.CASCADE, null=True, blank=True, related_name="submissions"
    )
    submitter_contact = models.CharField(max_length=200, blank=True)
    spam_score = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission #{self.pk}"
