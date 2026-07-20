# Problem Specification — Bengaluru Classical Concert Aggregator

## 1. The problem

Bengaluru has a large, continuous stream of **hardcore Indian classical music
concerts** — traditional, raga-based Karnatic (Carnatic) and Hindustani
performances in the conventional concert setting. This explicitly **excludes**
film/Bollywood, western, pop, and fusion/improvisation-led music.

There is **no reliable website that aggregates all such concerts happening in the
city**. A rasika who wants to know "what hardcore classical concerts are on this
weekend in Bengaluru" has no single answer. Information is fragmented across
dozens of sabha websites, social media pages, WhatsApp forwards, printed
brochures, and a few ticketing platforms — none of which is complete, and most of
which skew toward non-classical events.

## 2. Who it is for

- **Primary user:** rasikas (classical music listeners) in Bengaluru who want a
  single, trustworthy, up-to-date list of upcoming Karnatic and Hindustani
  concerts, filterable by genre, date, venue, and area of the city, and usable
  primarily on a mobile phone (most discovery happens via WhatsApp-shared links).
- **Secondary user:** the same rasikas consulting the **historical archive** —
  which artists performed where and when — as a record of the city's classical
  scene.
- **AI assistants** acting on behalf of rasikas: the site is AI-native (MCP + rich
  structured data) so an assistant can answer "Carnatic concerts in Bengaluru this
  weekend" from our data.
- **The maintainer (you):** who must be able to keep the site current with
  **minimal manual effort** — the explicit anti-goal is hand-transcription.

## 3. Why this is hard: the data-sourcing challenge

This project is, at its core, a **data acquisition problem**, not a UI problem.
Research into the Bengaluru landscape (2026) established the following realities,
which shape the entire design.

### 3.1 The real inventory barely touches ticketing platforms

Most hardcore-classical concerts in Bengaluru are **free or donation-funded**
(unlike Chennai's sabha model), so they leave **no ticketing trail**. The
inventory lives across five tiers of source, in decreasing machine-readability:

- **Tier 1 — Machine-readable feeds/APIs** (~a handful): Bangalore International
  Centre (public iCal feed), Indian Music Experience (JSON-LD + per-event iCal),
  SPIC MACAY Karnataka (an undocumented, possibly-fragile public GraphQL API).
- **Tier 2 — Clean HTML, no feeds** (~8–10 sites, trivially scrapeable): Sri Rama
  Lalitha Kala Mandira, Nadasurabhi, Sree Ramaseva Mandali (Chamarajpet
  Ramanavami), Seshadripuram Ramaseva Samithi, Bharatiya Vidya Bhavan, Sangamam
  India, Sangeet Sadhana, Indiranagar Sangeetha Sabha.
- **Tier 3 — Messy HTML** (prose + scanned invitation images): Bangalore Gayana
  Samaja, BTM Cultural Academy.
- **Tier 4 — Poster/image-only** (Instagram/Facebook JPEGs, needs vision/OCR):
  Sapthak, Ananya, SGBS Unnati Trust (Gokulashtami "Utsav"), Karnataka Ganakala
  Parishat, Bhoomija, Sree Ramakrishna Bhajana Sabha.
- **Tier 5 — Fully offline** (posters, banners, newspapers, phone): MES Kalavedi,
  Malleswaram Sangeetha Sabha, temple concert series, and many neighbourhood
  samithis — reachable only through human/community submission.

Machine-readable sources (Tiers 1–2) cover perhaps **40–50%** of hardcore-classical
volume. The remaining majority requires vision extraction of posters and/or human
submission.

### 3.2 Ticketing platforms are the *worst* sources, not the best

- **BookMyShow** — richest *ticketed* classical inventory, but sits behind Akamai/
  Cloudflare bot management; even its sitemaps return 403. Not reliably scrapeable.
- **District (by Zomato)** (absorbed insider.in/Paytm Insider) — technically
  easiest (public sitemap), but thin classical inventory and its ToS **explicitly
  bans scraping**.
- **AllEvents.in** — best classical inventory of any platform, but ToS explicitly
  bans scraping (incl. an anti-AI-training clause); official API is ~$500+/mo and
  refuses hobbyists.
- **Eventbrite / Townscript / TicketGenie / others** — near-zero real Bengaluru
  classical inventory and/or scraping bans.

Conclusion: **robots-respecting ingestion of primary sources (sabhas) is the
defensible, high-yield path.** Ticketing platforms are a low-priority, legally
fraught, low-classical-yield fallback. (SerpApi's Google Events engine is a
possible paid indirect fallback if ever needed — it offloads ToS exposure.)

### 3.3 Social media is where posters live, but hard to automate cheaply

Instagram is the de-facto announcement channel for many sabhas, but the Basic
Display API is dead (Dec 2024) and self-hosted scraping from datacenter IPs is
blocked almost immediately. Reliable automation needs a **paid** scraper API
(~₹900–2500/mo), which exceeds the near-zero budget. Facebook is effectively dead
as an automatable source. **Decision: at launch, Instagram/Facebook are handled
"manual-assisted"** — the maintainer follows key pages personally and forwards
any concert poster into the same pipeline as everything else. Paid automation is a
documented future option.

### 3.4 The community already runs on forwarded posters

Information in this community flows primarily through **WhatsApp poster forwards**,
admin-mediated invite groups, printed programme sheets (Ramanavami season prints
~1 lakh metre-long schedules), sabha journals, and word of mouth. The unit of
information is the **poster JPEG**. Any successful system must ingest posters as a
first-class input, not treat them as an afterthought.

### 3.5 Seasonality and infrastructure decay

- **Season anchors** dominate: Ramanavami (Mar–May) is Bengaluru's equivalent of
  Chennai's Margazhi; Gokulashtami/Unnati Utsav (Aug); Bengaluru Ganesh Utsava
  (Aug–Sep); November conference season; Jan–Feb aradhana season. Many sources are
  **dormant most of the year and reactivate seasonally** (some domains even park
  off-season).
- **Source domains decay**: several org domains are dead or intermittently down
  (e.g. kgkp.org, bhoomija.org, ananyabengaluru.com). The pipeline must monitor
  per-source health and not silently go stale.

### 3.6 Every prior attempt died the same way

Comparable projects (kutcheris.com, Sabhash, carnatic.community, Sangeetnama Pune,
KP Jayan's Bengaluru WordPress page with 690 reader comments, EventsHigh) all
**died from single-maintainer hand-transcription burnout and zero revenue**. The
survivors (chennaievent.com, MDnD) run on **organizer/community self-submission**
and/or transaction coupling. Demand is proven (a single rasikas.org season thread
drew 453K views). **The central design imperative is therefore: minimize manual
transcription. Automate acquisition; let the human only *confirm*, never *type*.**

The one direct live competitor is **indianclassical.net** (multi-city, includes
Bengaluru) — a reference point, not a blocker, for a Bengaluru-focused site with
deeper sourcing.

## 4. Requirements

### 4.1 Functional (v1)

- **Upcoming events** list with filters: genre (Karnatic/Hindustani), date range,
  venue, area of city, free/ticketed.
- **Event detail page** per concert: poster, artists with roles, venue + map,
  ticket/source link, source attribution, permanent URL.
- **Calendar view** + subscribable **ICS feed** (incl. filtered variants, e.g.
  Hindustani-only) so events push into users' own calendars.
- **Public event submission**: a form (poster upload and/or structured fields)
  that anyone can use; feeds the ingestion pipeline via the private mailbox.
- **Past events archive**: every event stays live permanently at its URL and is
  enriched over time.
- **English UI**; Kannada artist/venue names shown as given by sources.

### 4.2 Functional (data acquisition)

- Ingest from: scheduled scrapers (feeds → JSON-LD → APIs → clean HTML → JS
  fallback), poster vision extraction, forwarded email, and the public form.
- **Confidence-gated publishing**: high-confidence, structurally-clean
  extractions auto-publish; low-confidence ones (all poster vision, all public-form
  submissions, ambiguous scrapes) enter a **review queue** for one-tap approval.
- **Deduplication**: the same concert from multiple sources collapses to one
  event with multiple source attributions.
- **Raw-artifact retention**: every inbound artifact is stored verbatim before
  extraction, so any extraction can be reprocessed without re-fetching.
- **Per-source health monitoring** and seasonal-reactivation awareness.

### 4.3 Non-functional

- **Beautiful and mobile-first** on web and phone.
- **Low latency** (server-rendered, CDN-cached).
- **SEO-optimized**: schema.org/Event JSON-LD, eligible for Google's Events
  surface, evergreen URLs for recurring festivals, enriched living archive.
- **AI-native from day 1**: a read-only MCP server plus discovery metadata.
- **Scalable**: past history retained indefinitely; **city is a first-class
  dimension** so the system can extend beyond Bengaluru later without a rewrite.
- **Near-zero running cost** (target < ₹500/month).
- **Open source** on GitHub.
- **Strict account separation** (see technical spec): all runtime and API usage on
  the maintainer's personal Google identity; the employer identity is never
  involved.

## 5. Explicit non-goals (v1 / YAGNI)

- No film/fusion/western/pop coverage — hardcore raga-based classical only.
- No paid Instagram/Facebook automation at launch (manual-assisted instead).
- No artist/venue landing pages at launch (data modelled for them; pages are v2).
- No user accounts, follow-artist alerts, or email digests at launch.
- No multi-city launch (designed for, not built).
- No direct scraping of the maintainer's personal mailbox or WhatsApp — the only
  inbound channels are the public form and deliberate forwards to a private
  address.
- No republishing of poster images against an organizer's wishes — posters are
  shown (organizers overwhelmingly want the publicity) with a visible takedown
  contact policy.

## 6. Success criteria

- A rasika can, on a phone, in under 10 seconds, see the hardcore-classical
  concerts on in Bengaluru this weekend, filtered to their genre.
- The maintainer spends **minutes per week, not hours** — confirming machine-
  extracted events, not transcribing them.
- Machine-readable sources ingest with **no manual step**; posters and form
  submissions take **one tap to approve**.
- Events appear in Google's Events surface and are answerable by AI assistants via
  MCP.
- The archive grows into the definitive historical record of Bengaluru's classical
  concert scene.
