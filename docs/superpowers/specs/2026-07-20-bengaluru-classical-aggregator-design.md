# Design — Bengaluru Classical Concert Aggregator

Date: 2026-07-20
Status: Approved (brainstorming complete)

This is the consolidated design agreed during brainstorming. Full detail lives in
[`../../problem.md`](../../problem.md) (the problem) and
[`../../technical.md`](../../technical.md) (the how). This file is the decision
record.

## What we're building

A database-backed, mobile-first, SEO- and AI-native website that aggregates
**hardcore Karnatic and Hindustani classical concerts in Bengaluru** (traditional
raga-based, no film/fusion/western/pop), with a robust multi-source ingestion
pipeline and a public submission path. Open source, near-zero cost, designed to
extend to other cities later.

## Decisions locked

| Decision | Choice |
|---|---|
| Curation policy | **Auto-publish with confidence gate** — high-confidence machine reads auto-publish; posters, form submissions, and ambiguous scrapes go to a review queue. |
| V1 scope | Upcoming list + event detail pages; calendar + ICS subscribe; **public event submission** from day 1. |
| Ecosystem | "Whatever fits best" → **Django monolith** (Python). |
| Stack | Django 5.x + HTMX + Tailwind v4 + Flowbite/Preline; Supabase Postgres (free, Mumbai); GCS; Cloud Run + Cloud Scheduler (asia-south1); Cloudflare Email Worker; Gemini Flash extraction; FastMCP. **No React** (explicitly considered and rejected). |
| Budget | **< ₹500/month.** |
| Poster inbox | Private email address, **never shared/published**; the only public door is the on-site **form**, which relays to that mailbox. |
| Instagram/Facebook | **Manual-assisted at launch** (maintainer forwards posters); paid automation deferred. |
| Posters | **Show them, takedown on request** (visible contact policy). |
| Domain | To be purchased (.in). Candidates: **bengaluruclassical.in** (recommended, exact-match SEO), kacheribengaluru.in, rasikabengaluru.in, baithakblr.in. Final pick deferred. |
| Account separation | All runtime + API usage on personal `bharath12345@gmail.com`; employer `bharadwaj@conviva.com` is only the coding-assistant login. Hard rule. |

## Architecture summary

Single Django monolith = public site (SSR) + moderation backoffice (free Django
admin) + MCP server. Ingestion runs as scheduled Cloud Run Jobs feeding a
`RawIngest → extract → dedup → confidence gate → publish/review` flow. `city` is a
first-class dimension for future multi-city expansion. See technical spec for the
full diagram, data model, and pipeline cascade.

## Why this shape (grounded in research)

Every prior attempt at this (kutcheris.com, Sangeetnama Pune, KP Jayan's Bengaluru
page, EventsHigh…) died of **single-maintainer transcription burnout**. The design
imperative is therefore: **automate acquisition; the human only confirms, never
types.** Most real inventory is free-entry sabha concerts that never hit ticketing
platforms and often live only as WhatsApp poster JPEGs — so posters are a
first-class input and the pipeline stores raw artifacts for reprocessing and
monitors per-source health against seasonal dormancy and domain decay.

## Out of scope for v1

Artist/venue pages, user accounts, digests/alerts, paid social automation,
multi-city launch, full Kannada UI — all documented as future work, with the data
model prepared for them.
