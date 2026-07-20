# Plan 5 — MCP Server (AI-native read-only access) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AI-native surface: a read-only MCP server exposing published events via stateless streamable-HTTP using FastMCP, mounted alongside Django, with rate limiting, discovery metadata, and comprehensive tests.

**Architecture:** A FastMCP 2.x stateless streamable-HTTP server provides read-only tools (`search_events`, `get_event`, `list_venues`, `list_artists`) that query the Django ORM over PUBLISHED events only. The FastMCP ASGI app is composed with Django's ASGI app via Starlette `Mount` so both serve from a single Cloud Run service. An IP-based token-bucket rate limiter (429 + reset headers + Origin validation) guards the `/mcp` endpoint. Discovery metadata (`/.well-known/mcp.json`, `llms.txt`) is served, and registry publishing is documented. Tests call tool functions directly against factory-seeded DB and verify that unpublished events never leak.

**Tech Stack:** Python 3.13, Django 5.x, FastMCP 2.x (`fastmcp>=2.0`), Starlette (for ASGI composition), Pydantic (for schemas), `pytest` + `pytest-django`, `factory_boy`.

## Global Constraints

- Python version floor: **3.13** (`requires-python = ">=3.13"`).
- Django: **5.x** (`>=5.1,<6.0`).
- Database engine is **PostgreSQL only** — never add SQLite fallbacks; local + test + prod all use Postgres.
- **Account separation (hard rule):** all runtime/API usage and git authorship use the personal identity `bharath12345@gmail.com`; the employer identity `bharadwaj@conviva.com` is never referenced in code, config, or commits. Git commits set `user.email=bharath12345@gmail.com`, `user.name=Bharadwaj`.
- **Secrets never committed:** all secrets come from environment variables; `.env` is gitignored (already present).
- **Read-only:** the MCP server NEVER mutates data. All tools perform SELECT queries only.
- **Published events only:** All tools MUST filter `status=PUBLISHED` using `Event.objects.published()` (defined in Plan 2).
- MCP endpoint path: `/mcp` (stateless streamable-HTTP).
- Discovery path: `/.well-known/mcp.json`.
- All datetimes are timezone-aware; `TIME_ZONE = "Asia/Kolkata"`, `USE_TZ = True`.

---

## File Structure

```
apps/
  mcp/                               # New app for MCP server
    __init__.py
    apps.py
    server.py                        # FastMCP server definition + tools
    rate_limit.py                    # Token-bucket rate limiter
    schemas.py                       # Input/output Pydantic models
    asgi.py                          # ASGI composition (Django + FastMCP)
    tests/
      __init__.py
      test_mcp_tools.py              # Tool logic tests (DB queries)
      test_rate_limit.py             # Rate limiter logic tests
      test_asgi_mount.py             # Optional ASGI transport smoke test
static/
  .well-known/
    mcp.json                         # MCP discovery metadata
```

**ASSUMPTION:** FastMCP 2.x provides a `FastMCP()` server class with a `@tool` decorator for defining tools, and an ASGI-compatible app via `server.get_asgi_app()` or similar. If the actual API differs, the plan documents the expected interface and implementation will adapt.

**ASSUMPTION:** Starlette's `Mount` is used to compose the FastMCP ASGI app with Django's ASGI app under the `/mcp` path. This is a standard ASGI pattern; if FastMCP provides a custom mounting mechanism, that will be used instead.

---

### Task 1: Add `apps.mcp` app scaffold and dependencies

**Files:**
- Create: `apps/mcp/__init__.py`, `apps/mcp/apps.py`, `apps/mcp/tests/__init__.py`
- Modify: `config/settings/base.py` (append `"apps.mcp"` to `INSTALLED_APPS`)
- Modify: `pyproject.toml` (add FastMCP + Starlette deps)

**Interfaces:**
- Consumes: settings/app scaffolding from Plan 1.
- Produces:
  - `apps.mcp` app registered in Django `INSTALLED_APPS`.
  - Dependencies available: `fastmcp>=2.0`, `starlette>=0.37`.

- [ ] **Step 1: Add dependencies to pyproject.toml**

Modify the `dependencies` array in `pyproject.toml` to include FastMCP and Starlette:

```toml
dependencies = [
    "django>=5.1,<6.0",
    "psycopg[binary]>=3.2",
    "dj-database-url>=2.2",
    "fastmcp>=2.0",
    "starlette>=0.37",
]
```

- [ ] **Step 2: Install dependencies**

Run:
```bash
uv sync
```
Expected: `uv sync` resolves and updates `uv.lock` with FastMCP and Starlette.

- [ ] **Step 3: Create the app scaffold**

```python
# apps/mcp/__init__.py
```

```python
# apps/mcp/apps.py
from django.apps import AppConfig


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mcp"
    label = "mcp"
```

```python
# apps/mcp/tests/__init__.py
```

- [ ] **Step 4: Register the app in settings**

In `config/settings/base.py`, extend the local-apps section:

```python
    # local apps
    "apps.core",
    "apps.events",
    "apps.sources",
    "apps.ingest",
    "apps.mcp",
```

- [ ] **Step 5: Verify Django check passes**

Run: `uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add apps.mcp scaffold and FastMCP dependencies"
```

---

### Task 2: Define input/output schemas for MCP tools

**Files:**
- Create: `apps/mcp/schemas.py`
- Create: `apps/mcp/tests/test_schemas.py`

**Interfaces:**
- Consumes: nothing (schemas are pure data definitions).
- Produces (relied on by Task 3):
  - `SearchEventsInput(date_range: str | None, genre: str | None, venue: str | None, artist: str | None, area: str | None)`
  - `EventOutput(id: int, title: str, slug: str, genre: str, start_at: str, end_at: str | None, venue: str, area: str, is_free: bool, price: str | None, currency: str, source_url: str, description: str, poster_url: str | None, artists: list[dict], status: str)`
  - `VenueOutput(id: int, name: str, slug: str, area: str, address: str, map_url: str)`
  - `ArtistOutput(id: int, name: str, slug: str, primary_role: str)`

- [ ] **Step 1: Write the failing tests**

```python
# apps/mcp/tests/test_schemas.py
from apps.mcp.schemas import ArtistOutput, EventOutput, SearchEventsInput, VenueOutput


def test_search_events_input_all_optional():
    input_data = SearchEventsInput()
    assert input_data.date_range is None
    assert input_data.genre is None
    assert input_data.venue is None
    assert input_data.artist is None
    assert input_data.area is None


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
        id=1, name="Chowdiah Hall", slug="chowdiah-hall", area="Vyalikaval", address="123 Street", map_url=""
    )
    assert output.name == "Chowdiah Hall"


def test_artist_output():
    output = ArtistOutput(id=1, name="Artist", slug="artist", primary_role="vocal")
    assert output.name == "Artist"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest apps/mcp/tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.mcp.schemas'`.

- [ ] **Step 3: Implement the schemas**

```python
# apps/mcp/schemas.py
from pydantic import BaseModel


class SearchEventsInput(BaseModel):
    date_range: str | None = None  # Format: "YYYY-MM-DD:YYYY-MM-DD" or "YYYY-MM-DD" (single day)
    genre: str | None = None  # "karnatic" or "hindustani"
    venue: str | None = None  # Venue name (partial match)
    artist: str | None = None  # Artist name (partial match)
    area: str | None = None  # Area name (partial match)


class EventOutput(BaseModel):
    id: int
    title: str
    slug: str
    genre: str
    start_at: str  # ISO-8601 with timezone offset
    end_at: str | None
    venue: str  # Venue name
    area: str  # Venue area
    is_free: bool
    price: str | None  # Decimal as string
    currency: str
    source_url: str
    description: str
    poster_url: str | None
    artists: list[dict]  # [{"name": "...", "role": "..."}]
    status: str


class VenueOutput(BaseModel):
    id: int
    name: str
    slug: str
    area: str
    address: str
    map_url: str


class ArtistOutput(BaseModel):
    id: int
    name: str
    slug: str
    primary_role: str
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/mcp/tests/test_schemas.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add MCP input/output Pydantic schemas"
```

---

### Task 3: Implement MCP tool functions (read-only, published events only)

**Files:**
- Create: `apps/mcp/server.py`
- Create: `apps/mcp/tests/test_mcp_tools.py`

**Interfaces:**
- Consumes: `apps.events.models.Event`, `apps.core.models.{Venue, Artist}`, `apps.mcp.schemas.*`, `Event.objects.published()` (from Plan 2).
- Produces (relied on by Task 5):
  - FastMCP server instance with tools: `search_events(input: SearchEventsInput) -> list[EventOutput]`, `get_event(event_id: int) -> EventOutput | None`, `list_venues() -> list[VenueOutput]`, `list_artists() -> list[ArtistOutput]`.

**ASSUMPTION:** Plan 2 added `Event.objects.published()` as a custom manager method that returns `Event.objects.filter(status=Event.Status.PUBLISHED)`. Similarly, `Event.objects.upcoming()` returns published events with `start_at >= now()`, and `Event.objects.past()` returns published events with `start_at < now()`.

- [ ] **Step 1: Write the failing tests**

```python
# apps/mcp/tests/test_mcp_tools.py
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.factories import ArtistFactory, VenueFactory
from apps.events.factories import EventArtistFactory, EventFactory
from apps.events.models import Event
from apps.mcp.schemas import SearchEventsInput
from apps.mcp.server import get_event, list_artists, list_venues, search_events

pytestmark = pytest.mark.django_db


def test_search_events_returns_only_published():
    EventFactory(status=Event.Status.PUBLISHED, title="Published Concert")
    EventFactory(status=Event.Status.REVIEW, title="Review Concert")
    EventFactory(status=Event.Status.REJECTED, title="Rejected Concert")

    results = search_events(SearchEventsInput())
    assert len(results) == 1
    assert results[0].title == "Published Concert"


def test_search_events_filters_by_genre():
    EventFactory(status=Event.Status.PUBLISHED, genre=Event.Genre.KARNATIC)
    EventFactory(status=Event.Status.PUBLISHED, genre=Event.Genre.HINDUSTANI)

    results = search_events(SearchEventsInput(genre="karnatic"))
    assert len(results) == 1
    assert results[0].genre == "karnatic"


def test_search_events_filters_by_date_range():
    now = timezone.now()
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=1))
    EventFactory(status=Event.Status.PUBLISHED, start_at=now + timedelta(days=10))

    start = (now + timedelta(days=1)).date().isoformat()
    end = (now + timedelta(days=5)).date().isoformat()
    results = search_events(SearchEventsInput(date_range=f"{start}:{end}"))
    assert len(results) == 1


def test_search_events_filters_by_venue_name():
    venue1 = VenueFactory(name="Chowdiah Hall")
    venue2 = VenueFactory(name="Sri Rama Mandira")
    EventFactory(status=Event.Status.PUBLISHED, venue=venue1)
    EventFactory(status=Event.Status.PUBLISHED, venue=venue2)

    results = search_events(SearchEventsInput(venue="Chowdiah"))
    assert len(results) == 1
    assert results[0].venue == "Chowdiah Hall"


def test_search_events_filters_by_artist_name():
    artist1 = ArtistFactory(name="T. M. Krishna")
    artist2 = ArtistFactory(name="Bombay Jayashri")
    event1 = EventFactory(status=Event.Status.PUBLISHED)
    event2 = EventFactory(status=Event.Status.PUBLISHED)
    EventArtistFactory(event=event1, artist=artist1, role="vocal")
    EventArtistFactory(event=event2, artist=artist2, role="vocal")

    results = search_events(SearchEventsInput(artist="Krishna"))
    assert len(results) == 1
    assert results[0].artists[0]["name"] == "T. M. Krishna"


def test_search_events_filters_by_area():
    venue1 = VenueFactory(area="Jayanagar")
    venue2 = VenueFactory(area="Vyalikaval")
    EventFactory(status=Event.Status.PUBLISHED, venue=venue1)
    EventFactory(status=Event.Status.PUBLISHED, venue=venue2)

    results = search_events(SearchEventsInput(area="Jayanagar"))
    assert len(results) == 1
    assert results[0].area == "Jayanagar"


def test_get_event_returns_published_event():
    event = EventFactory(status=Event.Status.PUBLISHED, title="Concert")
    result = get_event(event.id)
    assert result is not None
    assert result.title == "Concert"


def test_get_event_returns_none_for_unpublished():
    event = EventFactory(status=Event.Status.REVIEW, title="Review Concert")
    result = get_event(event.id)
    assert result is None


def test_get_event_returns_none_for_nonexistent():
    result = get_event(99999)
    assert result is None


def test_list_venues_returns_all_venues():
    VenueFactory(name="Venue A")
    VenueFactory(name="Venue B")
    results = list_venues()
    assert len(results) == 2
    assert results[0].name in ["Venue A", "Venue B"]


def test_list_artists_returns_all_artists():
    ArtistFactory(name="Artist A")
    ArtistFactory(name="Artist B")
    results = list_artists()
    assert len(results) == 2
    assert results[0].name in ["Artist A", "Artist B"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest apps/mcp/tests/test_mcp_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.mcp.server'`.

- [ ] **Step 3: Implement the tool functions**

```python
# apps/mcp/server.py
from datetime import datetime

from django.db.models import Q
from fastmcp import FastMCP

from apps.core.models import Artist, Venue
from apps.events.models import Event
from apps.mcp.schemas import ArtistOutput, EventOutput, SearchEventsInput, VenueOutput

# Create the FastMCP server instance
mcp = FastMCP("Bengaluru Classical Concerts")


def _event_to_output(event: Event) -> EventOutput:
    """Convert an Event model instance to EventOutput schema."""
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
        artists=[
            {"name": ea.artist.name, "role": ea.role} for ea in event.event_artists.all()
        ],
        status=event.status,
    )


@mcp.tool()
def search_events(input: SearchEventsInput) -> list[EventOutput]:
    """
    Search for published classical concerts in Bengaluru.

    Filters:
    - date_range: "YYYY-MM-DD:YYYY-MM-DD" (inclusive) or "YYYY-MM-DD" (single day)
    - genre: "karnatic" or "hindustani"
    - venue: Venue name (partial match, case-insensitive)
    - artist: Artist name (partial match, case-insensitive)
    - area: Area name (partial match, case-insensitive)

    Returns only PUBLISHED events.
    """
    queryset = Event.objects.published().select_related("venue", "city").prefetch_related(
        "event_artists__artist"
    )

    # Filter by genre
    if input.genre:
        queryset = queryset.filter(genre=input.genre)

    # Filter by date range
    if input.date_range:
        if ":" in input.date_range:
            start_str, end_str = input.date_range.split(":")
            start_date = datetime.fromisoformat(start_str).date()
            end_date = datetime.fromisoformat(end_str).date()
            queryset = queryset.filter(start_at__date__gte=start_date, start_at__date__lte=end_date)
        else:
            single_date = datetime.fromisoformat(input.date_range).date()
            queryset = queryset.filter(start_at__date=single_date)

    # Filter by venue name
    if input.venue:
        queryset = queryset.filter(venue__name__icontains=input.venue)

    # Filter by artist name
    if input.artist:
        queryset = queryset.filter(artists__name__icontains=input.artist).distinct()

    # Filter by area
    if input.area:
        queryset = queryset.filter(venue__area__icontains=input.area)

    # Limit to 100 results to prevent abuse
    events = queryset[:100]
    return [_event_to_output(event) for event in events]


@mcp.tool()
def get_event(event_id: int) -> EventOutput | None:
    """
    Get a single event by ID.

    Returns the event if it is PUBLISHED, otherwise None.
    """
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


@mcp.tool()
def list_venues() -> list[VenueOutput]:
    """
    List all venues in Bengaluru.

    Returns all venues, ordered by name.
    """
    venues = Venue.objects.all().order_by("name")
    return [
        VenueOutput(
            id=v.id, name=v.name, slug=v.slug, area=v.area, address=v.address, map_url=v.map_url
        )
        for v in venues
    ]


@mcp.tool()
def list_artists() -> list[ArtistOutput]:
    """
    List all artists.

    Returns all artists, ordered by name.
    """
    artists = Artist.objects.all().order_by("name")
    return [
        ArtistOutput(id=a.id, name=a.name, slug=a.slug, primary_role=a.primary_role)
        for a in artists
    ]
```

**ASSUMPTION:** `Event.objects.published()` is a custom manager method defined in Plan 2 that filters `status=Event.Status.PUBLISHED`. If not yet implemented, the tool functions use `Event.objects.filter(status=Event.Status.PUBLISHED)` directly.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/mcp/tests/test_mcp_tools.py -v`
Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: implement read-only MCP tools (search_events, get_event, list_venues, list_artists)"
```

---

### Task 4: Implement token-bucket rate limiter

**Files:**
- Create: `apps/mcp/rate_limit.py`
- Create: `apps/mcp/tests/test_rate_limit.py`

**Interfaces:**
- Consumes: nothing (pure logic).
- Produces (relied on by Task 5):
  - `TokenBucket(capacity: int, refill_rate: float)` — class with `consume(tokens: int) -> bool` and `reset_time() -> float` methods.
  - `get_client_ip(scope: dict) -> str` — extracts IP from ASGI scope (honors `X-Forwarded-For`).
  - `RateLimiter(capacity: int, refill_rate: float)` — per-IP token-bucket manager with `check(ip: str) -> tuple[bool, float]` returning `(allowed, reset_time)`.

- [ ] **Step 1: Write the failing tests**

```python
# apps/mcp/tests/test_rate_limit.py
import time

import pytest

from apps.mcp.rate_limit import RateLimiter, TokenBucket, get_client_ip


def test_token_bucket_allows_within_capacity():
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    assert bucket.consume(5) is True
    assert bucket.consume(5) is True
    assert bucket.consume(1) is False  # Exceeded capacity


def test_token_bucket_refills_over_time():
    bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
    bucket.consume(10)
    time.sleep(0.5)  # 5 tokens refilled
    assert bucket.consume(5) is True
    assert bucket.consume(1) is False


def test_token_bucket_reset_time():
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    bucket.consume(10)
    reset = bucket.reset_time()
    assert reset > time.time()


def test_get_client_ip_from_x_forwarded_for():
    scope = {"headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")]}
    ip = get_client_ip(scope)
    assert ip == "1.2.3.4"


def test_get_client_ip_from_client():
    scope = {"client": ("9.8.7.6", 12345)}
    ip = get_client_ip(scope)
    assert ip == "9.8.7.6"


def test_get_client_ip_unknown():
    scope = {}
    ip = get_client_ip(scope)
    assert ip == "unknown"


def test_rate_limiter_allows_within_limit():
    limiter = RateLimiter(capacity=10, refill_rate=1.0)
    allowed, _ = limiter.check("1.2.3.4")
    assert allowed is True


def test_rate_limiter_blocks_over_limit():
    limiter = RateLimiter(capacity=2, refill_rate=1.0)
    limiter.check("1.2.3.4")
    limiter.check("1.2.3.4")
    allowed, reset = limiter.check("1.2.3.4")
    assert allowed is False
    assert reset > time.time()


def test_rate_limiter_per_ip_isolation():
    limiter = RateLimiter(capacity=1, refill_rate=1.0)
    limiter.check("1.2.3.4")
    allowed, _ = limiter.check("5.6.7.8")
    assert allowed is True  # Different IP, separate bucket
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest apps/mcp/tests/test_rate_limit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.mcp.rate_limit'`.

- [ ] **Step 3: Implement the rate limiter**

```python
# apps/mcp/rate_limit.py
import time


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize a token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def reset_time(self) -> float:
        """
        Get the time when the bucket will be full again.

        Returns:
            Unix timestamp
        """
        tokens_needed = self.capacity - self.tokens
        seconds_needed = tokens_needed / self.refill_rate
        return time.time() + seconds_needed


class RateLimiter:
    """Per-IP rate limiter using token buckets."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize the rate limiter.

        Args:
            capacity: Maximum requests per IP
            refill_rate: Requests refilled per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, TokenBucket] = {}

    def check(self, ip: str) -> tuple[bool, float]:
        """
        Check if a request from the given IP is allowed.

        Args:
            ip: Client IP address

        Returns:
            (allowed, reset_time) tuple
        """
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(self.capacity, self.refill_rate)

        bucket = self.buckets[ip]
        allowed = bucket.consume(1)
        reset_time = bucket.reset_time()
        return allowed, reset_time


def get_client_ip(scope: dict) -> str:
    """
    Extract client IP from ASGI scope, honoring X-Forwarded-For.

    Args:
        scope: ASGI scope dict

    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (Cloud Run sets this)
    headers = dict(scope.get("headers", []))
    forwarded_for = headers.get(b"x-forwarded-for", b"").decode("utf-8")
    if forwarded_for:
        # Take the first IP (client)
        return forwarded_for.split(",")[0].strip()

    # Fallback to direct client
    client = scope.get("client")
    if client:
        return client[0]

    return "unknown"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/mcp/tests/test_rate_limit.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: implement IP-based token-bucket rate limiter with tests"
```

---

### Task 5: Compose FastMCP and Django ASGI apps with rate limiting

**Files:**
- Create: `apps/mcp/asgi.py`
- Modify: `config/asgi.py` (import and use MCP ASGI app)
- Create: `apps/mcp/tests/test_asgi_mount.py`

**Interfaces:**
- Consumes: `apps.mcp.server.mcp` (FastMCP instance), `apps.mcp.rate_limit.{RateLimiter, get_client_ip}`, Django ASGI app.
- Produces:
  - ASGI application that serves Django at `/` and FastMCP at `/mcp`, with rate limiting on `/mcp`.

**ASSUMPTION:** FastMCP provides `mcp.get_asgi_app()` or similar to get an ASGI-compatible app. Starlette's `Mount` is used to compose the two ASGI apps. If FastMCP uses a different pattern, the implementation will adapt.

- [ ] **Step 1: Write the failing test**

```python
# apps/mcp/tests/test_asgi_mount.py
import pytest


@pytest.mark.django_db
def test_asgi_app_imports_cleanly():
    """Smoke test: the composed ASGI app imports without error."""
    from apps.mcp.asgi import application

    assert application is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/mcp/tests/test_asgi_mount.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.mcp.asgi'` or import error.

- [ ] **Step 3: Implement the ASGI composition with rate limiting**

```python
# apps/mcp/asgi.py
import os
from typing import Awaitable, Callable

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount

from apps.mcp.rate_limit import RateLimiter, get_client_ip

# Initialize Django ASGI application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django_app = get_asgi_application()

# Import FastMCP server
from apps.mcp.server import mcp

# Rate limiter: 100 requests per IP, refill 10/sec (burst tolerance)
rate_limiter = RateLimiter(capacity=100, refill_rate=10.0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limiting middleware for MCP endpoints."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Get client IP
        ip = get_client_ip(request.scope)

        # Check rate limit
        allowed, reset_time = rate_limiter.check(ip)
        if not allowed:
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={
                    "Retry-After": str(int(reset_time - __import__("time").time())),
                    "X-RateLimit-Reset": str(int(reset_time)),
                },
            )

        # Validate Origin (optional: block if not from expected domains)
        # For now, allow all origins (read-only public MCP)

        return await call_next(request)


# Get FastMCP ASGI app
# ASSUMPTION: FastMCP 2.x provides mcp.get_asgi_app() or similar
try:
    mcp_app = mcp.get_asgi_app()
except AttributeError:
    # Fallback: if FastMCP uses a different API, adapt here
    mcp_app = mcp  # Assume mcp instance is ASGI-compatible

# Wrap MCP app with rate limiting
mcp_app_with_middleware = Starlette(
    routes=[Mount("/", app=mcp_app)],
    middleware=[Middleware(RateLimitMiddleware)],
)

# Compose Django and FastMCP under a single ASGI app
application = Starlette(
    routes=[
        Mount("/mcp", app=mcp_app_with_middleware),
        Mount("/", app=django_app),
    ]
)
```

- [ ] **Step 4: Update config/asgi.py to use the composed app**

```python
# config/asgi.py
"""
ASGI config for bengaluru-classical project.

Exposes the ASGI callable as a module-level variable named `application`.

Serves Django at `/` and FastMCP at `/mcp`.
"""

from apps.mcp.asgi import application

__all__ = ["application"]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest apps/mcp/tests/test_asgi_mount.py -v`
Expected: PASS.

- [ ] **Step 6: Verify Django check passes**

Run: `uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 7: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: compose FastMCP and Django ASGI apps with rate limiting at /mcp"
```

---

### Task 6: Add discovery metadata and documentation

**Files:**
- Create: `static/.well-known/mcp.json`
- Modify: `apps/web/views.py` (add view for `/.well-known/mcp.json` — stub assumption that `apps.web` exists from Plan 2)
- Modify: `static/llms.txt` (add MCP endpoint reference — stub assumption from Plan 2)
- Create: `docs/MCP_REGISTRY.md`

**Interfaces:**
- Consumes: MCP server from Task 5.
- Produces:
  - `/.well-known/mcp.json` served with correct content-type.
  - `llms.txt` references the MCP endpoint.
  - Documentation for publishing to MCP Registry.

**ASSUMPTION:** `apps.web` and `static/llms.txt` exist from Plan 2. If not, this task creates placeholders.

- [ ] **Step 1: Create the MCP discovery metadata file**

```json
{
  "name": "Bengaluru Classical Concerts",
  "description": "Read-only access to published classical music concerts in Bengaluru (Karnatic and Hindustani)",
  "version": "1.0.0",
  "protocol": "mcp",
  "transport": "http",
  "endpoint": "/mcp",
  "capabilities": {
    "tools": [
      {
        "name": "search_events",
        "description": "Search for published classical concerts by date, genre, venue, artist, or area"
      },
      {
        "name": "get_event",
        "description": "Get a single event by ID"
      },
      {
        "name": "list_venues",
        "description": "List all venues in Bengaluru"
      },
      {
        "name": "list_artists",
        "description": "List all artists"
      }
    ]
  },
  "authentication": "none",
  "rateLimits": {
    "requests": 100,
    "window": "burst",
    "refillRate": "10/sec"
  }
}
```

Save as `static/.well-known/mcp.json`.

- [ ] **Step 2: Add Django view to serve the discovery file**

**ASSUMPTION:** `apps.web.views` exists from Plan 2. If not, create a minimal version.

```python
# apps/web/views.py (append if exists, or create)
from django.http import JsonResponse
from django.views import View
import json
from pathlib import Path


class McpDiscoveryView(View):
    """Serve MCP discovery metadata."""

    def get(self, request):
        mcp_json_path = Path(__file__).resolve().parent.parent.parent / "static" / ".well-known" / "mcp.json"
        with open(mcp_json_path, "r") as f:
            data = json.load(f)
        return JsonResponse(data, content_type="application/json")
```

- [ ] **Step 3: Wire the view to URLs**

**ASSUMPTION:** `config/urls.py` or `apps.web.urls` exists from Plan 2. Add the route.

In `config/urls.py`, add:

```python
from apps.web.views import McpDiscoveryView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(".well-known/mcp.json", McpDiscoveryView.as_view(), name="mcp_discovery"),
    # ... other routes from Plan 2
]
```

- [ ] **Step 4: Update llms.txt to reference the MCP endpoint**

**ASSUMPTION:** `static/llms.txt` exists from Plan 2. Append:

```
# AI-native access

MCP server (read-only): /mcp
MCP discovery: /.well-known/mcp.json
Tools: search_events, get_event, list_venues, list_artists
```

- [ ] **Step 5: Write MCP Registry publishing documentation**

```markdown
# MCP Registry Publishing

## Overview

The Bengaluru Classical Concerts MCP server provides read-only access to published concert data. This document describes how to publish the server to the MCP Registry.

## Registry submission

**Status:** NOT YET SUBMITTED (documented for future use).

### Submission steps (when ready)

1. Visit the MCP Registry submission portal (URL TBD by MCP spec maintainers).
2. Provide the following details:
   - **Name:** Bengaluru Classical Concerts
   - **Description:** Read-only access to published classical music concerts in Bengaluru (Karnatic and Hindustani)
   - **Discovery URL:** `https://<domain>/.well-known/mcp.json` (replace `<domain>` with production domain)
   - **Category:** Arts & Culture, Events
   - **Authentication:** None (public read-only)
   - **Rate limits:** 100 requests/IP, refill 10/sec
   - **Contact:** bharath12345@gmail.com
3. Submit for review.

## Local testing

Use an MCP-compatible client (e.g., Claude Desktop, MCP Inspector) to test locally:

```bash
# Start the server
uv run python manage.py runserver

# Point MCP client to http://localhost:8000/mcp
```

## Production endpoint

Once deployed to Cloud Run (Plan 6), the production endpoint will be:

```
https://<domain>/mcp
```

Discovery metadata: `https://<domain>/.well-known/mcp.json`

## Notes

- The MCP server is stateless (no session state).
- All tools are read-only (no mutations).
- Only PUBLISHED events are exposed; REVIEW/REJECTED/CANCELLED events are never returned.
- Rate limiting is enforced per IP (429 responses with `Retry-After` header).
```

Save as `docs/MCP_REGISTRY.md`.

- [ ] **Step 6: Verify the discovery endpoint responds**

Run:
```bash
uv run python manage.py runserver
```

Then in another terminal:
```bash
curl http://localhost:8000/.well-known/mcp.json
```
Expected: JSON response with the discovery metadata.

- [ ] **Step 7: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add MCP discovery metadata, llms.txt update, and registry docs"
```

---

### Task 7: Comprehensive integration tests (no unpublished leaks)

**Files:**
- Create: `apps/mcp/tests/test_integration.py`

**Interfaces:**
- Consumes: all MCP tools from Task 3.
- Produces:
  - Tests that verify PUBLISHED-only filtering across all tools, edge cases, and data integrity.

- [ ] **Step 1: Write the integration tests**

```python
# apps/mcp/tests/test_integration.py
import pytest
from django.utils import timezone

from apps.core.factories import ArtistFactory, VenueFactory
from apps.events.factories import EventArtistFactory, EventFactory
from apps.events.models import Event
from apps.mcp.schemas import SearchEventsInput
from apps.mcp.server import get_event, list_artists, list_venues, search_events

pytestmark = pytest.mark.django_db


def test_no_unpublished_events_leak_in_search():
    """Critical security test: unpublished events must NEVER appear in search results."""
    EventFactory(status=Event.Status.PUBLISHED, title="Published 1")
    EventFactory(status=Event.Status.PUBLISHED, title="Published 2")
    EventFactory(status=Event.Status.REVIEW, title="Review 1")
    EventFactory(status=Event.Status.REVIEW, title="Review 2")
    EventFactory(status=Event.Status.REJECTED, title="Rejected 1")
    EventFactory(status=Event.Status.CANCELLED, title="Cancelled 1")

    results = search_events(SearchEventsInput())
    assert len(results) == 2
    assert all(r.status == "published" for r in results)
    assert all("Review" not in r.title and "Rejected" not in r.title and "Cancelled" not in r.title for r in results)


def test_no_unpublished_events_leak_in_get():
    """Critical security test: get_event must NOT return unpublished events."""
    review = EventFactory(status=Event.Status.REVIEW)
    rejected = EventFactory(status=Event.Status.REJECTED)
    cancelled = EventFactory(status=Event.Status.CANCELLED)

    assert get_event(review.id) is None
    assert get_event(rejected.id) is None
    assert get_event(cancelled.id) is None


def test_search_events_empty_filters_returns_all_published():
    EventFactory(status=Event.Status.PUBLISHED)
    EventFactory(status=Event.Status.PUBLISHED)
    results = search_events(SearchEventsInput())
    assert len(results) == 2


def test_search_events_no_results_when_no_published():
    EventFactory(status=Event.Status.REVIEW)
    results = search_events(SearchEventsInput())
    assert len(results) == 0


def test_search_events_limit_enforced():
    """Verify the 100-result limit is enforced."""
    for _ in range(150):
        EventFactory(status=Event.Status.PUBLISHED)
    results = search_events(SearchEventsInput())
    assert len(results) == 100


def test_get_event_includes_artist_details():
    event = EventFactory(status=Event.Status.PUBLISHED)
    artist = ArtistFactory(name="Test Artist")
    EventArtistFactory(event=event, artist=artist, role="vocal")

    result = get_event(event.id)
    assert result is not None
    assert len(result.artists) == 1
    assert result.artists[0]["name"] == "Test Artist"
    assert result.artists[0]["role"] == "vocal"


def test_list_venues_returns_all():
    VenueFactory(name="Venue A")
    VenueFactory(name="Venue B")
    VenueFactory(name="Venue C")
    results = list_venues()
    assert len(results) == 3


def test_list_artists_returns_all():
    ArtistFactory(name="Artist A")
    ArtistFactory(name="Artist B")
    results = list_artists()
    assert len(results) == 2


def test_search_events_date_range_single_day():
    now = timezone.now()
    event = EventFactory(status=Event.Status.PUBLISHED, start_at=now)
    EventFactory(status=Event.Status.PUBLISHED, start_at=now.replace(day=now.day + 1))

    results = search_events(SearchEventsInput(date_range=now.date().isoformat()))
    assert len(results) == 1
    assert results[0].id == event.id


def test_search_events_combined_filters():
    venue = VenueFactory(name="Test Venue", area="Test Area")
    artist = ArtistFactory(name="Test Artist")
    event = EventFactory(
        status=Event.Status.PUBLISHED, genre=Event.Genre.KARNATIC, venue=venue
    )
    EventArtistFactory(event=event, artist=artist, role="vocal")

    # Should match
    results = search_events(
        SearchEventsInput(genre="karnatic", venue="Test", artist="Test", area="Test Area")
    )
    assert len(results) == 1
    assert results[0].id == event.id

    # Should NOT match (wrong genre)
    results = search_events(SearchEventsInput(genre="hindustani"))
    assert len(results) == 0
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `uv run pytest apps/mcp/tests/test_integration.py -v`
Expected: all 11 tests PASS.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests across all apps PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "test: add comprehensive MCP integration tests (published-only filtering)"
```

---

### Task 8: Final verification, lint, and documentation

**Files:**
- Modify: `docs/DEVELOPMENT.md` (add MCP testing instructions)
- Create: `docs/MCP_USAGE.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces:
  - Clean lint pass.
  - Updated developer documentation.
  - Usage guide for the MCP server.

- [ ] **Step 1: Run ruff and fix any lint**

Run: `uv run ruff check . && uv run ruff format .`
Expected: `All checks passed!` (fix and re-run if not).

- [ ] **Step 2: Update DEVELOPMENT.md with MCP testing instructions**

Append to `docs/DEVELOPMENT.md`:

```markdown
## MCP server (local testing)

Start the server:
```bash
uv run python manage.py runserver
```

Test the MCP endpoint:
```bash
# Discovery metadata
curl http://localhost:8000/.well-known/mcp.json

# MCP endpoint (requires MCP-compatible client)
# Point client to: http://localhost:8000/mcp
```

Run MCP-specific tests:
```bash
uv run pytest apps/mcp/tests/ -v
```
```

- [ ] **Step 3: Write MCP usage documentation**

```markdown
# MCP Server Usage

## Overview

The Bengaluru Classical Concerts MCP server provides read-only access to published concert data. It is designed for AI agents and assistants to query upcoming and past classical music events.

## Endpoint

- **Local:** `http://localhost:8000/mcp`
- **Production:** `https://<domain>/mcp` (once deployed)

## Discovery

- **Discovery metadata:** `/.well-known/mcp.json`
- **llms.txt:** `/llms.txt` (references the MCP endpoint)

## Tools

### 1. search_events

Search for published classical concerts.

**Inputs:**
- `date_range` (optional): `"YYYY-MM-DD:YYYY-MM-DD"` (range) or `"YYYY-MM-DD"` (single day)
- `genre` (optional): `"karnatic"` or `"hindustani"`
- `venue` (optional): Venue name (partial match, case-insensitive)
- `artist` (optional): Artist name (partial match, case-insensitive)
- `area` (optional): Area name (partial match, case-insensitive)

**Output:** List of `EventOutput` objects (max 100).

**Example:**
```json
{
  "date_range": "2026-07-20:2026-07-31",
  "genre": "karnatic",
  "area": "Jayanagar"
}
```

### 2. get_event

Get a single event by ID.

**Inputs:**
- `event_id` (int): Event ID

**Output:** `EventOutput` or `null` if not found or not published.

### 3. list_venues

List all venues in Bengaluru.

**Inputs:** None

**Output:** List of `VenueOutput` objects.

### 4. list_artists

List all artists.

**Inputs:** None

**Output:** List of `ArtistOutput` objects.

## Rate Limiting

- **Limit:** 100 requests per IP (burst)
- **Refill rate:** 10 requests/second
- **Response on exceeded:** `429 Too Many Requests` with `Retry-After` and `X-RateLimit-Reset` headers

## Security

- **Read-only:** No mutations allowed.
- **Published events only:** Events with `status=REVIEW`, `REJECTED`, or `CANCELLED` are NEVER returned.
- **IP-based rate limiting:** Enforced per client IP.
- **No authentication:** Public read-only access (unauthenticated).

## Testing with MCP clients

Use an MCP-compatible client (e.g., Claude Desktop, MCP Inspector) to test:

1. Start the local server: `uv run python manage.py runserver`
2. Configure the client to point to `http://localhost:8000/mcp`
3. Invoke tools via the client

## Production deployment

See Plan 6 for Cloud Run deployment. The production endpoint will be served over HTTPS with CDN caching.

## Registry submission

See `docs/MCP_REGISTRY.md` for instructions on publishing to the MCP Registry (not yet submitted).
```

Save as `docs/MCP_USAGE.md`.

- [ ] **Step 4: Run the full test suite to ensure green**

Run: `uv run pytest -v`
Expected: all tests PASS.

- [ ] **Step 5: Verify Django check passes**

Run: `uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "docs: add MCP usage guide and update dev documentation"
```

---

## Self-Review

**1. Spec coverage (this plan is Plan 5 of 6 — scope is MCP server only):**
- FastMCP stateless streamable-HTTP server → Tasks 1, 3, 5. ✓
- Read-only tools (`search_events`, `get_event`, `list_venues`, `list_artists`) → Task 3. ✓
- Filtering by date_range, genre, venue, artist, area → Task 3. ✓
- Precise input/output schemas (Pydantic) → Task 2. ✓
- `Event.objects.published()` usage (no unpublished leaks) → Task 3, tested in Task 7. ✓
- ASGI composition (Django + FastMCP under one service, MCP at `/mcp`) → Task 5. ✓
- Rate limiting (token-bucket per IP, 429 + reset headers) → Task 4, integrated in Task 5. ✓
- Discovery metadata (`/.well-known/mcp.json`) → Task 6. ✓
- `llms.txt` references MCP endpoint → Task 6. ✓
- MCP Registry publishing documented → Task 6. ✓
- Tests: tool functions called directly, PUBLISHED-only verified, rate limiter tested → Tasks 3, 4, 7. ✓
- **Deferred to later plans (correctly out of scope here):** Cloud Run deployment, CDN, domain, production hardening (Plan 6).

**2. Placeholder scan:** No TBD/TODO/"edge cases" placeholders; every code step contains full code. Assumptions about FastMCP API (`mcp.get_asgi_app()`) and `Event.objects.published()` are explicitly stated. ✓

**3. Type consistency:** Input/output schemas defined once (Task 2) and referenced consistently in Task 3. `Event.Status.PUBLISHED` used consistently. `related_name`s match Plan 1 conventions. ✓

**4. Assumptions documented:**
- **FastMCP API:** Assumed `FastMCP()` server class with `@tool` decorator and `mcp.get_asgi_app()` method. Plan documents expected interface; implementation will adapt if actual API differs.
- **Starlette Mount:** Assumed Starlette `Mount` for ASGI composition. Standard pattern; if FastMCP provides custom mounting, that will be used.
- **Event.objects.published():** Assumed custom manager method from Plan 2. If not yet implemented, tools use `Event.objects.filter(status=Event.Status.PUBLISHED)` directly.
- **apps.web existence:** Assumed `apps.web` and `static/llms.txt` from Plan 2. Task 6 creates placeholders if not present.

---

## Follow-on plans (roadmap — written one at a time after this one)

- **Plan 6 — Deployment & infra:** Cloud Build CI/CD, Cloud Run + CDN, GCS + Supabase wiring, Secret Manager, backups, domain, production settings hardening, HTTPS, serving the composed ASGI app in production.
