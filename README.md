# Bengaluru Classical

An open-source aggregator for **hardcore Karnatic and Hindustani classical music
concerts in Bengaluru** — traditional, raga-based performances only (no
film/fusion/western/pop).

There is no single place to find out which classical concerts are happening in the
city. This project aggregates them from sabha websites, event feeds, forwarded
posters, and public submissions into one fast, mobile-friendly, SEO- and AI-native
site — with a permanent archive of the city's classical concert history.

## Status

Planning complete — full implementation plan written across six phases, awaiting
review before any code is written.

### Specifications
- [`docs/problem.md`](docs/problem.md) — the problem and data-sourcing challenges.
- [`docs/technical.md`](docs/technical.md) — architecture, stack, pipeline, SEO,
  MCP, cost.
- [`docs/superpowers/specs/2026-07-20-bengaluru-classical-aggregator-design.md`](docs/superpowers/specs/2026-07-20-bengaluru-classical-aggregator-design.md)
  — the decision record.

### Implementation plans (sequential)
- [`plans/CONVENTIONS.md`](docs/superpowers/plans/CONVENTIONS.md) — shared
  cross-plan interfaces every plan honors.
- [Plan 1 — Foundation & data model](docs/superpowers/plans/2026-07-20-plan-1-foundation-and-data-model.md)
- [Plan 2 — Public site](docs/superpowers/plans/2026-07-20-plan-2-public-site.md)
- [Plan 3 — Submission & inbound email](docs/superpowers/plans/2026-07-20-plan-3-submission-and-inbound-email.md)
- [Plan 4 — Ingestion pipeline](docs/superpowers/plans/2026-07-20-plan-4-ingestion-pipeline.md)
- [Plan 5 — MCP server](docs/superpowers/plans/2026-07-20-plan-5-mcp-server.md)
- [Plan 6 — Deployment & infra](docs/superpowers/plans/2026-07-20-plan-6-deployment-and-infra.md)

## Stack (planned)

Django + HTMX + Tailwind · Supabase Postgres · Google Cloud Run · Gemini (poster
extraction) · FastMCP (AI-native from day 1). Target running cost: < ₹500/month.

## License

See [LICENSE](LICENSE).
