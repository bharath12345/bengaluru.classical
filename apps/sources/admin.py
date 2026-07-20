from django.contrib import admin

from apps.sources.models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "health_status", "last_seen_at", "active", "seasonal")
    list_filter = ("type", "health_status", "active", "seasonal", "city")
    search_fields = ("name", "url", "handle")
    list_editable = ("active",)
