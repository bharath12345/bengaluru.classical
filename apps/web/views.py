import json
from itertools import groupby

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.models import Series
from apps.events.models import Event
from apps.ingest.forms import SubmissionForm
from apps.ingest.models import RawIngest, Submission
from apps.ingest.rate_limit import check_rate_limit
from apps.ingest.storage import get_storage
from apps.sources.models import Source


def health(request):
    """Health check endpoint for Cloud Run readiness/liveness probes."""
    return JsonResponse({"status": "ok"})


def event_list(request):
    events = Event.objects.upcoming()

    genre = request.GET.get("genre")
    if genre:
        events = events.filter(genre=genre)

    free = request.GET.get("free")
    if free == "true":
        events = events.filter(is_free=True)

    area = request.GET.get("area")
    if area:
        events = events.filter(venue__area__icontains=area)

    template = (
        "web/partials/event_list_results.html"
        if request.headers.get("HX-Request")
        else "web/event_list.html"
    )

    return render(request, template, {"events": events, "filters": request.GET})


def event_detail(request, slug):
    event = get_object_or_404(Event.objects.published(), slug=slug)

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": event.title,
        "startDate": event.start_at.isoformat(),
        "eventStatus": (
            "https://schema.org/EventScheduled"
            if event.status == Event.Status.PUBLISHED
            else "https://schema.org/EventCancelled"
        ),
        "location": {
            "@type": "Place",
            "name": event.venue.name,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": event.city.name,
                "addressRegion": "Karnataka",
                "addressCountry": "IN",
                "streetAddress": event.venue.address or event.venue.area,
            },
        },
    }

    if event.end_at:
        jsonld["endDate"] = event.end_at.isoformat()

    if event.event_artists.exists():
        jsonld["performer"] = [
            {"@type": "Person", "name": ea.artist.name} for ea in event.event_artists.all()
        ]

    if event.is_free:
        jsonld["isAccessibleForFree"] = True
    elif event.price:
        jsonld["offers"] = {
            "@type": "Offer",
            "price": str(event.price),
            "priceCurrency": event.currency,
            "url": event.source_url or "",
        }

    if event.poster:
        jsonld["image"] = request.build_absolute_uri(event.poster.url)

    if event.description:
        jsonld["description"] = event.description

    return render(
        request,
        "web/event_detail.html",
        {"event": event, "jsonld": json.dumps(jsonld, indent=2)},
    )


def calendar_view(request):
    events = Event.objects.upcoming()

    events_by_date = {}
    for date, group in groupby(events, key=lambda e: e.start_at.date()):
        events_by_date[date] = list(group)

    return render(request, "web/calendar.html", {"events_by_date": events_by_date})


def archive_view(request):
    events = Event.objects.past()
    return render(request, "web/archive.html", {"events": events})


def series_detail(request, slug):
    series = get_object_or_404(Series, slug=slug)
    events = Event.objects.published().filter(series=series).order_by("-start_at")
    return render(request, "web/series_detail.html", {"series": series, "events": events})


@require_http_methods(["GET", "POST"])
def submit_form(request):
    if request.method == "POST":
        if not check_rate_limit(request):
            return HttpResponse("Too many requests. Please try again later.", status=429)

        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            form_source, _ = Source.objects.get_or_create(
                name="Public submission form", defaults={"type": Source.Type.FORM}
            )

            poster_blob_ref = None
            if form.cleaned_data.get("poster"):
                storage = get_storage()
                poster_file = form.cleaned_data["poster"]
                poster_content = poster_file.read()
                poster_blob_ref = storage.save(
                    poster_file.name,
                    poster_content,
                    poster_file.content_type or "image/jpeg",
                )

            submission_data = {
                "title": form.cleaned_data.get("title"),
                "genre": form.cleaned_data.get("genre"),
                "event_date": (
                    str(form.cleaned_data.get("event_date"))
                    if form.cleaned_data.get("event_date")
                    else None
                ),
                "event_time": (
                    str(form.cleaned_data.get("event_time"))
                    if form.cleaned_data.get("event_time")
                    else None
                ),
                "venue_text": form.cleaned_data.get("venue_text"),
                "artists_text": form.cleaned_data.get("artists_text"),
                "ticket_url": form.cleaned_data.get("ticket_url"),
                "description": form.cleaned_data.get("description"),
                "poster_blob_ref": poster_blob_ref,
            }
            submission_json = json.dumps(submission_data, indent=2).encode("utf-8")
            storage = get_storage()
            data_blob_ref = storage.save("submission.json", submission_json, "application/json")

            raw_ingest = RawIngest.objects.create(
                source=form_source,
                blob_ref=data_blob_ref,
                content_type="application/json",
                fetched_at=timezone.now(),
            )

            submission = Submission.objects.create(
                raw_ingest=raw_ingest,
                submitter_contact=form.cleaned_data.get("submitter_contact", ""),
            )

            if settings.SUBMISSION_INBOX:
                send_mail(
                    subject="New submission via web form",
                    message=(
                        f"Submission #{submission.pk}\n"
                        f"Contact: {submission.submitter_contact or 'none'}\n"
                        f"Title: {submission_data['title'] or 'N/A'}\n"
                        f"Poster: {poster_blob_ref or 'N/A'}"
                    ),
                    from_email=getattr(
                        settings, "DEFAULT_FROM_EMAIL", "noreply@bengaluruclassical.in"
                    ),
                    recipient_list=[settings.SUBMISSION_INBOX],
                    fail_silently=True,
                )

            return redirect(f"{request.path}?success=1")
    else:
        form = SubmissionForm()

    success = request.GET.get("success") == "1"
    return render(request, "web/submit.html", {"form": form, "success": success})
