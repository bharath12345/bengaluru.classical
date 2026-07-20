# Technical Specification — Bengaluru Classical Concert Aggregator

This document describes *how* the system in [`problem.md`](./problem.md) is built.
All choices target the stated constraints: beautiful & mobile-first, low latency,
SEO-optimized, AI-native (MCP from day 1), scalable (incl. future multi-city),
near-zero cost (< ₹500/month), and open source. Findings are current as of
July 2026; where 2026 reality diverges from older common advice, it is flagged.

## 1. Architecture at a glance

A **single Django monolith** serves the public site, the moderation backoffice
(Django admin), and the MCP server; a set of **Cloud Run Jobs** run the ingestion
pipeline on a schedule. One language (Python), one codebase, one deploy story —
matching the maintainer's Python fluency and the `mutual_funds` project's proven
GCP pattern.

```
                 ┌────────────────── Cloud Scheduler (cron, free) ──────────────────┐
                 ▼                                                                    ▼
        Cloud Run Job: scrapers                                        Cloud Run Job: (future)
        (feeds→JSON-LD→API→HTML→JS)                                    social automation
                 │                                                                    │
                 ▼                                                                    │
   ┌──────────── RawIngest (verbatim blob → GCS) ◄── Cloudflare Email Worker ◄── private mailbox
   │                                            ◄── public Submit form (relays to mailbox)
   ▼
 Extractors (feed parser / HTML→LLM / Gemini vision on posters)
   │
   ▼
 Candidate Event  ──►  Dedup  ──►  Confidence gate
                                     │            │
                              high & clean     low / poster / form
                                     │            │
                                     ▼            ▼
                               auto-publish   review queue (Django admin)
                                     │            │  (one-tap approve/edit/reject)
                                     └─────┬──────┘
                                           ▼
                                 Published Event (permanent URL + JSON-LD)
                                           │
                    ┌──────────────────────┼───────────────────────┐
                    ▼                       ▼                        ▼
             Public site (SSR)        ICS feeds              MCP server (read-only)
             + CDN cache            (calendar subscribe)     (streamable HTTP)
```

## 2. Technology stack

| Concern | Choice | Rationale |
|---|---|---|
| Web framework | **Django 5.x** (SSR) + **HTMX** + **Tailwind v4** | Perfect SSR/SEO; free production-grade admin as the moderation backoffice; Python fluency; HTMX gives instant filtering without a SPA. AI crawlers don't run JS — SSR puts JSON-LD in the initial HTML. |
| UI components/theme | **Flowbite / Preline** (free, plain-HTML Tailwind); optionally Tailwind Plus later | Modern component libraries are Tailwind markup; the plain-HTML variants drop straight into Django templates. No React needed. Distinctive visual identity applied on top (not a default template). |
| Database | **Supabase Postgres — free tier, Mumbai (ap-south-1)** | 500 MB Postgres with `tsvector`/`pg_trgm` full-text search; Mumbai region = lowest latency for Bengaluru. Accessed **server-side only** (see §7). Daily SSR traffic prevents the 7-day inactivity pause; add a cron ping as insurance; `pg_dump`→GCS backup cron. |
| Hosting | **Google Cloud Run**, `asia-south1` (Mumbai), scale-to-zero | Free-tier-friendly; proven in `mutual_funds`. Note asia-south1 is excluded from the always-free allotment, so expect low single-digit rupees, not literally zero. |
| CDN | CDN in front of Cloud Run (Cloud CDN or Cloudflare) | Cache rendered pages + poster images for low latency and to shield the DB. |
| Object storage | **Google Cloud Storage** | Raw ingest artifacts (audit/reprocess) + poster images served via CDN (WebP, lazy-loaded). |
| Scheduled jobs | **Cloud Scheduler** (free) → **Cloud Run Jobs** | Daily scrape runs; per-source cascade; Playwright available in a 2 GiB job when needed. |
| Inbound email | **Cloudflare Email Routing + Email Worker** (free) | Catches mail to the private address → drops raw MIME + attachments to GCS → pings Cloud Run. (SendGrid/Mailgun/Postmark free inbound tiers are all dead/paywalled in 2026.) |
| Poster/scrape extraction | **Gemini Flash / Flash-Lite** with structured output (Pydantic `response_schema`) | 2026: frontier VLMs beat OCR on real documents, incl. strong Indic-script performance; ~₹0.15/poster, free tier covers daily volume. Model ID kept in config (models deprecate). |
| MCP server | **FastMCP 2.x**, stateless streamable-HTTP, read-only, IP rate-limited | Python (same stack); stateless = forward-compatible with the MCP spec revision that removes sessions. Unauthenticated public read-only MCP is now precedented (e.g. Shopify). |
| CI/CD | **Cloud Build** (lint/test → deploy) + **Secret Manager** | Mirrors `mutual_funds`; secrets never in the repo or env files. |
| Observability | Structured logging (structlog) → Cloud Monitoring | Per-source health, pipeline runs, extraction confidence. |

### Approaches considered and rejected

- **Django + React (or Inertia.js):** the vast React theme ecosystem is
  overwhelmingly Tailwind markup wrapped in JSX; this site's interactivity is
  minimal, and client rendering harms the core SEO/AI-crawler requirement (crawlers
  don't execute JS) unless SSR is bolted on — added complexity for no benefit here.
  Django templates + HTMX + the same Tailwind components deliver the look without it.
- **Astro + FastAPI:** best template marketplace and sub-second cold starts, but
  two languages and a hand-built moderation UI. The free Django admin (the single
  biggest ongoing-effort saver) tipped the decision to Django.
- **FastAPI + Angular** (the `mutual_funds` stack): weak SEO/AI-crawler story for a
  public content site (client-rendered), so rejected here despite familiarity.

## 3. Data model

Postgres, accessed only server-side. Tables:

- **Event** — the concert. `title`, `genre` (karnatic|hindustani), `start_at`
  (tz-aware), `end_at`, `venue` (FK), `is_free`/`price`/`currency`, `source_url`
  (ticket/origin), `poster` (GCS ref), `description`, `status`
  (published|review|rejected|cancelled), `confidence` (float), `series` (FK,
  nullable), `dedup_key`, `city` (FK — Bengaluru now; the multi-city seam),
  `slug`, timestamps. One permanent URL each.
- **Artist** — `name`, `alt_names` (Kannada/transliterations), `primary_role`/
  instrument, `bio` (later). First-class from day 1 (pages are v2).
- **EventArtist** — join table: `event`, `artist`, `role` (vocal, violin,
  mridangam, tabla, harmonium, ghatam, …). A concert has many artists in roles.
- **Venue** — `name`, `area`, `address`, `geo` (lat/lng), `map_url`, `source_url`,
  `city` (FK).
- **Series** — recurring festivals (Ramanavami, Unnati Utsav, Gayana Samaja
  conference…). Backs the evergreen SEO pages.
- **Source** — the registry of ~50 origins: `type` (feed|jsonld|api|html|js|
  email|form|social), `url`/`handle`, `scrape_method`, `health_status`,
  `last_seen_at`, `active`, `seasonal` flag. Makes ingestion robust & monitorable.
- **RawIngest** — every inbound artifact stored verbatim: `source` (FK),
  `blob_ref` (GCS), `content_type`, `fetched_at`, `processed` status. Audit trail +
  reprocessing without re-fetch.
- **Submission** — public-form submissions, linked to the RawIngest they generate;
  `spam_score`, submitter contact (optional).

`city` on Event/Venue/Source is the **multi-city seam**: Bengaluru → other cities
becomes configuration + new Sources, not a schema change.

## 4. Ingestion pipeline

Runs as Cloud Run Jobs (scheduled) plus one always-available inbound endpoint.

### 4.1 Scheduled scrapers — per-source cascade (cheap → expensive)

For each active `Source`, attempt in order and stop at first success:

1. **ICS/iCal feed** (e.g. Bangalore International Centre; any WordPress "The
   Events Calendar" sites) — deterministic, free, no LLM.
2. **Embedded `schema.org/Event` JSON-LD** (e.g. Indian Music Experience) —
   deterministic, free.
3. **Open API** where present (e.g. SPIC MACAY GraphQL) — treated as fragile,
   wrapped in health checks and fallbacks.
4. **Clean HTML** (Nadasurabhi, Sri Rama Lalitha Kala Mandira, Ramanavami
   samithis, Bhavan, …) — fetch with `httpx`/`curl_cffi`, feed cleaned text to
   **Gemini Flash-Lite structured extraction** rather than hand-writing brittle
   per-site parsers. LLM-schema extraction is the 2026 standard and survives
   layout changes; check for embedded JSON-LD first (free/deterministic).
5. **Playwright fallback** — only for JS-heavy pages (available in a 2 GiB job).

### 4.2 Poster / image extraction

Any poster JPEG (from email forwards, the public form, or a scraped poster image)
→ **Gemini Flash vision** with a structured Pydantic schema and few-shot
Kannada/English poster examples, guarded with "extract only text visible in the
image" to curb hallucination. All poster extractions are treated as **low
confidence** (→ review queue).

### 4.3 Inbound email

The private mailbox receives (a) the maintainer's deliberate poster forwards and
(b) everything relayed by the **public Submit form**. A **Cloudflare Email
Worker** catches mail to that address, stores raw MIME + attachments in GCS, and
pings a Cloud Run endpoint → `RawIngest`. The address is **never published**; the
only public inbound door is the form. Large-MIME parsing is offloaded to Cloud Run
(not done inside the Worker).

### 4.4 Confidence gate (policy: auto-publish with confidence gate)

Each candidate Event is scored:

- **High** — feed/JSON-LD/API origin, all required fields present (title, genre,
  `start_at`, venue), clean dedup → **auto-publish**.
- **Low** — poster vision, ambiguous scrape, missing required field, fuzzy dedup
  collision, or **any public-form submission** → **review queue**.

### 4.5 Deduplication

The same concert appears in 3+ sources. Dedup key = (date + venue + fuzzy artist
match). Later duplicates attach as **additional Source attributions** on the
existing Event rather than creating a new row.

### 4.6 Review queue = Django admin

The moderation backoffice is the built-in Django admin (free, production-grade):
a list of pending candidates showing poster preview + extracted fields + source
attribution, with approve / edit / reject in one screen. This is the anti-burnout
lever — the human **confirms** machine work, never transcribes.

### 4.7 Source health & seasonality

Every run records success/failure per source. Dead domains and dormant seasonal
sources are flagged (not silently dropped); a simple "last seen per source" view
tells the maintainer when a site breaks or a season reactivates.

### 4.8 Robustness principles (baked in)

Raw-artifact-first (always reprocessable) · method cascade (cheap→expensive) ·
LLM extraction over brittle parsers · per-source health monitoring · human
confirmation only where confidence is low.

## 5. Frontend, performance & SEO

### 5.1 Look & feel

Django templates + Tailwind v4 + Flowbite/Preline components: event cards,
month calendar, filter bars, poster grids. **HTMX** powers instant filtering and
pagination with no page reloads and no SPA. **Mobile-first** (most arrivals are
WhatsApp links opened on phones). A deliberate visual identity — clean editorial
typography, a classical-inspired accent palette, posters as the visual anchor —
applied via the frontend-design process, not a stock template.

### 5.2 Performance / low latency

Pure SSR → fast first paint and full visibility to AI crawlers. Cloud Run in
`asia-south1` behind a CDN caching rendered pages; posters served from GCS via CDN
as lazy-loaded WebP. An optional single warm instance (~₹900/mo) is available if
cold starts ever annoy — **off by default** to stay in budget.

### 5.3 SEO (a core requirement, designed in)

- **`schema.org/Event` JSON-LD in the initial HTML** of every event page: `name`,
  ISO-8601 `startDate` with UTC offset, physical `location` + full address,
  `performer`, `offers` (with `priceCurrency` for ticketed), `eventStatus`. Makes
  events eligible for Google's Events surface and citable by AI Overviews/agents.
- **URL architecture:** one permanent leaf URL per concert **plus** one evergreen
  URL per recurring series/festival (accrues ranking year over year — Google's own
  advice). Markup lives on unique leaf pages (listing pages don't qualify).
- **Past events stay live (200) and get enriched** with artist/raga/program
  detail — the archive is the moat and a major traffic driver on comparable sites.
  Moved to an archive sitemap; never blanket-redirected (avoids soft-404).
- **Segmented sitemaps** (upcoming / archive / venues / artists) with honest
  `lastmod`; canonical URLs; OpenGraph/Twitter cards using the poster so WhatsApp
  shares render richly.
- On cancellation: keep the event data, flip `eventStatus` (don't delete).

### 5.4 AI-native (MCP from day 1)

- **FastMCP stateless streamable-HTTP** server, read-only, no auth, IP
  rate-limited (token bucket; 429 with reset headers; Origin validation), on the
  same Cloud Run service. Tools: `search_events(date_range, genre, venue, artist,
  area)`, `get_event(id)`, `list_venues`, `list_artists`.
- **Discovery:** publish to the MCP Registry; serve `/.well-known/mcp.json`; ship
  `llms.txt` for agentic browsers (shipped knowing Google ignores it for SEO).
- Net effect: an assistant answering "Carnatic concerts in Bengaluru this weekend"
  can return **our** structured data.

## 6. Repository & deployment

Open source, public on GitHub under the maintainer's personal account, permissive
license (MIT or Apache-2.0). Indicative layout:

```
docs/            problem.md, technical.md, superpowers/specs/<design>.md
app/             Django project — apps: site, events, sources, ingest
pipeline/        scrapers, extractors, email handler (Cloud Run Jobs)
mcp/             FastMCP server
infra/           Cloud Build config, Cloud Run / Scheduler definitions
```

CI/CD via **Cloud Build** (lint → test → deploy), secrets in **Secret Manager**,
structured logging to Cloud Monitoring — mirroring the `mutual_funds` setup.

## 7. Account separation (hard constraint)

- **All runtime and paid API usage lives on the maintainer's personal Google
  identity `bharath12345@gmail.com`**: Cloud Run, Cloud Scheduler, GCS, Secret
  Manager, Supabase, Cloudflare, and the **Gemini API key** (personal AI Studio /
  GCP), all in `asia-south1`/Mumbai.
- The employer identity `bharadwaj@conviva.com` is used **only** as this coding
  assistant's login. **No Conviva credentials, projects, billing, or API keys ever
  touch this project.** This is a standing rule for all future work here.

## 8. Cost model (target < ₹500/month)

| Item | Monthly cost |
|---|---|
| Cloud Run (scale-to-zero) + Scheduler + GCS | ~₹0 – low single digits (asia-south1 not free-tier) |
| Supabase Postgres (free, Mumbai) + pg_dump→GCS backup | ₹0 |
| Cloudflare inbound email | ₹0 |
| Gemini poster/scrape extraction | ₹0 free tier → a few ₹ if volume grows |
| Domain (.in) | ~₹800/yr ≈ ₹70/mo |
| Instagram (manual-assisted at launch) | ₹0 |
| **Total** | **comfortably < ₹500/mo** |

The single cost variable is an optional warm Cloud Run instance (~₹900/mo) if cold
starts become a problem — deferred and off by default.

## 9. Future work (documented, not built)

- Artist and venue landing pages (data model already supports them).
- Email digest / newsletter; follow-an-artist alerts; user accounts.
- Paid Instagram/Facebook automation (ScrapeCreators/Apify) or Business Discovery
  API for sanctioned IG ingestion.
- SerpApi Google Events engine as an indirect ticketing-platform fallback.
- **Multi-city expansion** — enabled by the `city` dimension; new city = config +
  new Sources, not a rewrite.
- Full Kannada UI.

## 10. Key "2026 ≠ 2024" notes for implementers

- SendGrid/Mailgun/Postmark free **inbound** email tiers are dead/paywalled →
  Cloudflare Email Workers is the answer.
- Gemini free tier was cut sharply (Dec 2025); "1,500 RPD" figures are stale —
  check the live dashboard. Keep the model ID in config (2.5 Flash deprecates
  Oct 2026).
- VLMs now beat OCR for posters — no "Cloud Vision then LLM" pipeline.
- Instagram Basic Display API is dead; reliable scraping needs paid APIs — hence
  manual-assisted at launch.
- LLM-schema extraction has replaced hand-written per-site parsers as standard.
- MCP goes stateless (spec revision, mid-2026); SSE transport is sunset — build
  stateless streamable-HTTP.
- `llms.txt` confirmed SEO-irrelevant by Google — ship it only for agentic
  browsers.
- Supabase was briefly ISP-blocked in India (Feb 2026) — **all DB access must be
  server-side**, never from Indian browsers.
- Cloud SQL still has no free tier; Astro DB was removed; LiteFS is abandoned
  (Litestream is fine) — reasons the Supabase-free choice stands.
