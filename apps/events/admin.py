from django.contrib import admin

from apps.events.models import Event, EventArtist


class EventArtistInline(admin.TabularInline):
    model = EventArtist
    extra = 1
    autocomplete_fields = ("artist",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "start_at", "venue", "status", "confidence")
    list_filter = ("status", "genre", "city", "is_free")
    search_fields = ("title", "description", "venue__name")
    date_hierarchy = "start_at"
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("venue", "series", "city")
    inlines = [EventArtistInline]
    list_editable = ("status",)
    actions = ["publish_selected", "reject_selected"]

    @admin.action(description="Publish selected events")
    def publish_selected(self, request, queryset):
        queryset.update(status=Event.Status.PUBLISHED)

    @admin.action(description="Reject selected events")
    def reject_selected(self, request, queryset):
        queryset.update(status=Event.Status.REJECTED)
