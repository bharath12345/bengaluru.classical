from django.db import models

from apps.core.models import City, TimeStampedModel


class Source(TimeStampedModel):
    class Type(models.TextChoices):
        FEED = "feed", "iCal/RSS feed"
        JSONLD = "jsonld", "Embedded JSON-LD"
        API = "api", "Open API"
        HTML = "html", "Clean HTML"
        JS = "js", "JS-rendered HTML"
        EMAIL = "email", "Inbound email"
        FORM = "form", "Public form"
        SOCIAL = "social", "Social media"

    class Health(models.TextChoices):
        OK = "ok", "OK"
        FAILING = "failing", "Failing"
        DEAD = "dead", "Dead"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=Type.choices)
    url = models.URLField(blank=True)
    handle = models.CharField(max_length=200, blank=True)
    scrape_method = models.CharField(max_length=120, blank=True)
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, null=True, blank=True, related_name="sources"
    )
    health_status = models.CharField(max_length=20, choices=Health.choices, default=Health.UNKNOWN)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    seasonal = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.type}]"

    def mark_seen(self, at):
        self.last_seen_at = at
        self.health_status = self.Health.OK
        self.save(update_fields=["last_seen_at", "health_status", "updated_at"])
