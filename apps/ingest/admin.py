from django.contrib import admin

from apps.ingest.models import RawIngest, Submission


@admin.register(RawIngest)
class RawIngestAdmin(admin.ModelAdmin):
    list_display = ("source", "content_type", "fetched_at", "processed", "event")
    list_filter = ("processed", "source")
    search_fields = ("blob_ref",)
    date_hierarchy = "fetched_at"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "submitter_contact", "spam_score", "created_at")
    search_fields = ("submitter_contact", "notes")
