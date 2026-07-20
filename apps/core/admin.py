from django.contrib import admin

from apps.core.models import Artist, City, Series, Venue


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "city")
    list_filter = ("city",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "area", "address")


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "primary_role")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    list_filter = ("city",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
