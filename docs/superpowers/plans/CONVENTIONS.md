# Cross-Plan Conventions

Shared decisions that every plan (2–6) must honor so interfaces line up. These
extend the Global Constraints already stated in Plan 1.

## Established by Plan 1 (do not redefine — consume these)

Apps: `apps.core`, `apps.events`, `apps.sources`, `apps.ingest`.

Models & key fields:
- `apps.core.models.City(name, slug, is_active)`, `Venue(name, slug, area, address,
  latitude, longitude, map_url, source_url, city)`, `Artist(name, slug, alt_names,
  primary_role, bio)`, `Series(name, slug, description, city)`, `TimeStampedModel`
  (abstract: `created_at`, `updated_at`).
- `apps.events.models.Event` — `title, slug, genre (Genre.KARNATIC/HINDUSTANI),
  start_at, end_at, venue, city, is_free, price, currency, source_url, description,
  poster (ImageField), status (Status.REVIEW/PUBLISHED/REJECTED/CANCELLED, default
  REVIEW), confidence (float), series, dedup_key, artists (M2M through EventArtist)`;
  property `is_upcoming`. `EventArtist(event, artist, role)`.
- `apps.sources.models.Source` — `name, type (Type.FEED/JSONLD/API/HTML/JS/EMAIL/
  FORM/SOCIAL), url, handle, scrape_method, city, health_status (Health.OK/FAILING/
  DEAD/UNKNOWN), last_seen_at, active, seasonal`; method `mark_seen(at)`.
- `apps.ingest.models.RawIngest(source, blob_ref, content_type, fetched_at,
  processed (State.PENDING/PROCESSED/FAILED), event)`; `Submission(raw_ingest,
  submitter_contact, spam_score, notes)`.

Stack/tooling: Python 3.13, Django 5.x, Postgres-only, `uv`, `ruff`, `pytest` +
`pytest-django`, `factory_boy`. Settings split `config/settings/{base,dev,prod,test}.py`.
Local Postgres via `docker-compose.yml`. Git author for every commit:
`user.name='Bharadwaj'`, `user.email='bharath12345@gmail.com'`.

## New apps introduced by later plans

- Plan 2 → `apps.web` — public site (views, templates, URLs, sitemaps, feeds).
- Plan 3 → submission form lives in `apps.web`; inbound-email receiver is a Django
  view `apps.ingest.views.inbound_email` mounted at `/ingest/email/` (authenticated
  via shared secret `INBOUND_EMAIL_SECRET` in POST body, not header).
- Plan 4 → `apps.pipeline` — scrapers, extractors, dedup, confidence, Cloud Run Job
  entrypoints as Django management commands.
- Plan 5 → `apps.mcp` — FastMCP server mounted alongside Django.
- Plan 6 → `infra/` — Cloud Build, Cloud Run, GCS, Secret Manager, Cloudflare worker.

## URL names (namespaced under `web:` unless noted)

- `web:health` → `/health/` (Cloud Run health check)
- `web:event_list` → `/` (upcoming) and `/events/`
- `web:event_detail` → `/events/<slug>/`
- `web:calendar` → `/calendar/`
- `web:archive` → `/archive/`
- `web:series_detail` → `/festivals/<slug>/`
- `web:venue_detail` (v2 stub, optional) → `/venues/<slug>/`
- `web:submit` → `/submit/`
- `web:ics_feed` → `/calendar.ics` (query params `genre`, filters)
- Sitemaps at `/sitemap.xml` + segmented children; `robots.txt`; `llms.txt`.
- `apps.ingest.views.inbound_email` → `/ingest/email/` (not in `web:` namespace)
- MCP → `/mcp` (streamable HTTP); discovery `/.well-known/mcp.json`.

## Template layout

`templates/base.html`, `templates/web/event_list.html`, `event_detail.html`,
`calendar.html`, `archive.html`, `series_detail.html`, `submit.html`,
partials under `templates/web/partials/` (e.g. `event_card.html`,
`event_list_results.html` for HTMX swaps). Tailwind built to
`app/static/dist/`. Component source: Flowbite/Preline (plain HTML).

## Publishing/query rules (bind Plans 2, 4, 5)

- Public pages and MCP expose ONLY `status=PUBLISHED` events.
- "Upcoming" = `status=PUBLISHED AND start_at >= now()`, ordered `start_at` asc.
- "Archive/past" = `status=PUBLISHED AND start_at < now()`, ordered `start_at` desc.
- A reusable manager/queryset method `Event.objects.published()` and
  `.upcoming()` / `.past()` is added in Plan 2, Task 1, and consumed by Plan 4/5.

## Confidence gate (bind Plan 4)

- High confidence (auto-publish → `status=PUBLISHED`): origin type in {FEED, JSONLD,
  API} AND all required fields present (title, genre, start_at, venue) AND no fuzzy
  dedup collision. Set `confidence >= 0.8`.
- Low confidence (→ `status=REVIEW`): poster/vision extraction, HTML→LLM extraction,
  any FORM/EMAIL/SOCIAL origin, missing required field, or dedup collision.

## SEO/JSON-LD (bind Plan 2)

`schema.org/Event` JSON-LD in initial HTML of each detail page: `name`, `startDate`
(ISO-8601 with +05:30 offset), `endDate` if present, `location` (Place + address),
`performer` (from EventArtist), `offers` (with `priceCurrency` when ticketed),
`eventStatus`, `image` (poster). Series pages use evergreen URLs.
