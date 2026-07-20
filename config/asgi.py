import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

django_asgi = get_asgi_application()

# Compose with FastMCP under /mcp (Plan 5)
from apps.mcp.asgi import build_asgi_application  # noqa: E402

application = build_asgi_application(django_asgi)
