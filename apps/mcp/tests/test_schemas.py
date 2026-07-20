from apps.mcp.schemas import ArtistOutput, EventOutput, SearchEventsInput, VenueOutput


def test_search_events_input_all_optional():
    input_data = SearchEventsInput()
    assert input_data.date_range is None
    assert input_data.genre is None


def test_search_events_input_with_values():
    input_data = SearchEventsInput(
        date_range="2026-07-20:2026-07-31", genre="karnatic", area="Jayanagar"
    )
    assert input_data.date_range == "2026-07-20:2026-07-31"
    assert input_data.genre == "karnatic"
    assert input_data.area == "Jayanagar"


def test_event_output_required_fields():
    output = EventOutput(
        id=1,
        title="Concert",
        slug="concert-1",
        genre="karnatic",
        start_at="2026-07-20T18:00:00+05:30",
        end_at=None,
        venue="Chowdiah Hall",
        area="Vyalikaval",
        is_free=True,
        price=None,
        currency="INR",
        source_url="https://example.com",
        description="A concert",
        poster_url=None,
        artists=[],
        status="published",
    )
    assert output.title == "Concert"
    assert output.is_free is True


def test_venue_output():
    output = VenueOutput(
        id=1,
        name="Chowdiah Hall",
        slug="chowdiah-hall",
        area="Vyalikaval",
        address="123 Street",
        map_url="",
    )
    assert output.name == "Chowdiah Hall"


def test_artist_output():
    output = ArtistOutput(id=1, name="T. M. Krishna", slug="tm-krishna", primary_role="vocal")
    assert output.primary_role == "vocal"
