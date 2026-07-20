# Pipeline Cloud Run Job wiring

Management commands (deployed as Cloud Run Jobs in Plan 6):

```bash
uv run python manage.py run_scrapers
uv run python manage.py process_raw_ingests
```

`run_scrapers` iterates active `Source` rows, runs registered fetchers, and creates
`RawIngest` artifacts. `process_raw_ingests` extracts candidates, deduplicates,
applies the confidence gate, and publishes or queues for review.
