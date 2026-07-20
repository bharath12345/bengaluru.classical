from django.http import HttpResponse
from icalendar import Calendar
from icalendar import Event as ICalEvent

from apps.events.models import Event


def ics_feed(request):
    events = Event.objects.upcoming()

    genre = request.GET.get("genre")
    if genre:
        events = events.filter(genre=genre)

    cal = Calendar()
    cal.add("prodid", "-//Bengaluru Classical//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Bengaluru Classical Concerts")

    for event in events:
        ical_event = ICalEvent()
        ical_event.add("summary", event.title)
        ical_event.add("dtstart", event.start_at)
        if event.end_at:
            ical_event.add("dtend", event.end_at)
        ical_event.add(
            "location",
            f"{event.venue.name}, {event.venue.area}, {event.city.name}".strip(", "),
        )
        if event.description:
            ical_event.add("description", event.description)
        ical_event.add("uid", f"event-{event.id}@bengaluruclassical.in")
        ical_event.add("dtstamp", event.created_at)
        cal.add_component(ical_event)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="bengaluru-classical.ics"'
    return response
