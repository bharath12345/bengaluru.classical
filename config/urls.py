from pathlib import Path

from django.contrib import admin
from django.contrib.sitemaps.views import index as sitemap_index
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.static import serve

from apps.web.sitemaps import ArchiveEventsSitemap, SeriesSitemap, UpcomingEventsSitemap

BASE_DIR = Path(__file__).resolve().parent.parent

sitemaps = {
    "upcoming": UpcomingEventsSitemap,
    "archive": ArchiveEventsSitemap,
    "series": SeriesSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "robots.txt",
        serve,
        {"path": "robots.txt", "document_root": str(BASE_DIR / "app" / "static")},
    ),
    path(
        "llms.txt",
        serve,
        {"path": "llms.txt", "document_root": str(BASE_DIR / "app" / "static")},
    ),
    path("sitemap.xml", sitemap_index, {"sitemaps": sitemaps}),
    path(
        "sitemap-<section>.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("apps.web.urls")),
]
