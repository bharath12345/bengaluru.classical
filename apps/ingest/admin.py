from django.contrib import admin
from django.utils.html import format_html

from apps.ingest.models import RawIngest, Submission


@admin.register(RawIngest)
class RawIngestAdmin(admin.ModelAdmin):
    list_display = ("source", "content_type", "fetched_at", "processed", "event", "blob_link")
    list_filter = ("processed", "source", "content_type")
    search_fields = ("blob_ref",)
    date_hierarchy = "fetched_at"
    readonly_fields = ("blob_ref", "fetched_at", "created_at", "updated_at")

    @admin.display(description="Artifact")
    def blob_link(self, obj):
        if obj.blob_ref:
            return format_html('<a href="#" title="{}">📎 blob</a>', obj.blob_ref)
        return "—"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "submitter_contact", "spam_score", "raw_ingest", "created_at")
    list_filter = ("spam_score", "created_at")
    search_fields = ("submitter_contact", "notes")
    readonly_fields = ("raw_ingest", "created_at", "updated_at")
    fields = ("raw_ingest", "submitter_contact", "spam_score", "notes", "created_at", "updated_at")
