# Bengaluru Classical

An open-source aggregator for **hardcore Karnatic and Hindustani classical music
concerts in Bengaluru** — traditional, raga-based performances only (no
film/fusion/western/pop).

There is no single place to find out which classical concerts are happening in the
city. This project aggregates them from sabha websites, event feeds, forwarded
posters, and public submissions into one fast, mobile-friendly, SEO- and AI-native
site — with a permanent archive of the city's classical concert history.

## Status

Planning complete. See the specifications:

- [`docs/problem.md`](docs/problem.md) — the problem and data-sourcing challenges.
- [`docs/technical.md`](docs/technical.md) — architecture, stack, pipeline, SEO,
  MCP, cost.
- [`docs/superpowers/specs/2026-07-20-bengaluru-classical-aggregator-design.md`](docs/superpowers/specs/2026-07-20-bengaluru-classical-aggregator-design.md)
  — the decision record.

## Stack (planned)

Django + HTMX + Tailwind · Supabase Postgres · Google Cloud Run · Gemini (poster
extraction) · FastMCP (AI-native from day 1). Target running cost: < ₹500/month.

## License

See [LICENSE](LICENSE).
