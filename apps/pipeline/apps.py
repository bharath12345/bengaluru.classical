from django.apps import AppConfig


class PipelineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pipeline"
    label = "pipeline"

    def ready(self):
        # Register fetchers on app load
        from apps.pipeline.fetchers import api as _api  # noqa: F401
        from apps.pipeline.fetchers import html as _html  # noqa: F401
        from apps.pipeline.fetchers import ics as _ics  # noqa: F401
        from apps.pipeline.fetchers import jsonld as _jsonld  # noqa: F401
