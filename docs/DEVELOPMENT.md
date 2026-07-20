# Development

## Prerequisites
- Python 3.13, `uv`, Docker (for local Postgres).

## First-time setup
```bash
cp .env.example .env
uv sync
docker compose up -d db
uv run python manage.py migrate
uv run python manage.py seed_bengaluru
uv run python manage.py createsuperuser
```

## Daily loop
```bash
docker compose up -d db          # ensure Postgres is running
uv run python manage.py runserver
# admin backoffice: http://localhost:8000/admin/
```

## Tests & lint
```bash
uv run pytest                    # full suite (uses config.settings.test)
uv run ruff check . && uv run ruff format .
```

## Migrations
```bash
uv run python manage.py makemigrations <app>
uv run python manage.py migrate
uv run python manage.py makemigrations --check --dry-run   # CI gate
```

## Account separation (hard rule)
All GCP/Supabase/API usage and git authorship use the personal identity
`bharath12345@gmail.com`. The employer identity is never used here.

## Tailwind CSS build

The project uses Tailwind CSS v4 standalone CLI (see `docs/TAILWIND.md` for installation).

Development (watch mode):
```bash
tailwindcss -i app/static/src/main.css -o app/static/dist/main.css --watch
```

Production (minified):
```bash
tailwindcss -i app/static/src/main.css -o app/static/dist/main.css --minify
```

## Running the public site

1. Build Tailwind (in one terminal):
```bash
tailwindcss -i app/static/src/main.css -o app/static/dist/main.css --watch
```

2. Run Django dev server (in another terminal):
```bash
docker compose up -d db
uv run python manage.py runserver
```

3. Visit:
- Public site: http://localhost:8000/
- Django admin: http://localhost:8000/admin/
- ICS feed: http://localhost:8000/calendar.ics
- Sitemap: http://localhost:8000/sitemap.xml

## Seeding test data

To see the public site with sample events, create some published events via the admin or shell:

```python
from apps.core.factories import CityFactory, VenueFactory, ArtistFactory
from apps.events.factories import EventFactory, EventArtistFactory
from apps.events.models import Event
from django.utils import timezone
from datetime import timedelta

city = CityFactory(name="Bengaluru", slug="bengaluru")
venue = VenueFactory(city=city)
event = EventFactory(
    status=Event.Status.PUBLISHED,
    start_at=timezone.now() + timedelta(days=3),
    venue=venue,
    city=city,
    slug="sample-concert",
)
artist = ArtistFactory()
EventArtistFactory(event=event, artist=artist, role="vocal")
```

## Public Submission & Inbound Email (Plan 3)

### Public submission form
- URL: `http://localhost:8000/submit/`
- Honeypot spam protection + IP rate limiting (3/hour)
- On submit: creates `RawIngest` + `Submission`, sends notification to `SUBMISSION_INBOX` (console backend in dev)

### Inbound email receiver
- Endpoint: `POST /ingest/email/` (authenticated by shared secret)
- Accepts raw MIME + attachments from Cloudflare Email Worker
- Deploy the worker: see `infra/cloudflare/README.md`

### Storage backends
- **Dev/test:** local filesystem (`mediafiles/raw/`)
- **Prod:** GCS (`RAW_STORAGE_GCS_BUCKET`)
