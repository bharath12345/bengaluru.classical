from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class City(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "cities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Venue(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    area = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    map_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="venues")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Artist(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    alt_names = models.JSONField(default=list, blank=True)
    primary_role = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Series(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="series")

    class Meta:
        verbose_name_plural = "series"
        ordering = ["name"]

    def __str__(self):
        return self.name
