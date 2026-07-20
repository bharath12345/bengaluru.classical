# Plan 1 — Foundation & Data Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Django project skeleton with a local Postgres dev/test loop and the complete relational data model (cities, venues, artists, events, series, sources, raw ingests, submissions) exposed through a review-oriented Django admin.

**Architecture:** A single Django 5 project managed with `uv`. Settings are split into `base`/`dev`/`prod` and read from the environment via `dj-database-url`. Local development and tests run against a Postgres 16 container (via Docker Compose) so trigram/full-text features match production Supabase. Domain models live in focused Django apps (`core`, `events`, `sources`, `ingest`); the built-in Django admin is the moderation backoffice. Tests are TDD-first with `pytest`, `pytest-django`, and `factory_boy`.

**Tech Stack:** Python 3.13, Django 5.x, PostgreSQL 16, `uv`, `ruff`, `pytest` + `pytest-django`, `factory_boy`, `dj-database-url`, `psycopg[binary]`, `django-extensions` (dev).

## Global Constraints

- Python version floor: **3.13** (`requires-python = ">=3.13"`).
- Django: **5.x** (`>=5.1,<6.0`).
- Database engine is **PostgreSQL only** — never add SQLite fallbacks; local + test + prod all use Postgres.
- **Account separation (hard rule):** all runtime/API usage and git authorship use the personal identity `bharath12345@gmail.com`; the employer identity `bharadwaj@conviva.com` is never referenced in code, config, or commits. Git commits set `user.email=bharath12345@gmail.com`, `user.name=Bharadwaj`.
- **Secrets never committed:** all secrets come from environment variables; `.env` is gitignored (already present).
- `city` is a first-class FK on `Venue`, `Event`, and `Source` — the multi-city seam. Seed exactly one city: `Bengaluru`.
- Genre is a fixed choice set: `karnatic`, `hindustani`.
- Event `status` choice set: `review`, `published`, `rejected`, `cancelled`. Default `review`.
- All datetimes are timezone-aware; `TIME_ZONE = "Asia/Kolkata"`, `USE_TZ = True`.
- Naming: apps and modules are lowercase; models are singular PascalCase; the join model is `EventArtist`.

---

## File Structure

```
pyproject.toml                     # uv project + deps + tool config (ruff, pytest)
uv.lock                            # lockfile (generated)
docker-compose.yml                 # local Postgres 16
.env.example                       # documented env vars (committed)
manage.py                          # Django entrypoint
conftest.py                        # pytest root config / fixtures
config/                            # Django project package
  __init__.py
  settings/
    __init__.py
    base.py                        # shared settings
    dev.py                         # local dev settings
    prod.py                        # production settings (used later)
    test.py                        # test settings
  urls.py
  wsgi.py
  asgi.py
apps/
  core/                            # City, Venue, Artist, Series + shared base
    __init__.py
    apps.py
    models.py
    admin.py
    migrations/
    factories.py
    tests/
      __init__.py
      test_core_models.py
  events/                          # Event, EventArtist
    __init__.py
    apps.py
    models.py
    admin.py
    migrations/
    factories.py
    tests/
      __init__.py
      test_event_models.py
  sources/                         # Source registry
    __init__.py
    apps.py
    models.py
    admin.py
    migrations/
    factories.py
    tests/
      __init__.py
      test_source_models.py
  ingest/                          # RawIngest, Submission
    __init__.py
    apps.py
    models.py
    admin.py
    migrations/
    factories.py
    tests/
      __init__.py
      test_ingest_models.py
```

Split rationale: `core` holds the stable descriptive entities (city/venue/artist/series) that everything references; `events` holds the central Event aggregate and its artist join; `sources` holds the ingestion registry; `ingest` holds raw inbound artifacts and public submissions. Files that change together live together (each app owns its models + admin + factories + tests).

---

### Task 1: Project bootstrap (uv, Django, Postgres, tooling)

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `manage.py`
- Create: `config/__init__.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`
- Create: `config/settings/__init__.py`, `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`, `config/settings/test.py`
- Create: `conftest.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `DJANGO_SETTINGS_MODULE` defaults to `config.settings.dev` for `manage.py`, `config.settings.test` under pytest.
  - `config.settings.base.INSTALLED_APPS` includes the four local apps `apps.core`, `apps.events`, `apps.sources`, `apps.ingest` (added in later tasks — leave placeholders that later tasks append to).
  - Database configured from env var `DATABASE_URL` (default `postgres://blr:blr@localhost:5432/blr_classical`).
  - A `pytest` invocation `uv run pytest` runs green (with a trivial smoke test).

- [ ] **Step 1: Create the uv project file**

```toml
# pyproject.toml
[project]
name = "bengaluru-classical"
version = "0.1.0"
description = "Aggregator for hardcore Karnatic and Hindustani classical concerts in Bengaluru"
requires-python = ">=3.13"
dependencies = [
    "django>=5.1,<6.0",
    "psycopg[binary]>=3.2",
    "dj-database-url>=2.2",
]

[dependency-groups]
dev = [
    "ruff>=0.6",
    "pytest>=8.3",
    "pytest-django>=4.9",
    "factory-boy>=3.3",
    "django-extensions>=3.2",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "DJ"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py"]
addopts = "-ra"
```

- [ ] **Step 2: Create the local Postgres compose file**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: blr
      POSTGRES_PASSWORD: blr
      POSTGRES_DB: blr_classical
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U blr -d blr_classical"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 3: Create the documented env example**

```bash
# .env.example — copy to .env and adjust. .env is gitignored.
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=dev-insecure-change-me
DJANGO_DEBUG=1
# Database (local Postgres from docker-compose)
DATABASE_URL=postgres://blr:blr@localhost:5432/blr_classical
```

- [ ] **Step 4: Create `manage.py`**

```python
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create the settings package**

```python
# config/settings/__init__.py
```

```python
# config/settings/base.py
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # local apps (appended by later tasks)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgres://blr:blr@localhost:5432/blr_classical"),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

```python
# config/settings/dev.py
from .base import *  # noqa: F401,F403

DEBUG = True
INSTALLED_APPS += ["django_extensions"]  # noqa: F405
```

```python
# config/settings/prod.py
from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Further production hardening added in the deployment plan.
```

```python
# config/settings/test.py
from .base import *  # noqa: F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
```

- [ ] **Step 6: Create urls / wsgi / asgi**

```python
# config/urls.py
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
```

```python
# config/wsgi.py
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
```

```python
# config/asgi.py
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_asgi_application()
```

- [ ] **Step 7: Create root conftest with a smoke test target**

```python
# conftest.py
# Root pytest configuration. pytest-django reads DJANGO_SETTINGS_MODULE from
# pyproject.toml ([tool.pytest.ini_options]). Shared fixtures are added by later tasks.
```

Also create the smoke test now:

```python
# apps/__init__.py  (create empty so "apps" is importable)
```

```python
# tests_smoke.py  (temporary root smoke test — deleted in Task 2 Step 1)
def test_smoke():
    assert 1 + 1 == 2
```

- [ ] **Step 8: Install deps and start the database**

Run:
```bash
uv sync
docker compose up -d db
```
Expected: `uv sync` resolves and writes `uv.lock`; `docker compose` reports the `db` container healthy (verify with `docker compose ps`).

- [ ] **Step 9: Run the smoke test to verify the toolchain**

Run: `uv run pytest tests_smoke.py -v`
Expected: PASS (1 passed).

- [ ] **Step 10: Verify Django check passes against Postgres**

Run: `uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 11: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "chore: bootstrap Django project with uv, Postgres, and tooling"
```

---

### Task 2: `core` app — City, Venue, Artist, Series

**Files:**
- Create: `apps/core/__init__.py`, `apps/core/apps.py`, `apps/core/models.py`, `apps/core/admin.py`, `apps/core/factories.py`
- Create: `apps/core/tests/__init__.py`, `apps/core/tests/test_core_models.py`
- Modify: `config/settings/base.py` (append `"apps.core"` to `INSTALLED_APPS`)
- Delete: `tests_smoke.py`

**Interfaces:**
- Consumes: settings/app scaffolding from Task 1.
- Produces (relied on by Tasks 3–5):
  - `apps.core.models.City(name: str, slug: str, is_active: bool)` — `__str__` → name; unique `slug`.
  - `apps.core.models.Venue(name, area, address, latitude, longitude, map_url, source_url, city: FK[City], slug)` — `__str__` → name; unique `slug`.
  - `apps.core.models.Artist(name, alt_names: list[str], primary_role, bio, slug)` — `__str__` → name; unique `slug`; `alt_names` is a `JSONField(default=list)`.
  - `apps.core.models.Series(name, description, city: FK[City], slug)` — `__str__` → name; unique `slug`.
  - `apps.core.models.TimeStampedModel` — abstract base with `created_at`, `updated_at`.
  - Factories: `CityFactory`, `VenueFactory`, `ArtistFactory`, `SeriesFactory` (in `apps/core/factories.py`).

- [ ] **Step 1: Delete the temporary smoke test and register the app**

Delete `tests_smoke.py`. Then append the app in `config/settings/base.py` — change the `INSTALLED_APPS` local-apps section to:

```python
    # local apps
    "apps.core",
```

- [ ] **Step 2: Create the app scaffold**

```python
# apps/core/__init__.py
```

```python
# apps/core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
```

```python
# apps/core/tests/__init__.py
```

- [ ] **Step 3: Write the failing tests**

```python
# apps/core/tests/test_core_models.py
import pytest

from apps.core.factories import ArtistFactory, CityFactory, SeriesFactory, VenueFactory

pytestmark = pytest.mark.django_db


def test_city_str_and_slug_unique():
    city = CityFactory(name="Bengaluru", slug="bengaluru")
    assert str(city) == "Bengaluru"
    with pytest.raises(Exception):
        CityFactory(slug="bengaluru")


def test_venue_belongs_to_city_and_str():
    venue = VenueFactory(name="Chowdiah Memorial Hall")
    assert str(venue) == "Chowdiah Memorial Hall"
    assert venue.city_id is not None


def test_artist_alt_names_defaults_to_list():
    artist = ArtistFactory(name="T. M. Krishna", alt_names=[])
    assert artist.alt_names == []
    artist2 = ArtistFactory()
    assert isinstance(artist2.alt_names, list)


def test_series_belongs_to_city_and_str():
    series = SeriesFactory(name="Ramanavami Festival")
    assert str(series) == "Ramanavami Festival"
    assert series.city_id is not None


def test_timestamps_are_populated():
    city = CityFactory()
    assert city.created_at is not None
    assert city.updated_at is not None
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run pytest apps/core/tests/test_core_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.core.factories'` (models/factories not yet written).

- [ ] **Step 5: Implement the models**

```python
# apps/core/models.py
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class City(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "cities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Venue(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    area = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    map_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="venues")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Artist(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    alt_names = models.JSONField(default=list, blank=True)
    primary_role = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Series(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="series")

    class Meta:
        verbose_name_plural = "series"
        ordering = ["name"]

    def __str__(self):
        return self.name
```

- [ ] **Step 6: Implement the factories**

```python
# apps/core/factories.py
import factory

from apps.core.models import Artist, City, Series, Venue


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f"City {n}")
    slug = factory.Sequence(lambda n: f"city-{n}")


class VenueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venue

    name = factory.Sequence(lambda n: f"Venue {n}")
    slug = factory.Sequence(lambda n: f"venue-{n}")
    city = factory.SubFactory(CityFactory)


class ArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Artist

    name = factory.Sequence(lambda n: f"Artist {n}")
    slug = factory.Sequence(lambda n: f"artist-{n}")
    alt_names = factory.LazyFunction(list)


class SeriesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Series

    name = factory.Sequence(lambda n: f"Series {n}")
    slug = factory.Sequence(lambda n: f"series-{n}")
    city = factory.SubFactory(CityFactory)
```

- [ ] **Step 7: Make and run migrations, then run the tests**

Run:
```bash
uv run python manage.py makemigrations core
uv run pytest apps/core/tests/test_core_models.py -v
```
Expected: migration `core/migrations/0001_initial.py` created; all 5 tests PASS.

- [ ] **Step 8: Register admin (list/search for curation)**

```python
# apps/core/admin.py
from django.contrib import admin

from apps.core.models import Artist, City, Series, Venue


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "city")
    list_filter = ("city",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "area", "address")


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "primary_role")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    list_filter = ("city",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
```

- [ ] **Step 9: Verify admin imports cleanly**

Run: `uv run python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 10: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add core models (city, venue, artist, series) with admin and tests"
```

---

### Task 3: `events` app — Event and EventArtist

**Files:**
- Create: `apps/events/__init__.py`, `apps/events/apps.py`, `apps/events/models.py`, `apps/events/admin.py`, `apps/events/factories.py`
- Create: `apps/events/tests/__init__.py`, `apps/events/tests/test_event_models.py`
- Modify: `config/settings/base.py` (append `"apps.events"`)

**Interfaces:**
- Consumes: `apps.core.models.{City, Venue, Series, Artist, TimeStampedModel}`; `apps.core.factories.{CityFactory, VenueFactory, ArtistFactory, SeriesFactory}`.
- Produces (relied on by Tasks 4–5):
  - `apps.events.models.Event` with fields: `title`, `slug` (unique), `genre` (`Event.Genre` choices `KARNATIC="karnatic"`, `HINDUSTANI="hindustani"`), `start_at` (tz-aware datetime), `end_at` (nullable), `venue` FK→Venue, `city` FK→City, `is_free` bool (default True), `price` Decimal(nullable), `currency` (default `"INR"`), `source_url`, `description`, `poster` (ImageField, nullable), `status` (`Event.Status` choices, default `REVIEW`), `confidence` Float (default 0.0), `series` FK→Series (nullable), `dedup_key` (indexed), timestamps.
  - `Event.artists` M2M through `EventArtist`.
  - `Event.Status`: `REVIEW="review"`, `PUBLISHED="published"`, `REJECTED="rejected"`, `CANCELLED="cancelled"`.
  - `Event.is_upcoming` property → `start_at >= now()`.
  - `apps.events.models.EventArtist(event FK, artist FK, role: str)`.
  - Factories: `EventFactory`, `EventArtistFactory`.

- [ ] **Step 1: Register the app**

In `config/settings/base.py`, extend the local-apps section:

```python
    # local apps
    "apps.core",
    "apps.events",
```

- [ ] **Step 2: Create the app scaffold**

```python
# apps/events/__init__.py
```

```python
# apps/events/apps.py
from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
    label = "events"
```

```python
# apps/events/tests/__init__.py
```

- [ ] **Step 3: Write the failing tests**

```python
# apps/events/tests/test_event_models.py
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.factories import EventArtistFactory, EventFactory
from apps.events.models import Event

pytestmark = pytest.mark.django_db


def test_event_defaults():
    event = EventFactory()
    assert event.status == Event.Status.REVIEW
    assert event.is_free is True
    assert event.currency == "INR"
    assert event.confidence == 0.0


def test_event_genre_choices():
    event = EventFactory(genre=Event.Genre.HINDUSTANI)
    assert event.genre == "hindustani"


def test_event_is_upcoming_true_for_future():
    event = EventFactory(start_at=timezone.now() + timedelta(days=3))
    assert event.is_upcoming is True


def test_event_is_upcoming_false_for_past():
    event = EventFactory(start_at=timezone.now() - timedelta(days=3))
    assert event.is_upcoming is False


def test_event_str_includes_title():
    event = EventFactory(title="Vidwan Concert")
    assert "Vidwan Concert" in str(event)


def test_event_artist_roles():
    event = EventFactory()
    EventArtistFactory(event=event, role="vocal")
    EventArtistFactory(event=event, role="mridangam")
    roles = sorted(ea.role for ea in event.event_artists.all())
    assert roles == ["mridangam", "vocal"]
    assert event.artists.count() == 2


def test_dedup_key_is_indexed():
    field = Event._meta.get_field("dedup_key")
    assert field.db_index is True
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run pytest apps/events/tests/test_event_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.events.factories'`.

- [ ] **Step 5: Implement the models**

```python
# apps/events/models.py
from django.db import models
from django.utils import timezone

from apps.core.models import Artist, City, Series, TimeStampedModel, Venue


class Event(TimeStampedModel):
    class Genre(models.TextChoices):
        KARNATIC = "karnatic", "Karnatic"
        HINDUSTANI = "hindustani", "Hindustani"

    class Status(models.TextChoices):
        REVIEW = "review", "In review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    genre = models.CharField(max_length=20, choices=Genre.choices)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="events")
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    source_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    poster = models.ImageField(upload_to="posters/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REVIEW)
    confidence = models.FloatField(default=0.0)
    series = models.ForeignKey(
        Series, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    dedup_key = models.CharField(max_length=200, blank=True, db_index=True)
    artists = models.ManyToManyField(Artist, through="EventArtist", related_name="events")

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["genre", "start_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_at:%Y-%m-%d})"

    @property
    def is_upcoming(self):
        return self.start_at >= timezone.now()


class EventArtist(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_artists")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="event_artists")
    role = models.CharField(max_length=80)

    class Meta:
        unique_together = ("event", "artist", "role")

    def __str__(self):
        return f"{self.artist} — {self.role}"
```

Note: `ImageField` requires Pillow. Add it to dependencies:

Run: `uv add "pillow>=10.4"`

- [ ] **Step 6: Implement the factories**

```python
# apps/events/factories.py
import factory
from django.utils import timezone

from apps.core.factories import ArtistFactory, CityFactory, VenueFactory
from apps.events.models import Event, EventArtist


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    title = factory.Sequence(lambda n: f"Concert {n}")
    slug = factory.Sequence(lambda n: f"concert-{n}")
    genre = Event.Genre.KARNATIC
    start_at = factory.LazyFunction(timezone.now)
    venue = factory.SubFactory(VenueFactory)
    city = factory.SubFactory(CityFactory)


class EventArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventArtist

    event = factory.SubFactory(EventFactory)
    artist = factory.SubFactory(ArtistFactory)
    role = "vocal"
```

- [ ] **Step 7: Make migrations and run the tests**

Run:
```bash
uv run python manage.py makemigrations events
uv run pytest apps/events/tests/test_event_models.py -v
```
Expected: migration created; all 7 tests PASS.

- [ ] **Step 8: Register admin with inline artists and status workflow**

```python
# apps/events/admin.py
from django.contrib import admin

from apps.events.models import Event, EventArtist


class EventArtistInline(admin.TabularInline):
    model = EventArtist
    extra = 1
    autocomplete_fields = ("artist",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "start_at", "venue", "status", "confidence")
    list_filter = ("status", "genre", "city", "is_free")
    search_fields = ("title", "description", "venue__name")
    date_hierarchy = "start_at"
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("venue", "series", "city")
    inlines = [EventArtistInline]
    list_editable = ("status",)
    actions = ["publish_selected", "reject_selected"]

    @admin.action(description="Publish selected events")
    def publish_selected(self, request, queryset):
        queryset.update(status=Event.Status.PUBLISHED)

    @admin.action(description="Reject selected events")
    def reject_selected(self, request, queryset):
        queryset.update(status=Event.Status.REJECTED)
```

The `autocomplete_fields = ("artist",)` inline requires `ArtistAdmin.search_fields` (added in Task 2) — already present.

- [ ] **Step 9: Verify checks pass**

Run: `uv run python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 10: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add event and event-artist models with curation admin and tests"
```

---

### Task 4: `sources` app — Source registry

**Files:**
- Create: `apps/sources/__init__.py`, `apps/sources/apps.py`, `apps/sources/models.py`, `apps/sources/admin.py`, `apps/sources/factories.py`
- Create: `apps/sources/tests/__init__.py`, `apps/sources/tests/test_source_models.py`
- Modify: `config/settings/base.py` (append `"apps.sources"`)

**Interfaces:**
- Consumes: `apps.core.models.{City, TimeStampedModel}`; `apps.core.factories.CityFactory`.
- Produces (relied on by Task 5):
  - `apps.sources.models.Source` with fields: `name`, `type` (`Source.Type` choices: `FEED="feed"`, `JSONLD="jsonld"`, `API="api"`, `HTML="html"`, `JS="js"`, `EMAIL="email"`, `FORM="form"`, `SOCIAL="social"`), `url`, `handle`, `scrape_method`, `city` FK→City (nullable — email/form have no city), `health_status` (`Source.Health` choices: `OK="ok"`, `FAILING="failing"`, `DEAD="dead"`, `UNKNOWN="unknown"`, default `UNKNOWN`), `last_seen_at` (nullable), `active` bool (default True), `seasonal` bool (default False), timestamps.
  - `Source.mark_seen(at)` method: sets `last_seen_at=at`, `health_status=OK`, saves.
  - Factory: `SourceFactory`.

- [ ] **Step 1: Register the app**

In `config/settings/base.py`:

```python
    # local apps
    "apps.core",
    "apps.events",
    "apps.sources",
```

- [ ] **Step 2: Create the app scaffold**

```python
# apps/sources/__init__.py
```

```python
# apps/sources/apps.py
from django.apps import AppConfig


class SourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sources"
    label = "sources"
```

```python
# apps/sources/tests/__init__.py
```

- [ ] **Step 3: Write the failing tests**

```python
# apps/sources/tests/test_source_models.py
import pytest
from django.utils import timezone

from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_source_defaults():
    source = SourceFactory()
    assert source.active is True
    assert source.seasonal is False
    assert source.health_status == Source.Health.UNKNOWN
    assert source.last_seen_at is None


def test_source_type_choices():
    source = SourceFactory(type=Source.Type.FEED)
    assert source.type == "feed"


def test_mark_seen_sets_ok_and_timestamp():
    source = SourceFactory()
    now = timezone.now()
    source.mark_seen(now)
    source.refresh_from_db()
    assert source.health_status == Source.Health.OK
    assert source.last_seen_at == now


def test_source_str_includes_name():
    source = SourceFactory(name="Nadasurabhi")
    assert "Nadasurabhi" in str(source)
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run pytest apps/sources/tests/test_source_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.sources.factories'`.

- [ ] **Step 5: Implement the model**

```python
# apps/sources/models.py
from django.db import models

from apps.core.models import City, TimeStampedModel


class Source(TimeStampedModel):
    class Type(models.TextChoices):
        FEED = "feed", "iCal/RSS feed"
        JSONLD = "jsonld", "Embedded JSON-LD"
        API = "api", "Open API"
        HTML = "html", "Clean HTML"
        JS = "js", "JS-rendered HTML"
        EMAIL = "email", "Inbound email"
        FORM = "form", "Public form"
        SOCIAL = "social", "Social media"

    class Health(models.TextChoices):
        OK = "ok", "OK"
        FAILING = "failing", "Failing"
        DEAD = "dead", "Dead"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=Type.choices)
    url = models.URLField(blank=True)
    handle = models.CharField(max_length=200, blank=True)
    scrape_method = models.CharField(max_length=120, blank=True)
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, null=True, blank=True, related_name="sources"
    )
    health_status = models.CharField(
        max_length=20, choices=Health.choices, default=Health.UNKNOWN
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    seasonal = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.type}]"

    def mark_seen(self, at):
        self.last_seen_at = at
        self.health_status = self.Health.OK
        self.save(update_fields=["last_seen_at", "health_status", "updated_at"])
```

- [ ] **Step 6: Implement the factory**

```python
# apps/sources/factories.py
import factory

from apps.core.factories import CityFactory
from apps.sources.models import Source


class SourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Source

    name = factory.Sequence(lambda n: f"Source {n}")
    type = Source.Type.HTML
    city = factory.SubFactory(CityFactory)
```

- [ ] **Step 7: Make migrations and run the tests**

Run:
```bash
uv run python manage.py makemigrations sources
uv run pytest apps/sources/tests/test_source_models.py -v
```
Expected: migration created; all 4 tests PASS.

- [ ] **Step 8: Register admin (health dashboard)**

```python
# apps/sources/admin.py
from django.contrib import admin

from apps.sources.models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "health_status", "last_seen_at", "active", "seasonal")
    list_filter = ("type", "health_status", "active", "seasonal", "city")
    search_fields = ("name", "url", "handle")
    list_editable = ("active",)
```

- [ ] **Step 9: Verify checks pass**

Run: `uv run python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 10: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add source registry model with health-tracking admin and tests"
```

---

### Task 5: `ingest` app — RawIngest and Submission

**Files:**
- Create: `apps/ingest/__init__.py`, `apps/ingest/apps.py`, `apps/ingest/models.py`, `apps/ingest/admin.py`, `apps/ingest/factories.py`
- Create: `apps/ingest/tests/__init__.py`, `apps/ingest/tests/test_ingest_models.py`
- Modify: `config/settings/base.py` (append `"apps.ingest"`)

**Interfaces:**
- Consumes: `apps.core.models.TimeStampedModel`; `apps.sources.models.Source`; `apps.events.models.Event`; `apps.sources.factories.SourceFactory`.
- Produces (relied on by later plans):
  - `apps.ingest.models.RawIngest` with fields: `source` FK→Source, `blob_ref` (GCS path/URI string), `content_type`, `fetched_at` (tz-aware), `processed` (`RawIngest.State` choices: `PENDING="pending"`, `PROCESSED="processed"`, `FAILED="failed"`, default `PENDING`), `event` FK→Event (nullable — set when an event is produced), timestamps.
  - `apps.ingest.models.Submission` with fields: `raw_ingest` FK→RawIngest (nullable), `submitter_contact` (blank), `spam_score` Float (default 0.0), `notes` (blank), timestamps.
  - Factories: `RawIngestFactory`, `SubmissionFactory`.

- [ ] **Step 1: Register the app**

In `config/settings/base.py`:

```python
    # local apps
    "apps.core",
    "apps.events",
    "apps.sources",
    "apps.ingest",
```

- [ ] **Step 2: Create the app scaffold**

```python
# apps/ingest/__init__.py
```

```python
# apps/ingest/apps.py
from django.apps import AppConfig


class IngestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingest"
    label = "ingest"
```

```python
# apps/ingest/tests/__init__.py
```

- [ ] **Step 3: Write the failing tests**

```python
# apps/ingest/tests/test_ingest_models.py
import pytest
from django.utils import timezone

from apps.ingest.factories import RawIngestFactory, SubmissionFactory
from apps.ingest.models import RawIngest

pytestmark = pytest.mark.django_db


def test_raw_ingest_defaults():
    raw = RawIngestFactory()
    assert raw.processed == RawIngest.State.PENDING
    assert raw.event is None
    assert raw.source_id is not None


def test_raw_ingest_str_includes_source():
    raw = RawIngestFactory()
    assert str(raw.source) in str(raw)


def test_submission_links_to_raw_ingest():
    raw = RawIngestFactory()
    submission = SubmissionFactory(raw_ingest=raw)
    assert submission.raw_ingest_id == raw.id
    assert submission.spam_score == 0.0


def test_raw_ingest_fetched_at_is_timezone_aware():
    raw = RawIngestFactory(fetched_at=timezone.now())
    assert timezone.is_aware(raw.fetched_at)
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run pytest apps/ingest/tests/test_ingest_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.ingest.factories'`.

- [ ] **Step 5: Implement the models**

```python
# apps/ingest/models.py
from django.db import models

from apps.core.models import TimeStampedModel
from apps.events.models import Event
from apps.sources.models import Source


class RawIngest(TimeStampedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="raw_ingests")
    blob_ref = models.CharField(max_length=500)
    content_type = models.CharField(max_length=120, blank=True)
    fetched_at = models.DateTimeField()
    processed = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    event = models.ForeignKey(
        Event, on_delete=models.SET_NULL, null=True, blank=True, related_name="raw_ingests"
    )

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self):
        return f"RawIngest from {self.source} @ {self.fetched_at:%Y-%m-%d %H:%M}"


class Submission(TimeStampedModel):
    raw_ingest = models.ForeignKey(
        RawIngest, on_delete=models.CASCADE, null=True, blank=True, related_name="submissions"
    )
    submitter_contact = models.CharField(max_length=200, blank=True)
    spam_score = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission #{self.pk}"
```

- [ ] **Step 6: Implement the factories**

```python
# apps/ingest/factories.py
import factory
from django.utils import timezone

from apps.ingest.models import RawIngest, Submission
from apps.sources.factories import SourceFactory


class RawIngestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RawIngest

    source = factory.SubFactory(SourceFactory)
    blob_ref = factory.Sequence(lambda n: f"gs://blr-classical/raw/{n}.bin")
    fetched_at = factory.LazyFunction(timezone.now)


class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    raw_ingest = factory.SubFactory(RawIngestFactory)
```

- [ ] **Step 7: Make migrations and run the tests**

Run:
```bash
uv run python manage.py makemigrations ingest
uv run pytest apps/ingest/tests/test_ingest_models.py -v
```
Expected: migration created; all 4 tests PASS.

- [ ] **Step 8: Register admin**

```python
# apps/ingest/admin.py
from django.contrib import admin

from apps.ingest.models import RawIngest, Submission


@admin.register(RawIngest)
class RawIngestAdmin(admin.ModelAdmin):
    list_display = ("source", "content_type", "fetched_at", "processed", "event")
    list_filter = ("processed", "source")
    search_fields = ("blob_ref",)
    date_hierarchy = "fetched_at"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "submitter_contact", "spam_score", "created_at")
    search_fields = ("submitter_contact", "notes")
```

- [ ] **Step 9: Verify checks pass**

Run: `uv run python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 10: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add raw-ingest and submission models with admin and tests"
```

---

### Task 6: Seed data, full migration check, and developer runbook

**Files:**
- Create: `apps/core/management/__init__.py`, `apps/core/management/commands/__init__.py`, `apps/core/management/commands/seed_bengaluru.py`
- Create: `apps/core/tests/test_seed_command.py`
- Create: `docs/DEVELOPMENT.md`

**Interfaces:**
- Consumes: all models from Tasks 2–5.
- Produces:
  - Management command `seed_bengaluru` — idempotently creates the `Bengaluru` City (slug `bengaluru`) and a starter set of `Source` rows from the researched Tier 1–2 sabhas. Safe to run repeatedly (`get_or_create`).

- [ ] **Step 1: Write the failing test**

```python
# apps/core/tests/test_seed_command.py
import pytest
from django.core.management import call_command

from apps.core.models import City
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_seed_is_idempotent():
    call_command("seed_bengaluru")
    call_command("seed_bengaluru")
    assert City.objects.filter(slug="bengaluru").count() == 1
    assert Source.objects.count() >= 5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/core/tests/test_seed_command.py -v`
Expected: FAIL — `CommandError: Unknown command: 'seed_bengaluru'`.

- [ ] **Step 3: Implement the management command**

```python
# apps/core/management/__init__.py
```

```python
# apps/core/management/commands/__init__.py
```

```python
# apps/core/management/commands/seed_bengaluru.py
from django.core.management.base import BaseCommand

from apps.core.models import City
from apps.sources.models import Source

STARTER_SOURCES = [
    # (name, type, url)
    ("Bangalore International Centre", Source.Type.FEED,
     "https://bangaloreinternationalcentre.org/events/?ical=1"),
    ("Indian Music Experience", Source.Type.JSONLD,
     "https://www.indianmusicexperience.org/events/"),
    ("SPIC MACAY Karnataka", Source.Type.API, "https://api.spicmacay.org/graphql"),
    ("Sri Rama Lalitha Kala Mandira", Source.Type.HTML, "https://srlkmandira.org/events/"),
    ("Nadasurabhi", Source.Type.HTML, "https://nadasurabhi.org/jobs"),
    ("Sree Ramaseva Mandali (Chamarajpet)", Source.Type.HTML,
     "https://ramanavami.org/schedule"),
    ("Seshadripuram Ramaseva Samithi", Source.Type.HTML, "https://ssrss.org/schedule"),
    ("Bharatiya Vidya Bhavan Bengaluru", Source.Type.HTML,
     "https://bhavankarnataka.com/allevents"),
    ("Sangamam India", Source.Type.HTML, "https://sangamamindia.org/"),
    ("Public submission form", Source.Type.FORM, ""),
    ("Forwarded email", Source.Type.EMAIL, ""),
]


class Command(BaseCommand):
    help = "Idempotently seed the Bengaluru city and starter source registry."

    def handle(self, *args, **options):
        city, created = City.objects.get_or_create(
            slug="bengaluru", defaults={"name": "Bengaluru"}
        )
        self.stdout.write(f"City: {'created' if created else 'exists'} -> {city}")

        for name, type_, url in STARTER_SOURCES:
            city_fk = None if type_ in (Source.Type.EMAIL, Source.Type.FORM) else city
            _, made = Source.objects.get_or_create(
                name=name, defaults={"type": type_, "url": url, "city": city_fk}
            )
            self.stdout.write(f"Source: {'created' if made else 'exists'} -> {name}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest apps/core/tests/test_seed_command.py -v`
Expected: PASS.

- [ ] **Step 5: Run the entire test suite and the migration integrity check**

Run:
```bash
uv run pytest -v
uv run python manage.py makemigrations --check --dry-run
```
Expected: all tests PASS across the four apps; `makemigrations --check` reports `No changes detected` (every model change already has a migration).

- [ ] **Step 6: Run ruff and fix any lint**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: `All checks passed!` (fix and re-run if not).

- [ ] **Step 7: Write the developer runbook**

```markdown
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
```

- [ ] **Step 8: Apply migrations and seed locally to verify end-to-end**

Run:
```bash
uv run python manage.py migrate
uv run python manage.py seed_bengaluru
```
Expected: migrations apply cleanly; seed prints created/exists lines; re-running seed prints all "exists".

- [ ] **Step 9: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add Bengaluru seed command, dev runbook, and green full test suite"
```

---

## Self-Review

**1. Spec coverage (this plan is Plan 1 of 6 — scope is Foundation & Data Model only):**
- Data model — City, Venue, Artist, Series, Event, EventArtist, Source, RawIngest, Submission → Tasks 2–5. ✓
- `city` multi-city seam on Venue/Event/Source → present. ✓
- Genre + status + confidence + dedup_key on Event → Task 3. ✓
- Source registry with health + seasonal + `mark_seen` → Task 4. ✓
- Raw-artifact-first (RawIngest with blob_ref + event link) → Task 5. ✓
- Public submission storage (Submission) → Task 5. ✓
- Django admin as moderation backoffice (list/filter/search, publish/reject actions, inlines) → Tasks 2–5. ✓
- Postgres-only local loop matching prod features → Task 1 (Docker Compose). ✓
- Account separation in git authorship → every commit step. ✓
- Seed of researched Tier 1–2 sources → Task 6. ✓
- **Deferred to later plans (correctly out of scope here):** public site/templates/HTMX/SEO/JSON-LD/ICS (Plan 2), submission form + inbound email (Plan 3), scrapers/extractors/dedup logic/confidence scoring/Cloud Run Jobs (Plan 4), MCP server (Plan 5), Cloud Build/Cloud Run/GCS/CDN/domain deploy (Plan 6).

**2. Placeholder scan:** No TBD/TODO/"handle edge cases" style placeholders; every code step contains full code. ✓

**3. Type consistency:** `Event.Status.REVIEW/PUBLISHED/REJECTED/CANCELLED`, `Event.Genre.KARNATIC/HINDUSTANI`, `Source.Type.*`, `Source.Health.*`, `RawIngest.State.*` are defined once (Tasks 3–5) and referenced with the same names in tests, admin, and the seed command. `related_name`s (`events`, `venues`, `series`, `sources`, `raw_ingests`, `event_artists`) are unique per target. `mark_seen(at)` signature matches its test. ✓

---

## Follow-on plans (roadmap — written one at a time after this one)

- **Plan 2 — Public site (read paths):** base template + Tailwind/Flowbite build, home/upcoming list with HTMX filters, event detail with `schema.org/Event` JSON-LD, calendar view, ICS feeds, past archive, segmented sitemaps, OpenGraph cards.
- **Plan 3 — Submission & inbound email:** public submission form (honeypot + rate limit) → RawIngest/Submission relayed to the private mailbox; Cloudflare Email Worker + Cloud Run inbound endpoint.
- **Plan 4 — Ingestion pipeline:** per-source scraper cascade (ICS/JSON-LD/API/HTML→LLM/Playwright), Gemini poster + HTML extraction, dedup, confidence gate + auto-publish, source-health updates, Cloud Run Jobs + Scheduler.
- **Plan 5 — MCP server:** FastMCP stateless read-only tools (`search_events`, `get_event`, `list_venues`, `list_artists`), rate limiting, discovery metadata (`/.well-known/mcp.json`, `llms.txt`, registry).
- **Plan 6 — Deployment & infra:** Cloud Build CI/CD, Cloud Run + CDN, GCS + Supabase wiring, Secret Manager, backups, domain, production settings hardening.
```
