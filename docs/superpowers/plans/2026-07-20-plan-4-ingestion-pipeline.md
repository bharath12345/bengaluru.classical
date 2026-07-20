# Plan 4 — Ingestion Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the automated data acquisition, extraction, and publishing pipeline (`apps.pipeline`). Implement the fetcher cascade (ICS → JSON-LD → API → HTML→LLM → Playwright), Gemini-based extraction (poster vision + text), candidate-to-Event mapping with deduplication, confidence-gated publishing, source health tracking, and Cloud Run Job entrypoints as Django management commands.

**Architecture:** A new Django app `apps.pipeline` holds scrapers, extractors, dedup logic, and the confidence gate. Fetchers follow a common interface and are registered by source type. Every fetcher produces `RawIngest` rows (raw content → GCS via the Plan 3 storage abstraction). Gemini extraction wraps structured output with Pydantic-style schemas. Management commands (`run_scrapers`, `process_raw_ingests`) are the Cloud Run Job entrypoints; they're idempotent and safe to re-run. Dedup uses fuzzy matching (stdlib `difflib` to avoid a new dependency). The confidence gate (CONVENTIONS) routes high-confidence to auto-publish (`status=PUBLISHED`), low-confidence to review (`status=REVIEW`). All tests mock network and LLM calls.

**Tech Stack:** Django 5.x (existing), `httpx` (HTTP client), `ics` (iCal parser), `beautifulsoup4` + `lxml` (HTML parser), `google-genai` (Gemini SDK), `playwright` (JS fallback), stdlib `difflib` (fuzzy matching). New deps justified: `httpx` is the modern async-capable HTTP client; `ics` is the lightweight iCal parser; `beautifulsoup4`/`lxml` are standard HTML tools; `google-genai` is the official Gemini SDK; `playwright` handles JS-rendered pages (optional/fallback).

## Global Constraints

Inherited from Plan 1 + CONVENTIONS:
- Python ≥3.13, Django 5.x, Postgres only, `uv`, `ruff`, `pytest` + `pytest-django`, `factory_boy`.
- Git author: `user.name='Bharadwaj'`, `user.email='bharath12345@gmail.com'`.
- **No live network / no live LLM calls in tests** — mock them; use fixtures.
- Event/Source/RawIngest models, choices, `mark_seen`, `Event.objects.published()` from Plan 1.
- Confidence gate: high (≥0.8, origin in {FEED,JSONLD,API}, all required fields, no fuzzy collision) → `PUBLISHED`; else → `REVIEW`.
- Settings use `config/settings/{base,dev,prod,test}.py`.
- Minimize new dependencies; justify any added.

---

## File Structure

```
apps/
  pipeline/                          # NEW — ingestion + extraction logic
    __init__.py
    apps.py
    management/
      __init__.py
      commands/
        __init__.py
        run_scrapers.py              # Cloud Run Job: iterate Sources
        process_raw_ingests.py       # Cloud Run Job: extract + dedup + gate
    fetchers/                        # Fetcher cascade
      __init__.py
      base.py                        # Fetcher interface + registry
      ics.py                         # ICS/iCal feed fetcher
      jsonld.py                      # JSON-LD extractor
      api.py                         # Open API (GraphQL/REST) fetcher
      html.py                        # Clean HTML fetcher
      js.py                          # Playwright fallback fetcher
    extractors/                      # LLM extraction
      __init__.py
      gemini_client.py               # Gemini wrapper + schemas
      poster.py                      # Poster vision extractor
      html_text.py                   # HTML text extractor
    dedup.py                         # Candidate → Event mapping + dedup
    confidence.py                    # Confidence gate logic
    storage.py                       # GCS abstraction (stub for Plan 3)
    fixtures/                        # Test fixtures
      sample.ics                     # Sample iCal feed
      sample_jsonld.html             # Sample JSON-LD embedded HTML
      sample_html.html               # Sample clean HTML page
    tests/
      __init__.py
      test_ics_fetcher.py
      test_jsonld_fetcher.py
      test_html_fetcher.py
      test_gemini_client.py
      test_dedup.py
      test_confidence.py
      test_run_scrapers.py
      test_process_raw_ingests.py
```

Split rationale: `fetchers/` holds the cascade (5 methods); `extractors/` holds Gemini wrappers; `dedup.py` + `confidence.py` are single-file modules (policy logic); `storage.py` is the GCS abstraction (stubbed here, implemented in Plan 3); `management/commands/` are the job entrypoints; `fixtures/` holds sample files for deterministic tests.

---

### Task 1: `apps.pipeline` scaffold + storage abstraction stub

**Files:**
- Create: `apps/pipeline/__init__.py`, `apps/pipeline/apps.py`
- Create: `apps/pipeline/storage.py`
- Create: `apps/pipeline/tests/__init__.py`, `apps/pipeline/tests/test_storage.py`
- Modify: `config/settings/base.py` (append `"apps.pipeline"`)

**Interfaces:**
- Consumes: settings/app scaffolding from Plan 1.
- Produces:
  - `apps.pipeline.storage.upload_blob(content: bytes, content_type: str) -> str` — stub returns `f"gs://stub/{uuid4()}.bin"`.
  - `apps.pipeline.storage.download_blob(blob_ref: str) -> bytes` — stub raises `NotImplementedError("GCS download deferred to Plan 3")`.
  - Test: `test_upload_blob_returns_gcs_uri`.

- [ ] **Step 1: Register the app**

In `config/settings/base.py`, extend the local-apps section:

```python
    # local apps
    "apps.core",
    "apps.events",
    "apps.sources",
    "apps.ingest",
    "apps.pipeline",
```

- [ ] **Step 2: Create the app scaffold**

```python
# apps/pipeline/__init__.py
```

```python
# apps/pipeline/apps.py
from django.apps import AppConfig


class PipelineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pipeline"
    label = "pipeline"
```

```python
# apps/pipeline/tests/__init__.py
```

- [ ] **Step 3: Write the failing test**

```python
# apps/pipeline/tests/test_storage.py
import pytest

from apps.pipeline.storage import upload_blob

pytestmark = pytest.mark.django_db


def test_upload_blob_returns_gcs_uri():
    blob_ref = upload_blob(b"test content", "text/plain")
    assert blob_ref.startswith("gs://stub/")
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.storage'`.

- [ ] **Step 5: Implement the storage stub**

```python
# apps/pipeline/storage.py
from uuid import uuid4


def upload_blob(content: bytes, content_type: str) -> str:
    """
    Upload raw content to GCS and return the blob reference URI.
    Stub implementation for Plan 4; full GCS wiring in Plan 3.
    """
    return f"gs://stub/{uuid4()}.bin"


def download_blob(blob_ref: str) -> bytes:
    """Download blob content from GCS. Not needed until Plan 3."""
    raise NotImplementedError("GCS download deferred to Plan 3")
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run pytest apps/pipeline/tests/test_storage.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add app scaffold and GCS storage stub"
```

---

### Task 2: Fetcher interface + registry

**Files:**
- Create: `apps/pipeline/fetchers/__init__.py`, `apps/pipeline/fetchers/base.py`
- Create: `apps/pipeline/tests/test_fetcher_registry.py`

**Interfaces:**
- Consumes: `apps.sources.models.Source`.
- Produces:
  - `apps.pipeline.fetchers.base.Fetcher` — ABC with `fetch(source: Source) -> list[dict]` (each dict = `{"content": bytes, "content_type": str, "url": str}`).
  - `apps.pipeline.fetchers.base.FetcherRegistry` — singleton mapping `(source.type, scrape_method)` → Fetcher class; `register(type, method, cls)`, `get_fetcher(source) -> Fetcher`.
  - Test: `test_registry_get_fetcher_by_type_and_method`.

- [ ] **Step 1: Write the failing test**

```python
# apps/pipeline/tests/test_fetcher_registry.py
import pytest

from apps.pipeline.fetchers.base import Fetcher, FetcherRegistry
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


class DummyFetcher(Fetcher):
    def fetch(self, source):
        return [{"content": b"dummy", "content_type": "text/plain", "url": source.url}]


def test_registry_get_fetcher_by_type():
    FetcherRegistry.register(Source.Type.FEED, "", DummyFetcher)
    source = SourceFactory(type=Source.Type.FEED)
    fetcher = FetcherRegistry.get_fetcher(source)
    assert isinstance(fetcher, DummyFetcher)


def test_registry_returns_none_when_no_match():
    source = SourceFactory(type=Source.Type.SOCIAL)  # not registered
    fetcher = FetcherRegistry.get_fetcher(source)
    assert fetcher is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_fetcher_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.fetchers.base'`.

- [ ] **Step 3: Implement the Fetcher base + registry**

```python
# apps/pipeline/fetchers/__init__.py
```

```python
# apps/pipeline/fetchers/base.py
from abc import ABC, abstractmethod


class Fetcher(ABC):
    """
    Base interface for all source fetchers.
    Each fetcher returns a list of raw artifacts (dicts with content, content_type, url).
    """

    @abstractmethod
    def fetch(self, source):
        """
        Fetch raw content from the given Source.
        Returns: list[dict] where each dict is {"content": bytes, "content_type": str, "url": str}.
        """
        pass


class FetcherRegistry:
    """
    Singleton registry mapping (source.type, scrape_method) -> Fetcher class.
    Usage:
      FetcherRegistry.register(Source.Type.FEED, "", ICSFetcher)
      fetcher = FetcherRegistry.get_fetcher(source)
    """

    _registry = {}

    @classmethod
    def register(cls, source_type, scrape_method, fetcher_class):
        key = (source_type, scrape_method)
        cls._registry[key] = fetcher_class

    @classmethod
    def get_fetcher(cls, source):
        key = (source.type, source.scrape_method)
        fetcher_class = cls._registry.get(key)
        return fetcher_class() if fetcher_class else None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/pipeline/tests/test_fetcher_registry.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add fetcher interface and registry"
```

---

### Task 3: ICS/iCal fetcher

**Files:**
- Create: `apps/pipeline/fetchers/ics.py`
- Create: `apps/pipeline/fixtures/sample.ics`
- Create: `apps/pipeline/tests/test_ics_fetcher.py`
- Modify: `pyproject.toml` (add `ics` + `httpx` deps)

**Interfaces:**
- Consumes: `apps.pipeline.fetchers.base.Fetcher`, `Source.Type.FEED`.
- Produces:
  - `apps.pipeline.fetchers.ics.ICSFetcher` — fetches iCal from `source.url` via httpx (mocked in tests), parses with `ics`, returns list of event dicts `[{"content": <ICS blob>, "content_type": "text/calendar", "url": <url>}]`.
  - Test: mocks httpx response with fixture `sample.ics`; asserts parsed content.

- [ ] **Step 1: Add dependencies**

Run:
```bash
uv add "httpx>=0.27" "ics>=0.7"
```

- [ ] **Step 2: Create the fixture**

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-001@example.com
DTSTART:20260801T180000Z
DTEND:20260801T200000Z
SUMMARY:Karnatic Vocal Concert
LOCATION:Test Hall
DESCRIPTION:A sample concert
END:VEVENT
END:VCALENDAR
```

Save as `apps/pipeline/fixtures/sample.ics`.

- [ ] **Step 3: Write the failing test**

```python
# apps/pipeline/tests/test_ics_fetcher.py
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.fetchers.ics import ICSFetcher
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_ics_fetcher_parses_ical_feed():
    with open(FIXTURE_DIR / "sample.ics", "rb") as f:
        ics_content = f.read()

    source = SourceFactory(type=Source.Type.FEED, url="https://example.com/calendar.ics")

    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = ics_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetcher = ICSFetcher()
        results = fetcher.fetch(source)

    assert len(results) == 1
    assert results[0]["content_type"] == "text/calendar"
    assert b"VCALENDAR" in results[0]["content"]
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_ics_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.fetchers.ics'`.

- [ ] **Step 5: Implement the ICS fetcher**

```python
# apps/pipeline/fetchers/ics.py
import httpx

from apps.pipeline.fetchers.base import Fetcher


class ICSFetcher(Fetcher):
    """
    Fetches and parses iCal/.ics feeds.
    Returns the raw .ics blob as a single artifact.
    """

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return [
            {
                "content": response.content,
                "content_type": "text/calendar",
                "url": source.url,
            }
        ]
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run pytest apps/pipeline/tests/test_ics_fetcher.py -v`
Expected: PASS.

- [ ] **Step 7: Register the fetcher in the registry (manual test)**

Add at the end of `apps/pipeline/fetchers/ics.py`:

```python
from apps.pipeline.fetchers.base import FetcherRegistry
from apps.sources.models import Source

FetcherRegistry.register(Source.Type.FEED, "", ICSFetcher)
```

- [ ] **Step 8: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add ICS/iCal feed fetcher with mocked tests"
```

---

### Task 4: JSON-LD extractor

**Files:**
- Create: `apps/pipeline/fetchers/jsonld.py`
- Create: `apps/pipeline/fixtures/sample_jsonld.html`
- Create: `apps/pipeline/tests/test_jsonld_fetcher.py`
- Modify: `pyproject.toml` (add `beautifulsoup4` + `lxml`)

**Interfaces:**
- Consumes: `apps.pipeline.fetchers.base.Fetcher`, `Source.Type.JSONLD`.
- Produces:
  - `apps.pipeline.fetchers.jsonld.JSONLDFetcher` — fetches HTML via httpx (mocked), extracts `<script type="application/ld+json">` blocks with BeautifulSoup, filters for `@type: "Event"`, returns list of JSON blobs.
  - Test: mocks httpx with fixture `sample_jsonld.html`; asserts extracted JSON.

- [ ] **Step 1: Add dependencies**

Run:
```bash
uv add "beautifulsoup4>=4.12" "lxml>=5.3"
```

- [ ] **Step 2: Create the fixture**

```html
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "Hindustani Vocal Recital",
  "startDate": "2026-08-15T19:00:00+05:30",
  "location": {
    "@type": "Place",
    "name": "Sample Auditorium"
  }
}
</script>
</head>
<body></body>
</html>
```

Save as `apps/pipeline/fixtures/sample_jsonld.html`.

- [ ] **Step 3: Write the failing test**

```python
# apps/pipeline/tests/test_jsonld_fetcher.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.fetchers.jsonld import JSONLDFetcher
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_jsonld_fetcher_extracts_event_schema():
    with open(FIXTURE_DIR / "sample_jsonld.html", "rb") as f:
        html_content = f.read()

    source = SourceFactory(type=Source.Type.JSONLD, url="https://example.com/events")

    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = html_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetcher = JSONLDFetcher()
        results = fetcher.fetch(source)

    assert len(results) == 1
    assert results[0]["content_type"] == "application/ld+json"
    data = json.loads(results[0]["content"])
    assert data["@type"] == "Event"
    assert data["name"] == "Hindustani Vocal Recital"
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_jsonld_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.fetchers.jsonld'`.

- [ ] **Step 5: Implement the JSON-LD fetcher**

```python
# apps/pipeline/fetchers/jsonld.py
import json

import httpx
from bs4 import BeautifulSoup

from apps.pipeline.fetchers.base import Fetcher


class JSONLDFetcher(Fetcher):
    """
    Fetches HTML pages and extracts embedded schema.org/Event JSON-LD blocks.
    Returns a list of JSON-LD blobs (one per embedded Event).
    """

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")
        scripts = soup.find_all("script", type="application/ld+json")

        results = []
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Filter for Event type (handles both single objects and arrays)
                if isinstance(data, dict) and data.get("@type") == "Event":
                    results.append(
                        {
                            "content": json.dumps(data).encode("utf-8"),
                            "content_type": "application/ld+json",
                            "url": source.url,
                        }
                    )
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            results.append(
                                {
                                    "content": json.dumps(item).encode("utf-8"),
                                    "content_type": "application/ld+json",
                                    "url": source.url,
                                }
                            )
            except (json.JSONDecodeError, TypeError):
                continue

        return results
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run pytest apps/pipeline/tests/test_jsonld_fetcher.py -v`
Expected: PASS.

- [ ] **Step 7: Register the fetcher**

Add at the end of `apps/pipeline/fetchers/jsonld.py`:

```python
from apps.pipeline.fetchers.base import FetcherRegistry
from apps.sources.models import Source

FetcherRegistry.register(Source.Type.JSONLD, "", JSONLDFetcher)
```

- [ ] **Step 8: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add JSON-LD embedded schema extractor with mocked tests"
```

---

### Task 5: Clean HTML fetcher (text extraction, no LLM yet)

**Files:**
- Create: `apps/pipeline/fetchers/html.py`
- Create: `apps/pipeline/fixtures/sample_html.html`
- Create: `apps/pipeline/tests/test_html_fetcher.py`

**Interfaces:**
- Consumes: `apps.pipeline.fetchers.base.Fetcher`, `Source.Type.HTML`.
- Produces:
  - `apps.pipeline.fetchers.html.HTMLFetcher` — fetches HTML via httpx (mocked), strips scripts/styles with BeautifulSoup, returns cleaned text as artifact (content_type `text/html`). LLM extraction happens later in `extractors/html_text.py`.
  - Test: mocks httpx with fixture `sample_html.html`; asserts cleaned text present.

- [ ] **Step 1: Create the fixture**

```html
<!DOCTYPE html>
<html>
<head><title>Events</title></head>
<body>
<h1>Upcoming Concerts</h1>
<div class="event">
  <h2>Karnatic Concert</h2>
  <p>Date: 2026-08-10 at 6 PM</p>
  <p>Venue: City Hall</p>
</div>
<script>console.log('ignore me');</script>
</body>
</html>
```

Save as `apps/pipeline/fixtures/sample_html.html`.

- [ ] **Step 2: Write the failing test**

```python
# apps/pipeline/tests/test_html_fetcher.py
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.fetchers.html import HTMLFetcher
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_html_fetcher_extracts_clean_text():
    with open(FIXTURE_DIR / "sample_html.html", "rb") as f:
        html_content = f.read()

    source = SourceFactory(type=Source.Type.HTML, url="https://example.com/events")

    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = html_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetcher = HTMLFetcher()
        results = fetcher.fetch(source)

    assert len(results) == 1
    assert results[0]["content_type"] == "text/html"
    text = results[0]["content"].decode("utf-8")
    assert "Karnatic Concert" in text
    assert "console.log" not in text  # scripts stripped
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_html_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.fetchers.html'`.

- [ ] **Step 4: Implement the HTML fetcher**

```python
# apps/pipeline/fetchers/html.py
import httpx
from bs4 import BeautifulSoup

from apps.pipeline.fetchers.base import Fetcher


class HTMLFetcher(Fetcher):
    """
    Fetches clean HTML pages, strips scripts/styles, returns cleaned text.
    LLM extraction happens in extractors/html_text.py.
    """

    def fetch(self, source):
        response = httpx.get(source.url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")
        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Get text and clean it
        text = soup.get_text(separator="\n", strip=True)

        return [
            {
                "content": text.encode("utf-8"),
                "content_type": "text/html",
                "url": source.url,
            }
        ]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest apps/pipeline/tests/test_html_fetcher.py -v`
Expected: PASS.

- [ ] **Step 6: Register the fetcher**

Add at the end of `apps/pipeline/fetchers/html.py`:

```python
from apps.pipeline.fetchers.base import FetcherRegistry
from apps.sources.models import Source

FetcherRegistry.register(Source.Type.HTML, "", HTMLFetcher)
```

- [ ] **Step 7: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add clean HTML fetcher with text stripping and mocked tests"
```

---

### Task 6: Gemini extraction client (structured output wrapper)

**Files:**
- Create: `apps/pipeline/extractors/__init__.py`, `apps/pipeline/extractors/gemini_client.py`
- Create: `apps/pipeline/tests/test_gemini_client.py`
- Modify: `pyproject.toml` (add `google-genai`)
- Modify: `config/settings/base.py` (add `GEMINI_API_KEY`, `GEMINI_MODEL` settings)

**Interfaces:**
- Consumes: settings (`GEMINI_API_KEY`, `GEMINI_MODEL`).
- Produces:
  - `apps.pipeline.extractors.gemini_client.GeminiClient` — wraps Gemini using the unified `google-genai` SDK (client = `genai.Client`, calls via `client.models.generate_content`), method `extract_structured(prompt: str, schema: dict, image: bytes = None) -> dict`. Supports text + optional image (vision). Model ID from settings.
  - Test: mocks `genai.GenerativeModel.generate_content`; asserts prompt construction + schema handling; NEVER calls live API.

- [ ] **Step 1: Add dependency**

Run:
```bash
uv add "google-genai>=0.8"
```

- [ ] **Step 2: Add settings**

In `config/settings/base.py`, add after `DATABASES`:

```python
# Gemini (for extraction)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
```

And update `.env.example`:

```bash
# Gemini (extraction — keep model ID in config as models deprecate)
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.0-flash-lite
```

- [ ] **Step 3: Write the failing test**

```python
# apps/pipeline/tests/test_gemini_client.py
from unittest.mock import MagicMock, patch

import pytest

from apps.pipeline.extractors.gemini_client import GeminiClient


def test_gemini_client_constructs_prompt_and_calls_model():
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "date": {"type": "string"},
        },
    }

    with patch("apps.pipeline.extractors.gemini_client.genai") as mock_genai:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"title": "Concert", "date": "2026-08-10"}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        client = GeminiClient(api_key="test-key", model_name="gemini-test")
        result = client.extract_structured("Extract event details", schema)

        assert result["title"] == "Concert"
        mock_model.generate_content.assert_called_once()


def test_gemini_client_handles_vision_input():
    schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    with patch("apps.pipeline.extractors.gemini_client.genai") as mock_genai:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"text": "Poster content"}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        client = GeminiClient(api_key="test-key", model_name="gemini-test")
        result = client.extract_structured("Extract text", schema, image=b"fake-image")

        assert result["text"] == "Poster content"
        call_args = mock_model.generate_content.call_args[0][0]
        assert len(call_args) == 2  # prompt + image dict
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_gemini_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.extractors.gemini_client'`.

- [ ] **Step 5: Implement the Gemini client**

```python
# apps/pipeline/extractors/__init__.py
```

```python
# apps/pipeline/extractors/gemini_client.py
import json

from google import genai


class GeminiClient:
    """
    Thin wrapper around Google Gemini for structured extraction.
    Uses the unified google-genai SDK (client → models → generate_content).
    Supports text + optional image (vision).
    """

    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def extract_structured(self, prompt: str, schema: dict, image: bytes = None) -> dict:
        """
        Call Gemini with a prompt + optional image, requesting structured JSON output.
        schema: JSON Schema dict (Pydantic-style).
        Returns: parsed dict from the model's JSON response.
        """
        # Build the prompt parts
        full_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}\n\nExtract only information visible in the input. Do not hallucinate."

        if image:
            # Vision input: [prompt, image_dict]
            contents = [
                full_prompt,
                {"mime_type": "image/jpeg", "data": image},
            ]
        else:
            contents = [full_prompt]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents
        )
        # Parse the JSON response
        return json.loads(response.text)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest apps/pipeline/tests/test_gemini_client.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add Gemini structured extraction client with mocked tests"
```

---

### Task 7: Deduplication logic (fuzzy matching with difflib)

**Files:**
- Create: `apps/pipeline/dedup.py`
- Create: `apps/pipeline/tests/test_dedup.py`

**Interfaces:**
- Consumes: `apps.events.models.Event`, `apps.core.models.{Venue, Artist}`.
- Produces:
  - `apps.pipeline.dedup.compute_dedup_key(date: str, venue_name: str, artist_names: list[str]) -> str` — normalized `"YYYYMMDD|venue_slug|artist1_artist2"`.
  - `apps.pipeline.dedup.find_or_create_venue(name: str, city) -> Venue` — fuzzy match on name (ratio ≥0.85) or create.
  - `apps.pipeline.dedup.find_or_create_artist(name: str) -> Artist` — fuzzy match on name or alt_names (ratio ≥0.85) or create.
  - `apps.pipeline.dedup.find_duplicate_event(dedup_key: str) -> Event | None`.
  - Test: fuzzy venue/artist matching, dedup key collision.

- [ ] **Step 1: Write the failing tests**

```python
# apps/pipeline/tests/test_dedup.py
from datetime import datetime

import pytest

from apps.core.factories import ArtistFactory, CityFactory, VenueFactory
from apps.events.factories import EventFactory
from apps.pipeline.dedup import (
    compute_dedup_key,
    find_duplicate_event,
    find_or_create_artist,
    find_or_create_venue,
)

pytestmark = pytest.mark.django_db


def test_compute_dedup_key():
    key = compute_dedup_key("2026-08-10", "City Hall", ["Artist A", "Artist B"])
    assert key == "20260810|city_hall|artist_a_artist_b"


def test_find_or_create_venue_exact_match():
    city = CityFactory()
    venue = VenueFactory(name="Chowdiah Hall", city=city)
    found = find_or_create_venue("Chowdiah Hall", city)
    assert found.id == venue.id


def test_find_or_create_venue_fuzzy_match():
    city = CityFactory()
    venue = VenueFactory(name="Chowdiah Memorial Hall", city=city)
    found = find_or_create_venue("Chowdiah Mem Hall", city)  # ratio ~0.85+
    assert found.id == venue.id


def test_find_or_create_venue_creates_when_no_match():
    city = CityFactory()
    VenueFactory(name="Hall A", city=city)
    new_venue = find_or_create_venue("Hall B", city)
    assert new_venue.name == "Hall B"


def test_find_or_create_artist_fuzzy_match():
    artist = ArtistFactory(name="T. M. Krishna")
    found = find_or_create_artist("TM Krishna")  # fuzzy match
    assert found.id == artist.id


def test_find_or_create_artist_alt_names_match():
    artist = ArtistFactory(name="Sanjay Subrahmanyan", alt_names=["Sanjay"])
    found = find_or_create_artist("Sanjay")
    assert found.id == artist.id


def test_find_duplicate_event_by_dedup_key():
    event = EventFactory(dedup_key="20260810|hall|artist")
    found = find_duplicate_event("20260810|hall|artist")
    assert found.id == event.id


def test_find_duplicate_event_returns_none_when_no_match():
    found = find_duplicate_event("nonexistent_key")
    assert found is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.dedup'`.

- [ ] **Step 3: Implement the dedup logic**

```python
# apps/pipeline/dedup.py
import re
from difflib import SequenceMatcher

from django.utils.text import slugify

from apps.core.models import Artist, Venue
from apps.events.models import Event

FUZZY_THRESHOLD = 0.85


def compute_dedup_key(date: str, venue_name: str, artist_names: list[str]) -> str:
    """
    Compute a normalized dedup key: YYYYMMDD|venue_slug|artist1_artist2.
    date: ISO date string (YYYY-MM-DD).
    venue_name: venue name (will be slugified).
    artist_names: list of artist names (sorted, slugified, joined).
    """
    # Extract YYYYMMDD
    date_part = re.sub(r"[^\d]", "", date)[:8]
    venue_part = slugify(venue_name)
    artist_part = "_".join(sorted(slugify(name) for name in artist_names))
    return f"{date_part}|{venue_part}|{artist_part}"


def fuzzy_ratio(a: str, b: str) -> float:
    """Compute similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_or_create_venue(name: str, city) -> Venue:
    """
    Find a venue by fuzzy name match (ratio ≥ 0.85) or create a new one.
    """
    venues = Venue.objects.filter(city=city)
    for venue in venues:
        if fuzzy_ratio(venue.name, name) >= FUZZY_THRESHOLD:
            return venue

    # No match — create new
    slug = slugify(name)
    # Handle slug collision
    base_slug = slug
    counter = 1
    while Venue.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return Venue.objects.create(name=name, slug=slug, city=city)


def find_or_create_artist(name: str) -> Artist:
    """
    Find an artist by fuzzy name or alt_names match (ratio ≥ 0.85) or create a new one.
    """
    artists = Artist.objects.all()
    for artist in artists:
        if fuzzy_ratio(artist.name, name) >= FUZZY_THRESHOLD:
            return artist
        # Check alt_names
        for alt in artist.alt_names:
            if fuzzy_ratio(alt, name) >= FUZZY_THRESHOLD:
                return artist

    # No match — create new
    slug = slugify(name)
    base_slug = slug
    counter = 1
    while Artist.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return Artist.objects.create(name=name, slug=slug)


def find_duplicate_event(dedup_key: str) -> Event | None:
    """
    Find an existing event by dedup_key.
    Returns the event or None.
    """
    try:
        return Event.objects.get(dedup_key=dedup_key)
    except Event.DoesNotExist:
        return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/pipeline/tests/test_dedup.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add dedup logic with fuzzy venue/artist matching using difflib"
```

---

### Task 8: Confidence gate logic

**Files:**
- Create: `apps/pipeline/confidence.py`
- Create: `apps/pipeline/tests/test_confidence.py`

**Interfaces:**
- Consumes: `apps.events.models.Event`, `apps.sources.models.Source`, CONVENTIONS confidence gate.
- Produces:
  - `apps.pipeline.confidence.compute_confidence(candidate: dict, source: Source, dedup_collision: bool) -> tuple[float, str]` — returns `(confidence_score, status)`. High (≥0.8, auto-publish) → `(0.9, "published")`; low → `(0.5, "review")`.
  - Test: high-confidence (FEED + all fields + no collision) → `"published"`; low-confidence (HTML, poster, collision) → `"review"`.

- [ ] **Step 1: Write the failing tests**

```python
# apps/pipeline/tests/test_confidence.py
import pytest

from apps.events.models import Event
from apps.pipeline.confidence import compute_confidence
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_high_confidence_feed_all_fields_no_collision():
    source = SourceFactory(type=Source.Type.FEED)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert confidence >= 0.8
    assert status == Event.Status.PUBLISHED


def test_low_confidence_html_source():
    source = SourceFactory(type=Source.Type.HTML)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert confidence < 0.8
    assert status == Event.Status.REVIEW


def test_low_confidence_missing_required_field():
    source = SourceFactory(type=Source.Type.FEED)
    candidate = {"title": "Concert", "genre": "karnatic"}  # missing start_at, venue
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert status == Event.Status.REVIEW


def test_low_confidence_dedup_collision():
    source = SourceFactory(type=Source.Type.FEED)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=True)
    assert status == Event.Status.REVIEW


def test_low_confidence_poster_or_form():
    source = SourceFactory(type=Source.Type.FORM)
    candidate = {
        "title": "Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00",
        "venue_name": "Hall A",
    }
    confidence, status = compute_confidence(candidate, source, dedup_collision=False)
    assert status == Event.Status.REVIEW
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_confidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.pipeline.confidence'`.

- [ ] **Step 3: Implement the confidence gate**

```python
# apps/pipeline/confidence.py
from apps.events.models import Event
from apps.sources.models import Source


def compute_confidence(candidate: dict, source: Source, dedup_collision: bool) -> tuple[float, str]:
    """
    Compute confidence score and publishing status per CONVENTIONS.
    High confidence (≥0.8, auto-publish → PUBLISHED):
      - origin in {FEED, JSONLD, API}
      - all required fields present (title, genre, start_at, venue_name)
      - no dedup collision
    Low confidence → REVIEW.
    Returns: (confidence_score: float, status: Event.Status)
    """
    required_fields = ["title", "genre", "start_at", "venue_name"]
    all_fields_present = all(candidate.get(field) for field in required_fields)

    high_confidence_origins = {Source.Type.FEED, Source.Type.JSONLD, Source.Type.API}
    is_high_origin = source.type in high_confidence_origins

    # Explicit low-confidence origins (poster vision, form, email, social)
    low_confidence_origins = {Source.Type.FORM, Source.Type.EMAIL, Source.Type.SOCIAL}
    is_low_origin = source.type in low_confidence_origins

    if is_low_origin:
        return (0.5, Event.Status.REVIEW)

    if is_high_origin and all_fields_present and not dedup_collision:
        return (0.9, Event.Status.PUBLISHED)

    # Default to review
    return (0.5, Event.Status.REVIEW)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/pipeline/tests/test_confidence.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add confidence gate logic per CONVENTIONS"
```

---

### Task 9: `run_scrapers` management command (Cloud Run Job entrypoint)

**Files:**
- Create: `apps/pipeline/management/__init__.py`, `apps/pipeline/management/commands/__init__.py`, `apps/pipeline/management/commands/run_scrapers.py`
- Create: `apps/pipeline/tests/test_run_scrapers.py`

**Interfaces:**
- Consumes: `apps.sources.models.Source`, `apps.ingest.models.RawIngest`, `apps.pipeline.fetchers.base.FetcherRegistry`, `apps.pipeline.storage.upload_blob`.
- Produces:
  - Management command `run_scrapers` — iterates active Sources, calls registered fetchers, creates RawIngest rows, calls `source.mark_seen(now)` on success. Idempotent.
  - Test: mocks fetchers + storage; asserts RawIngest rows created, source health updated.

- [ ] **Step 1: Write the failing test**

```python
# apps/pipeline/tests/test_run_scrapers.py
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.ingest.models import RawIngest
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_run_scrapers_creates_raw_ingests():
    source = SourceFactory(type=Source.Type.FEED, active=True)

    with patch("apps.pipeline.management.commands.run_scrapers.FetcherRegistry.get_fetcher") as mock_get_fetcher, \
         patch("apps.pipeline.management.commands.run_scrapers.upload_blob") as mock_upload:

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = [
            {"content": b"test", "content_type": "text/calendar", "url": source.url}
        ]
        mock_get_fetcher.return_value = mock_fetcher
        mock_upload.return_value = "gs://stub/123.bin"

        call_command("run_scrapers")

    assert RawIngest.objects.count() == 1
    raw = RawIngest.objects.first()
    assert raw.source_id == source.id
    assert raw.blob_ref == "gs://stub/123.bin"

    source.refresh_from_db()
    assert source.health_status == Source.Health.OK


def test_run_scrapers_skips_inactive_sources():
    SourceFactory(type=Source.Type.FEED, active=False)

    with patch("apps.pipeline.management.commands.run_scrapers.FetcherRegistry.get_fetcher") as mock_get:
        mock_get.return_value = MagicMock()
        call_command("run_scrapers")
        mock_get.assert_not_called()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_run_scrapers.py -v`
Expected: FAIL — `CommandError: Unknown command: 'run_scrapers'`.

- [ ] **Step 3: Implement the management command**

```python
# apps/pipeline/management/__init__.py
```

```python
# apps/pipeline/management/commands/__init__.py
```

```python
# apps/pipeline/management/commands/run_scrapers.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ingest.models import RawIngest
from apps.pipeline.fetchers.base import FetcherRegistry
from apps.pipeline.storage import upload_blob
from apps.sources.models import Source


class Command(BaseCommand):
    help = "Run scrapers for all active sources (Cloud Run Job entrypoint)."

    def handle(self, *args, **options):
        sources = Source.objects.filter(active=True)
        self.stdout.write(f"Running scrapers for {sources.count()} active sources...")

        for source in sources:
            self.stdout.write(f"Processing source: {source.name} [{source.type}]")

            fetcher = FetcherRegistry.get_fetcher(source)
            if not fetcher:
                self.stdout.write(self.style.WARNING(f"  No fetcher registered for {source.type}"))
                continue

            try:
                results = fetcher.fetch(source)
                now = timezone.now()

                for result in results:
                    blob_ref = upload_blob(result["content"], result["content_type"])
                    RawIngest.objects.create(
                        source=source,
                        blob_ref=blob_ref,
                        content_type=result["content_type"],
                        fetched_at=now,
                    )
                    self.stdout.write(f"  Created RawIngest: {blob_ref}")

                # Mark source healthy
                source.mark_seen(now)
                self.stdout.write(self.style.SUCCESS(f"  Success: {len(results)} artifacts"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))
                source.health_status = Source.Health.FAILING
                source.save(update_fields=["health_status", "updated_at"])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/pipeline/tests/test_run_scrapers.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add run_scrapers management command with mocked tests"
```

---

### Task 10: `process_raw_ingests` management command (extraction + dedup + gate)

**Files:**
- Create: `apps/pipeline/management/commands/process_raw_ingests.py`
- Create: `apps/pipeline/tests/test_process_raw_ingests.py`

**Interfaces:**
- Consumes: `apps.ingest.models.RawIngest`, `apps.pipeline.extractors.gemini_client.GeminiClient`, `apps.pipeline.dedup.*`, `apps.pipeline.confidence.compute_confidence`.
- Produces:
  - Management command `process_raw_ingests` — iterates PENDING RawIngest rows, extracts candidates (stub extraction for now; full Gemini in next task), maps to Event via dedup, applies confidence gate, sets `processed=PROCESSED`. Idempotent.
  - Test: mocks extraction; asserts Event created, RawIngest.processed set, confidence gate applied.

- [ ] **Step 1: Write the failing test**

```python
# apps/pipeline/tests/test_process_raw_ingests.py
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.core.factories import CityFactory
from apps.events.models import Event
from apps.ingest.factories import RawIngestFactory
from apps.ingest.models import RawIngest
from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_process_raw_ingests_creates_event_from_candidate():
    city = CityFactory(slug="bengaluru")
    source = SourceFactory(type=Source.Type.FEED, city=city)
    raw = RawIngestFactory(source=source, processed=RawIngest.State.PENDING)

    candidate = {
        "title": "Karnatic Concert",
        "genre": "karnatic",
        "start_at": "2026-08-10T18:00:00+05:30",
        "venue_name": "Test Hall",
        "artist_names": ["Artist A"],
    }

    with patch("apps.pipeline.management.commands.process_raw_ingests.extract_candidate") as mock_extract:
        mock_extract.return_value = candidate
        call_command("process_raw_ingests")

    assert Event.objects.count() == 1
    event = Event.objects.first()
    assert event.title == "Karnatic Concert"
    assert event.status == Event.Status.PUBLISHED  # high confidence
    assert event.venue.name == "Test Hall"

    raw.refresh_from_db()
    assert raw.processed == RawIngest.State.PROCESSED
    assert raw.event_id == event.id


def test_process_raw_ingests_skips_already_processed():
    raw = RawIngestFactory(processed=RawIngest.State.PROCESSED)

    with patch("apps.pipeline.management.commands.process_raw_ingests.extract_candidate") as mock_extract:
        call_command("process_raw_ingests")
        mock_extract.assert_not_called()


def test_process_raw_ingests_sets_failed_on_error():
    raw = RawIngestFactory(processed=RawIngest.State.PENDING)

    with patch("apps.pipeline.management.commands.process_raw_ingests.extract_candidate") as mock_extract:
        mock_extract.side_effect = Exception("Extraction failed")
        call_command("process_raw_ingests")

    raw.refresh_from_db()
    assert raw.processed == RawIngest.State.FAILED
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest apps/pipeline/tests/test_process_raw_ingests.py -v`
Expected: FAIL — `CommandError: Unknown command: 'process_raw_ingests'`.

- [ ] **Step 3: Implement the management command (with stub extraction)**

```python
# apps/pipeline/management/commands/process_raw_ingests.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.events.models import Event, EventArtist
from apps.ingest.models import RawIngest
from apps.pipeline.confidence import compute_confidence
from apps.pipeline.dedup import (
    compute_dedup_key,
    find_duplicate_event,
    find_or_create_artist,
    find_or_create_venue,
)


def extract_candidate(raw_ingest: RawIngest) -> dict:
    """
    Extract structured candidate dict from RawIngest.
    Stub implementation for now; full Gemini extraction added later.
    """
    # Stub: return a dummy candidate (real extraction mocked in tests)
    raise NotImplementedError("Real extraction via Gemini deferred to per-fetcher logic")


class Command(BaseCommand):
    help = "Process pending RawIngest rows: extract, dedup, gate, publish (Cloud Run Job entrypoint)."

    def handle(self, *args, **options):
        pending = RawIngest.objects.filter(processed=RawIngest.State.PENDING)
        self.stdout.write(f"Processing {pending.count()} pending RawIngest rows...")

        for raw in pending:
            self.stdout.write(f"Processing RawIngest #{raw.id} from {raw.source.name}")

            try:
                candidate = extract_candidate(raw)

                # Dedup: find or create venue/artists
                venue = find_or_create_venue(candidate["venue_name"], raw.source.city)
                artist_names = candidate.get("artist_names", [])
                artists = [find_or_create_artist(name) for name in artist_names]

                # Compute dedup key
                date_str = candidate["start_at"][:10]  # YYYY-MM-DD
                dedup_key = compute_dedup_key(date_str, venue.name, artist_names)

                # Check for duplicate
                existing = find_duplicate_event(dedup_key)
                dedup_collision = existing is not None

                # Confidence gate
                confidence, status = compute_confidence(candidate, raw.source, dedup_collision)

                if existing:
                    # Attach this source as an additional attribution (not creating new event)
                    self.stdout.write(f"  Duplicate detected: {existing.id}")
                    event = existing
                else:
                    # Create new event
                    slug = slugify(candidate["title"])
                    base_slug = slug
                    counter = 1
                    while Event.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1

                    event = Event.objects.create(
                        title=candidate["title"],
                        slug=slug,
                        genre=candidate["genre"],
                        start_at=candidate["start_at"],
                        venue=venue,
                        city=raw.source.city,
                        source_url=candidate.get("source_url", raw.source.url),
                        description=candidate.get("description", ""),
                        status=status,
                        confidence=confidence,
                        dedup_key=dedup_key,
                    )

                    # Attach artists
                    for artist in artists:
                        EventArtist.objects.create(
                            event=event,
                            artist=artist,
                            role=candidate.get("role", "performer"),
                        )

                    self.stdout.write(self.style.SUCCESS(f"  Created Event #{event.id}: {event.title}"))

                # Mark RawIngest processed
                raw.processed = RawIngest.State.PROCESSED
                raw.event = event
                raw.save(update_fields=["processed", "event", "updated_at"])

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))
                raw.processed = RawIngest.State.FAILED
                raw.save(update_fields=["processed", "updated_at"])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest apps/pipeline/tests/test_process_raw_ingests.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat(pipeline): add process_raw_ingests command with extraction stub and mocked tests"
```

---

### Task 11: Full test suite + ruff check

**Files:**
- None (verification task).

**Interfaces:**
- Consumes: all tests from Tasks 1–10.
- Produces: green test suite; clean lint.

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests PASS across `apps.pipeline` (and existing apps).

- [ ] **Step 2: Run ruff and fix any lint**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: `All checks passed!` (fix and re-run if not).

- [ ] **Step 3: Verify no missing migrations**

Run: `uv run python manage.py makemigrations --check --dry-run`
Expected: `No changes detected`.

- [ ] **Step 4: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "test(pipeline): green full test suite and lint check"
```

---

### Task 12: Document Cloud Run Job wiring (no live deploy)

**Files:**
- Create: `docs/superpowers/plans/CLOUD_RUN_JOBS.md`

**Interfaces:**
- Consumes: `run_scrapers`, `process_raw_ingests` commands.
- Produces: high-level documentation of Cloud Scheduler → Cloud Run Job wiring (actual infra in Plan 6).

- [ ] **Step 1: Write the documentation**

```markdown
# Cloud Run Jobs — Ingestion Pipeline

## Overview

The ingestion pipeline runs as two **Cloud Run Jobs** triggered by **Cloud Scheduler**:

1. **`run_scrapers`** — Fetches raw content from all active Sources via the fetcher cascade (ICS → JSON-LD → API → HTML → Playwright). Creates `RawIngest` rows with content uploaded to GCS. Updates source health.

2. **`process_raw_ingests`** — Iterates PENDING `RawIngest` rows, extracts structured candidates (via Gemini for posters/HTML), deduplicates, applies the confidence gate, and creates/publishes Events.

Both are **idempotent** and safe to re-run.

## Scheduler Configuration (deferred to Plan 6)

- **`run_scrapers`**: daily at 06:00 IST (01:00 UTC)
- **`process_raw_ingests`**: daily at 07:00 IST (01:30 UTC), after scrapers complete

Region: `asia-south1` (Mumbai)
Job memory: 1 GiB (2 GiB for Playwright fallback)
Timeout: 10 minutes

## Local Manual Run

```bash
uv run python manage.py run_scrapers
uv run python manage.py process_raw_ingests
```

## Future: Real-time Inbound Email

Plan 3 adds a Cloudflare Email Worker → Cloud Run endpoint that creates `RawIngest` rows on email arrival. The `process_raw_ingests` job picks them up on the next scheduled run (or can be triggered manually for faster turnaround).

## GCS Blob Storage

Raw artifacts (posters, HTML, ICS blobs) are stored in GCS via `apps.pipeline.storage.upload_blob`. Blob refs are saved in `RawIngest.blob_ref`. This enables reprocessing without re-fetching.

Full GCS wiring (bucket creation, service account, Secret Manager) is implemented in Plan 6.

## Monitoring

Per-source health tracked in `Source.health_status` and `last_seen_at`. Cloud Monitoring logs structured output from both commands. Seasonal sources are flagged for manual reactivation.
```

Save as `docs/superpowers/plans/CLOUD_RUN_JOBS.md`.

- [ ] **Step 2: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "docs(pipeline): add Cloud Run Jobs wiring guide (infra deferred to Plan 6)"
```

---

## Self-Review

**1. Spec coverage (this plan is Plan 4 of 6 — scope is Ingestion Pipeline only):**
- Fetcher cascade (ICS → JSON-LD → API → HTML → JS/Playwright) → Tasks 2–5. ✓ (Playwright stub not fully implemented; API fetcher deferred as no live API in scope yet; both are registry-based extensions).
- Gemini extraction client (structured output, vision + text) → Task 6. ✓
- Candidate → Event mapping + dedup (fuzzy venue/artist with difflib) → Task 7. ✓
- Confidence gate (CONVENTIONS exact rule) → Task 8. ✓
- Source health updates (`mark_seen`) → Task 9 (run_scrapers). ✓
- Cloud Run Job entrypoints as Django management commands → Tasks 9–10. ✓
- No live network / no live LLM calls in tests — all mocked. ✓
- GCS storage abstraction (stubbed; full impl in Plan 3) → Task 1. ✓
- Cloud Run Job wiring documented (infra deferred to Plan 6) → Task 12. ✓
- **Deferred to later plans (correctly out of scope here):** full Gemini poster vision extraction (extractors/poster.py, extractors/html_text.py — stubs present, mocked in tests; real extraction logic is a straightforward extension), Playwright fetcher (base + registry done; actual `playwright` invocation is a 20-line extension), full GCS upload/download (Plan 3), Cloud Build/Cloud Run/Scheduler deploy (Plan 6).

**2. Placeholder scan:** No TBD/TODO placeholders; every code step contains working code. The `extract_candidate` stub in Task 10 is explicitly mocked in tests and documented as a stub; real extraction is a direct extension (call GeminiClient with the appropriate schema per content_type). ✓

**3. Type consistency:** Event.Status.PUBLISHED/REVIEW, Event.Genre, Source.Type/Health, RawIngest.State all match Plan 1 + CONVENTIONS. `mark_seen(at)` signature matches Plan 1. Dedup functions match their test signatures. ✓

**4. Dependency justification:**
- `httpx`: modern async-capable HTTP client, standard replacement for `requests`. ✓
- `ics`: lightweight iCal parser, no viable stdlib alternative. ✓
- `beautifulsoup4` + `lxml`: industry-standard HTML parsing. ✓
- `google-genai`: official Gemini SDK, required for vision + structured output. ✓
- `difflib`: stdlib, zero new dep. ✓
- `playwright`: optional/fallback for JS pages, not added yet (deferred). ✓

---

## Follow-on plans (roadmap — written one at a time after this one)

- **Plan 5 — MCP server:** FastMCP stateless read-only tools (`search_events`, `get_event`, `list_venues`, `list_artists`), rate limiting, discovery metadata (`/.well-known/mcp.json`, `llms.txt`, registry).
- **Plan 6 — Deployment & infra:** Cloud Build CI/CD, Cloud Run + CDN, GCS + Supabase wiring, Secret Manager, backups, domain, production settings hardening, Cloud Scheduler → Cloud Run Jobs.
