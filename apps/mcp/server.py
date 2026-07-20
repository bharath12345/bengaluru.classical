from datetime import datetime

from fastmcp import FastMCP

from apps.core.models import Artist, Venue
from apps.events.models import Event
from apps.mcp.schemas import ArtistOutput, EventOutput, SearchEventsInput, VenueOutput

mcp = FastMCP("Bengaluru Classical Concerts")


def _event_to_output(event: Event) -> EventOutput:
    return EventOutput(
        id=event.id,
        title=event.title,
        slug=event.slug,
        genre=event.genre,
        start_at=event.start_at.isoformat(),
        end_at=event.end_at.isoformat() if event.end_at else None,
        venue=event.venue.name,
        area=event.venue.area,
        is_free=event.is_free,
        price=str(event.price) if event.price else None,
        currency=event.currency,
        source_url=event.source_url,
        description=event.description,
        poster_url=event.poster.url if event.poster else None,
        artists=[{"name": ea.artist.name, "role": ea.role} for ea in event.event_artists.all()],
        status=event.status,
    )


def search_events(input: SearchEventsInput) -> list[EventOutput]:
    """Search published classical concerts in Bengaluru."""
    queryset = (
        Event.objects.published()
        .select_related("venue", "city")
        .prefetch_related("event_artists__artist")
    )

    if input.genre:
        queryset = queryset.filter(genre=input.genre)

    if input.date_range:
        if ":" in input.date_range:
            start_str, end_str = input.date_range.split(":", 1)
            start_date = datetime.fromisoformat(start_str).date()
            end_date = datetime.fromisoformat(end_str).date()
            queryset = queryset.filter(start_at__date__gte=start_date, start_at__date__lte=end_date)
        else:
            single_date = datetime.fromisoformat(input.date_range).date()
            queryset = queryset.filter(start_at__date=single_date)

    if input.venue:
        queryset = queryset.filter(venue__name__icontains=input.venue)

    if input.artist:
        queryset = queryset.filter(artists__name__icontains=input.artist).distinct()

    if input.area:
        queryset = queryset.filter(venue__area__icontains=input.area)

    return [_event_to_output(event) for event in queryset[:100]]


def get_event(event_id: int) -> EventOutput | None:
    """Get a single published event by ID."""
    try:
        event = (
            Event.objects.published()
            .select_related("venue", "city")
            .prefetch_related("event_artists__artist")
            .get(id=event_id)
        )
        return _event_to_output(event)
    except Event.DoesNotExist:
        return None


def list_venues() -> list[VenueOutput]:
    """List all venues ordered by name."""
    venues = Venue.objects.all().order_by("name")
    return [
        VenueOutput(
            id=v.id, name=v.name, slug=v.slug, area=v.area, address=v.address, map_url=v.map_url
        )
        for v in venues
    ]


def list_artists() -> list[ArtistOutput]:
    """List all artists ordered by name."""
    artists = Artist.objects.all().order_by("name")
    return [
        ArtistOutput(id=a.id, name=a.name, slug=a.slug, primary_role=a.primary_role)
        for a in artists
    ]


# Register tools with FastMCP (callable wrappers preserve plain-function tests)
mcp.tool()(search_events)
mcp.tool()(get_event)
mcp.tool()(list_venues)
mcp.tool()(list_artists)
