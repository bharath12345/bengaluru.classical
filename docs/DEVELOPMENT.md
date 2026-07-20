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
