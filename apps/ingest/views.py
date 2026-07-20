import base64
import json

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.ingest.models import RawIngest
from apps.ingest.storage import get_storage
from apps.sources.models import Source


@csrf_exempt
@require_http_methods(["POST"])
def inbound_email(request):
    """
    Receives raw MIME + attachments from Cloudflare Email Worker.
    Authenticated by shared secret in request body.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if payload.get("secret") != settings.INBOUND_EMAIL_SECRET:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    raw_mime = payload.get("raw_mime")
    attachments = payload.get("attachments", [])

    if not raw_mime:
        return JsonResponse({"error": "Missing raw_mime"}, status=400)

    email_source, _ = Source.objects.get_or_create(
        name="Forwarded email", defaults={"type": Source.Type.EMAIL}
    )

    storage = get_storage()
    now = timezone.now()

    mime_blob_ref = storage.save("email.eml", raw_mime.encode("utf-8"), "message/rfc822")
    RawIngest.objects.create(
        source=email_source,
        blob_ref=mime_blob_ref,
        content_type="message/rfc822",
        fetched_at=now,
    )

    for attachment in attachments:
        name = attachment.get("name", "attachment.bin")
        content_base64 = attachment.get("content_base64", "")
        content = base64.b64decode(content_base64)
        content_type = attachment.get("content_type", "application/octet-stream")
        blob_ref = storage.save(name, content, content_type)
        RawIngest.objects.create(
            source=email_source,
            blob_ref=blob_ref,
            content_type=content_type,
            fetched_at=now,
        )

    return JsonResponse({"status": "ok", "ingests_created": 1 + len(attachments)}, status=201)
