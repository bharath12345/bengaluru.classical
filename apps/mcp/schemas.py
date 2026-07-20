from pydantic import BaseModel, Field


class SearchEventsInput(BaseModel):
    date_range: str | None = None
    genre: str | None = None
    venue: str | None = None
    artist: str | None = None
    area: str | None = None


class EventOutput(BaseModel):
    id: int
    title: str
    slug: str
    genre: str
    start_at: str
    end_at: str | None = None
    venue: str
    area: str = ""
    is_free: bool = True
    price: str | None = None
    currency: str = "INR"
    source_url: str = ""
    description: str = ""
    poster_url: str | None = None
    artists: list[dict] = Field(default_factory=list)
    status: str = "published"


class VenueOutput(BaseModel):
    id: int
    name: str
    slug: str
    area: str = ""
    address: str = ""
    map_url: str = ""


class ArtistOutput(BaseModel):
    id: int
    name: str
    slug: str
    primary_role: str = ""
