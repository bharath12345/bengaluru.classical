from django.contrib.sitemaps import Sitemap

from apps.core.models import Series
from apps.events.models import Event


class UpcomingEventsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Event.objects.upcoming()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/events/{obj.slug}/"


class ArchiveEventsSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Event.objects.past()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/events/{obj.slug}/"


class SeriesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Series.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/festivals/{obj.slug}/"
