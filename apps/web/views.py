import json
from itertools import groupby

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.core.models import Series
from apps.events.models import Event


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
