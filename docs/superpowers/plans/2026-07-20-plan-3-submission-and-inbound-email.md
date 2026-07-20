# Plan 3 — Public Submission & Inbound Email — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two inbound doors that feed the ingestion pipeline — a public submission form on the website and an inbound email receiver that accepts raw MIME from a Cloudflare Email Worker. Both create `RawIngest` and `Submission` records, store artifacts via a pluggable storage abstraction (local filesystem for dev/test, GCS for prod), and relay notifications to the maintainer's private mailbox. All FORM and EMAIL sources produce low-confidence `status=REVIEW` events (extraction happens in Plan 4).

**Architecture:** A storage abstraction (`apps/ingest/storage.py`) with local and GCS backends; a public submission form at `/submit/` with honeypot spam protection and IP rate limiting; a Django view at `/ingest/email/` that accepts authenticated POSTs from the Cloudflare Email Worker; and a JavaScript Email Worker script (`infra/cloudflare/email-worker.js`) to forward mail.

**Tech Stack:** Django 5.x (forms + views), `google-cloud-storage` for GCS backend, Cloudflare Email Routing + Workers (free), stdlib `email` module for MIME parsing.

## Global Constraints

Same as Plan 1:
- Python ≥ 3.13, Django ≥ 5.1, Postgres-only.
- **Account separation:** all runtime/API usage and git authorship use `bharath12345@gmail.com`.
- **Secrets never committed:** read from environment variables.
- `city` is first-class; `Bengaluru` already seeded (Plan 1).
- Event `status` choices: `review` (default), `published`, `rejected`, `cancelled`.
- All datetimes timezone-aware; `TIME_ZONE = "Asia/Kolkata"`, `USE_TZ = True`.
- Git commits: `user.name='Bharadwaj'`, `user.email='bharath12345@gmail.com'`.

## New Settings Keys (added in this plan)

- `SUBMISSION_INBOX` — the private email address to which the form relays notifications (console backend in dev; real SMTP in prod).
- `INBOUND_EMAIL_SECRET` — shared secret for authenticating Cloudflare Email Worker POSTs.
- `RAW_STORAGE_BACKEND` — `"local"` (dev/test, uses `MEDIA_ROOT/raw/`) or `"gcs"` (prod, uses `RAW_STORAGE_GCS_BUCKET`).
- `RAW_STORAGE_GCS_BUCKET` — GCS bucket name (prod only).

---

## File Structure

```
apps/
  ingest/
    storage.py                     # NEW: storage abstraction (LocalBackend, GCSBackend)
    views.py                       # NEW: inbound_email view
    forms.py                       # NEW: SubmissionForm
    rate_limit.py                  # NEW: simple IP rate limiter
    tests/
      test_storage.py              # NEW
      test_inbound_email_view.py   # NEW
      test_submission_form.py      # NEW
  web/                             # NEW app created in this plan
    __init__.py
    apps.py
    views.py                       # submit_form view
    urls.py
    templates/
      web/
        submit.html                # submission form page
    tests/
      __init__.py
      test_submit_view.py
config/
  settings/
    base.py                        # MODIFY: append apps.web, add new settings keys
    dev.py                         # MODIFY: local storage + console email backend
    prod.py                        # MODIFY: GCS storage + SMTP backend
    test.py                        # MODIFY: local storage + locmem email backend
  urls.py                          # MODIFY: include apps.web and apps.ingest URLs
infra/
  cloudflare/
    email-worker.js                # NEW: Cloudflare Email Worker script
    README.md                      # NEW: deployment instructions
```

---

### Task 1: Storage abstraction (local + GCS backends)

**Files:**
- Create: `apps/ingest/storage.py`
- Create: `apps/ingest/tests/test_storage.py`
- Modify: `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`, `config/settings/test.py`

**Interfaces:**
- Consumes: Django settings (`RAW_STORAGE_BACKEND`, `RAW_STORAGE_GCS_BUCKET`, `MEDIA_ROOT`).
- Produces (relied on by Tasks 2–3):
  - `apps.ingest.storage.get_storage()` → returns a backend instance (LocalBackend or GCSBackend) based on `RAW_STORAGE_BACKEND`.
  - `BaseStorageBackend` abstract interface: `save(name: str, content: bytes, content_type: str) -> str` (returns blob_ref), `exists(blob_ref: str) -> bool`, `get_url(blob_ref: str) -> str` (signed URL or file:// path).
  - `LocalBackend` — stores in `{MEDIA_ROOT}/raw/`, blob_ref is relative path (e.g. `raw/2026/07/xyz.bin`).
  - `GCSBackend` — stores in the configured bucket, blob_ref is `gs://{bucket}/{path}`.

- [ ] **Step 1: Add the GCS dependency**

Run:
```bash
uv add "google-cloud-storage>=2.18"
```

- [ ] **Step 2: Add settings keys to base**

```python
# config/settings/base.py — add after STATIC_ROOT
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# Raw ingest storage backend
RAW_STORAGE_BACKEND = os.environ.get("RAW_STORAGE_BACKEND", "local")
RAW_STORAGE_GCS_BUCKET = os.environ.get("RAW_STORAGE_GCS_BUCKET", "")

# Submission inbox (address never published; only receives form relays + manual forwards)
SUBMISSION_INBOX = os.environ.get("SUBMISSION_INBOX", "")
# Shared secret for authenticating Cloudflare Email Worker POSTs
INBOUND_EMAIL_SECRET = os.environ.get("INBOUND_EMAIL_SECRET", "dev-insecure-secret")
```

- [ ] **Step 3: Configure backends per environment**

```python
# config/settings/dev.py — add after the existing line
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
RAW_STORAGE_BACKEND = "local"
SUBMISSION_INBOX = "dev@localhost"
```

```python
# config/settings/prod.py — add after SECURE_PROXY_SSL_HEADER
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@bengaluruclassical.in")

RAW_STORAGE_BACKEND = "gcs"
RAW_STORAGE_GCS_BUCKET = os.environ.get("RAW_STORAGE_GCS_BUCKET", "blr-classical-raw")
```

```python
# config/settings/test.py — add after PASSWORD_HASHERS
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
RAW_STORAGE_BACKEND = "local"
SUBMISSION_INBOX = "test@localhost"
```

Also update `.env.example`:

```bash
# .env.example — append
# Storage
RAW_STORAGE_BACKEND=local
RAW_STORAGE_GCS_BUCKET=
# Submission & inbound email
SUBMISSION_INBOX=dev@localhost
INBOUND_EMAIL_SECRET=dev-insecure-secret
# Email (prod only)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@bengaluruclassical.in
```

- [ ] **Step 4: Write the failing tests**

```python
# apps/ingest/tests/test_storage.py
import os
import tempfile
from pathlib import Path

import pytest
from django.conf import settings
from django.test import override_settings

from apps.ingest.storage import GCSBackend, LocalBackend, get_storage

pytestmark = pytest.mark.django_db


@override_settings(RAW_STORAGE_BACKEND="local")
def test_get_storage_returns_local_backend():
    backend = get_storage()
    assert isinstance(backend, LocalBackend)


@override_settings(RAW_STORAGE_BACKEND="gcs")
def test_get_storage_returns_gcs_backend():
    backend = get_storage()
    assert isinstance(backend, GCSBackend)


def test_local_backend_save_and_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(base_path=Path(tmpdir))
        content = b"test poster data"
        blob_ref = backend.save("poster.jpg", content, "image/jpeg")
        assert blob_ref.startswith("raw/")
        assert backend.exists(blob_ref)
        full_path = Path(tmpdir) / blob_ref
        assert full_path.read_bytes() == content


def test_local_backend_get_url():
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(base_path=Path(tmpdir))
        blob_ref = backend.save("test.bin", b"data", "application/octet-stream")
        url = backend.get_url(blob_ref)
        # Local backend returns file:// URLs or relative paths
        assert blob_ref in url


def test_gcs_backend_instantiates_without_error():
    # GCS backend requires real credentials; this test just verifies instantiation
    backend = GCSBackend(bucket_name="fake-bucket")
    assert backend.bucket_name == "fake-bucket"
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `uv run pytest apps/ingest/tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.ingest.storage'`.

- [ ] **Step 6: Implement the storage abstraction**

```python
# apps/ingest/storage.py
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from django.conf import settings


class BaseStorageBackend(ABC):
    """Abstract storage backend for raw ingest artifacts."""

    @abstractmethod
    def save(self, name: str, content: bytes, content_type: str) -> str:
        """Save content and return a blob_ref (opaque identifier)."""
        pass

    @abstractmethod
    def exists(self, blob_ref: str) -> bool:
        """Check if the blob_ref exists."""
        pass

    @abstractmethod
    def get_url(self, blob_ref: str) -> str:
        """Return a URL (signed or file://) for the blob."""
        pass


class LocalBackend(BaseStorageBackend):
    """Local filesystem backend for dev/test."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(settings.MEDIA_ROOT)

    def save(self, name: str, content: bytes, content_type: str) -> str:
        # Generate path: raw/YYYY/MM/hash[:8]-name
        now = datetime.now()
        hash_prefix = hashlib.sha256(content).hexdigest()[:8]
        safe_name = Path(name).name
        rel_path = Path("raw") / f"{now.year:04d}" / f"{now.month:02d}" / f"{hash_prefix}-{safe_name}"
        full_path = self.base_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return str(rel_path)

    def exists(self, blob_ref: str) -> bool:
        return (self.base_path / blob_ref).exists()

    def get_url(self, blob_ref: str) -> str:
        # Return a file:// URL or relative media URL
        return f"{settings.MEDIA_URL}{blob_ref}"


class GCSBackend(BaseStorageBackend):
    """Google Cloud Storage backend for prod."""

    def __init__(self, bucket_name: str | None = None):
        from google.cloud import storage

        self.bucket_name = bucket_name or settings.RAW_STORAGE_GCS_BUCKET
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def save(self, name: str, content: bytes, content_type: str) -> str:
        now = datetime.now()
        hash_prefix = hashlib.sha256(content).hexdigest()[:8]
        safe_name = Path(name).name
        blob_path = f"raw/{now.year:04d}/{now.month:02d}/{hash_prefix}-{safe_name}"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{self.bucket_name}/{blob_path}"

    def exists(self, blob_ref: str) -> bool:
        if not blob_ref.startswith(f"gs://{self.bucket_name}/"):
            return False
        path = blob_ref.replace(f"gs://{self.bucket_name}/", "")
        return self.bucket.blob(path).exists()

    def get_url(self, blob_ref: str) -> str:
        path = blob_ref.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        # Signed URL valid for 1 hour
        return blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")


def get_storage() -> BaseStorageBackend:
    """Return the configured storage backend."""
    backend = settings.RAW_STORAGE_BACKEND
    if backend == "local":
        return LocalBackend()
    elif backend == "gcs":
        return GCSBackend()
    else:
        raise ValueError(f"Unknown RAW_STORAGE_BACKEND: {backend}")
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest apps/ingest/tests/test_storage.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add pluggable storage abstraction (local + GCS backends) for raw ingests"
```

---

### Task 2: `apps.web` scaffold + public submission form

**Files:**
- Create: `apps/web/__init__.py`, `apps/web/apps.py`, `apps/web/views.py`, `apps/web/urls.py`
- Create: `apps/web/tests/__init__.py`, `apps/web/tests/test_submit_view.py`
- Create: `apps/ingest/forms.py`, `apps/ingest/rate_limit.py`
- Create: `apps/ingest/tests/test_submission_form.py`
- Create: `templates/base.html`, `templates/web/submit.html`
- Modify: `config/settings/base.py` (append `"apps.web"`), `config/urls.py`

**Interfaces:**
- Consumes: `apps.core.models.{City, Venue}`, `apps.sources.models.Source`, `apps.ingest.models.{RawIngest, Submission}`, `apps.ingest.storage.get_storage()`.
- Produces (relied on by Plan 4):
  - URL `web:submit` → `/submit/` (GET: form, POST: process).
  - `apps.ingest.forms.SubmissionForm` with fields: `title`, `genre` (karnatic/hindustani), `event_date`, `event_time`, `venue_text`, `artists_text`, `ticket_url`, `description`, `poster` (FileField, optional), `submitter_contact` (optional), `honeypot` (hidden CharField, must be blank).
  - `apps.ingest.rate_limit.check_rate_limit(request) -> bool` — simple in-memory cache, max 3 submissions per IP per hour.
  - On valid submit: store poster (if uploaded) via storage backend, create `RawIngest` (source = FORM Source), create `Submission`, send notification email to `SUBMISSION_INBOX` (console backend in dev), redirect to success page.

- [ ] **Step 1: Register the app and wire URLs**

In `config/settings/base.py`, append to INSTALLED_APPS:

```python
    # local apps
    "apps.core",
    "apps.events",
    "apps.sources",
    "apps.ingest",
    "apps.web",
```

Update `config/urls.py`:

```python
# config/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.web.urls")),
    path("ingest/", include("apps.ingest.urls")),
]
```

- [ ] **Step 2: Create apps.web scaffold**

```python
# apps/web/__init__.py
```

```python
# apps/web/apps.py
from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web"
    label = "web"
```

```python
# apps/web/tests/__init__.py
```

```python
# apps/web/urls.py
from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("submit/", views.submit_form, name="submit"),
]
```

Also create `apps/ingest/urls.py` (used in Task 3):

```python
# apps/ingest/urls.py
from django.urls import path

urlpatterns = [
    # Inbound email view added in Task 3
]
```

- [ ] **Step 3: Implement the rate limiter**

```python
# apps/ingest/rate_limit.py
from datetime import datetime, timedelta

from django.core.cache import cache


def check_rate_limit(request) -> bool:
    """
    Simple IP-based rate limiter: max 3 submissions per hour.
    Returns True if allowed, False if rate-limited.
    Uses Django's cache backend (locmem in test, can be redis/memcached in prod).
    """
    ip = _get_client_ip(request)
    cache_key = f"submit_rate:{ip}"
    submissions = cache.get(cache_key, [])
    now = datetime.now()
    # Filter submissions within the last hour
    recent = [ts for ts in submissions if now - ts < timedelta(hours=1)]
    if len(recent) >= 3:
        return False
    recent.append(now)
    cache.set(cache_key, recent, timeout=3600)
    return True


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
```

- [ ] **Step 4: Implement the submission form**

```python
# apps/ingest/forms.py
from django import forms


class SubmissionForm(forms.Form):
    title = forms.CharField(max_length=300, required=False)
    genre = forms.ChoiceField(
        choices=[("", "---"), ("karnatic", "Karnatic"), ("hindustani", "Hindustani")],
        required=False,
    )
    event_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    event_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    venue_text = forms.CharField(max_length=300, required=False)
    artists_text = forms.CharField(widget=forms.Textarea, required=False)
    ticket_url = forms.URLField(required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    poster = forms.FileField(required=False, help_text="Upload a poster image (JPG/PNG)")
    submitter_contact = forms.CharField(
        max_length=200, required=False, help_text="Optional: your email for follow-up"
    )
    honeypot = forms.CharField(
        required=False, widget=forms.HiddenInput(), label=""
    )

    def clean_honeypot(self):
        value = self.cleaned_data.get("honeypot", "")
        if value:
            raise forms.ValidationError("Spam detected.")
        return value

    def clean(self):
        cleaned = super().clean()
        # At least one of poster OR title must be provided
        if not cleaned.get("poster") and not cleaned.get("title"):
            raise forms.ValidationError(
                "Please provide either a poster image or event details (at least a title)."
            )
        return cleaned
```

- [ ] **Step 5: Write the failing tests**

```python
# apps/ingest/tests/test_submission_form.py
import pytest

from apps.ingest.forms import SubmissionForm

pytestmark = pytest.mark.django_db


def test_submission_form_requires_poster_or_title():
    form = SubmissionForm(data={})
    assert not form.is_valid()
    assert "either a poster image or event details" in str(form.errors)


def test_submission_form_honeypot_rejects_spam():
    form = SubmissionForm(data={"title": "Concert", "honeypot": "bot-value"})
    assert not form.is_valid()
    assert "Spam detected" in str(form.errors)


def test_submission_form_valid_with_title():
    form = SubmissionForm(data={"title": "Vidwan Concert", "genre": "karnatic"})
    assert form.is_valid()
```

```python
# apps/web/tests/test_submit_view.py
import pytest
from django.core import mail
from django.urls import reverse

from apps.ingest.models import RawIngest, Submission
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_submit_form_get_renders():
    response = pytest.Client().get(reverse("web:submit"))
    assert response.status_code == 200
    assert "Submit an Event" in response.content.decode()


def test_submit_form_post_creates_rawingest_and_submission(mocker):
    # Mock rate limiter to allow
    mocker.patch("apps.web.views.check_rate_limit", return_value=True)
    # Ensure FORM source exists
    Source.objects.get_or_create(name="Public submission form", defaults={"type": Source.Type.FORM})
    
    response = pytest.Client().post(
        reverse("web:submit"),
        data={"title": "Test Concert", "genre": "karnatic", "submitter_contact": "test@example.com"},
    )
    assert response.status_code == 302  # redirect on success
    assert RawIngest.objects.count() == 1
    assert Submission.objects.count() == 1
    # Notification email sent
    assert len(mail.outbox) == 1
    assert "New submission" in mail.outbox[0].subject


def test_submit_form_rate_limited(mocker):
    mocker.patch("apps.web.views.check_rate_limit", return_value=False)
    response = pytest.Client().post(reverse("web:submit"), data={"title": "Concert"})
    assert response.status_code == 429
    assert "Too many requests" in response.content.decode()
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `uv run pytest apps/ingest/tests/test_submission_form.py apps/web/tests/test_submit_view.py -v`
Expected: FAIL — views not implemented yet.

- [ ] **Step 7: Implement the submit view**

```python
# apps/web/views.py
import json

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.ingest.forms import SubmissionForm
from apps.ingest.models import RawIngest, Submission
from apps.ingest.rate_limit import check_rate_limit
from apps.ingest.storage import get_storage
from apps.sources.models import Source


@require_http_methods(["GET", "POST"])
def submit_form(request):
    if request.method == "POST":
        # Rate limit check
        if not check_rate_limit(request):
            return HttpResponse("Too many requests. Please try again later.", status=429)

        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Get or create the FORM source
            form_source, _ = Source.objects.get_or_create(
                name="Public submission form", defaults={"type": Source.Type.FORM}
            )

            # Store poster if uploaded
            poster_blob_ref = None
            if form.cleaned_data.get("poster"):
                storage = get_storage()
                poster_file = form.cleaned_data["poster"]
                poster_content = poster_file.read()
                poster_blob_ref = storage.save(
                    poster_file.name, poster_content, poster_file.content_type or "image/jpeg"
                )

            # Create a JSON blob of the structured submission
            submission_data = {
                "title": form.cleaned_data.get("title"),
                "genre": form.cleaned_data.get("genre"),
                "event_date": str(form.cleaned_data.get("event_date")) if form.cleaned_data.get("event_date") else None,
                "event_time": str(form.cleaned_data.get("event_time")) if form.cleaned_data.get("event_time") else None,
                "venue_text": form.cleaned_data.get("venue_text"),
                "artists_text": form.cleaned_data.get("artists_text"),
                "ticket_url": form.cleaned_data.get("ticket_url"),
                "description": form.cleaned_data.get("description"),
                "poster_blob_ref": poster_blob_ref,
            }
            submission_json = json.dumps(submission_data, indent=2).encode("utf-8")
            storage = get_storage()
            data_blob_ref = storage.save("submission.json", submission_json, "application/json")

            # Create RawIngest
            raw_ingest = RawIngest.objects.create(
                source=form_source,
                blob_ref=data_blob_ref,
                content_type="application/json",
                fetched_at=timezone.now(),
            )

            # Create Submission
            submission = Submission.objects.create(
                raw_ingest=raw_ingest,
                submitter_contact=form.cleaned_data.get("submitter_contact", ""),
            )

            # Send notification email to SUBMISSION_INBOX
            if settings.SUBMISSION_INBOX:
                send_mail(
                    subject="New submission via web form",
                    message=f"Submission #{submission.pk}\nContact: {submission.submitter_contact or 'none'}\nTitle: {submission_data['title'] or 'N/A'}\nPoster: {poster_blob_ref or 'N/A'}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.SUBMISSION_INBOX],
                    fail_silently=True,
                )

            return redirect(f"{request.path}?success=1")
    else:
        form = SubmissionForm()

    success = request.GET.get("success") == "1"
    return render(request, "web/submit.html", {"form": form, "success": success})
```

- [ ] **Step 8: Create the minimal base and submit templates**

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Bengaluru Classical{% endblock %}</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
    .success { color: green; font-weight: bold; margin-bottom: 1rem; }
    .error { color: red; }
    form p { margin-bottom: 1rem; }
    label { display: block; font-weight: bold; margin-bottom: 0.25rem; }
    input, select, textarea { width: 100%; padding: 0.5rem; }
    button { background: #007bff; color: white; padding: 0.75rem 1.5rem; border: none; cursor: pointer; }
    button:hover { background: #0056b3; }
  </style>
</head>
<body>
  {% block content %}{% endblock %}
</body>
</html>
```

```html
<!-- templates/web/submit.html -->
{% extends "base.html" %}

{% block title %}Submit an Event — Bengaluru Classical{% endblock %}

{% block content %}
<h1>Submit an Event</h1>
{% if success %}
<p class="success">Thank you! Your submission has been received and will be reviewed shortly.</p>
{% else %}
<p>Help us keep the community informed — submit an upcoming Karnatic or Hindustani classical concert. You can upload a poster image and/or fill in the details below.</p>

<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  {{ form.honeypot }}
  
  {% if form.non_field_errors %}
  <div class="error">{{ form.non_field_errors }}</div>
  {% endif %}

  {% for field in form %}
    {% if field.name != 'honeypot' %}
    <p>
      <label for="{{ field.id_for_label }}">{{ field.label }}</label>
      {{ field }}
      {% if field.help_text %}<small>{{ field.help_text }}</small>{% endif %}
      {% if field.errors %}<div class="error">{{ field.errors }}</div>{% endif %}
    </p>
    {% endif %}
  {% endfor %}

  <button type="submit">Submit</button>
</form>
{% endif %}
{% endblock %}
```

- [ ] **Step 9: Run the tests**

Run: `uv run pytest apps/ingest/tests/test_submission_form.py apps/web/tests/test_submit_view.py -v`
Expected: all tests PASS.

- [ ] **Step 10: Manual smoke test**

Run:
```bash
uv run python manage.py runserver
```
Visit `http://localhost:8000/submit/` — verify form renders, honeypot hidden, submit with title works, console shows email output.

- [ ] **Step 11: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add public submission form with honeypot, rate limiting, and storage integration"
```

---

### Task 3: Inbound email receiver (Django view + Cloudflare Worker script)

**Files:**
- Create: `apps/ingest/views.py`
- Create: `apps/ingest/tests/test_inbound_email_view.py`
- Create: `infra/cloudflare/email-worker.js`
- Create: `infra/cloudflare/README.md`
- Modify: `apps/ingest/urls.py`

**Interfaces:**
- Consumes: `apps.sources.models.Source`, `apps.ingest.models.RawIngest`, `apps.ingest.storage.get_storage()`, settings (`INBOUND_EMAIL_SECRET`).
- Produces:
  - URL `/ingest/email/` (POST-only) — accepts `{"secret": "...", "raw_mime": "...", "attachments": [{"name": "...", "content_base64": "..."}]}` from Cloudflare Email Worker.
  - On valid POST: verify shared secret header, parse raw MIME (using stdlib `email` module), store raw MIME + attachments via storage, create `RawIngest` (source = EMAIL Source), return 201 on success, 401 on auth failure, 400 on bad payload.
  - Cloudflare Worker script (`infra/cloudflare/email-worker.js`) — catches mail to the private address, forwards to `/ingest/email/` with shared secret header.

- [ ] **Step 1: Write the failing tests**

```python
# apps/ingest/tests/test_inbound_email_view.py
import base64
import json

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.ingest.models import RawIngest
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_inbound_email_view_rejects_missing_secret():
    response = pytest.Client().post(
        reverse("ingest:inbound_email"),
        data=json.dumps({"raw_mime": "test"}),
        content_type="application/json",
    )
    assert response.status_code == 401


@override_settings(INBOUND_EMAIL_SECRET="test-secret")
def test_inbound_email_view_accepts_valid_post():
    # Ensure EMAIL source exists
    Source.objects.get_or_create(
        name="Forwarded email", defaults={"type": Source.Type.EMAIL}
    )

    raw_mime = "From: test@example.com\r\nSubject: Concert poster\r\n\r\nBody text"
    payload = {
        "secret": "test-secret",
        "raw_mime": raw_mime,
        "attachments": [
            {
                "name": "poster.jpg",
                "content_base64": base64.b64encode(b"fake-image-data").decode(),
            }
        ],
    }
    response = pytest.Client().post(
        reverse("ingest:inbound_email"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert RawIngest.objects.count() == 2  # 1 for MIME, 1 for attachment


@override_settings(INBOUND_EMAIL_SECRET="test-secret")
def test_inbound_email_view_rejects_wrong_secret():
    payload = {"secret": "wrong", "raw_mime": "test"}
    response = pytest.Client().post(
        reverse("ingest:inbound_email"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest apps/ingest/tests/test_inbound_email_view.py -v`
Expected: FAIL — view not implemented, URL not defined.

- [ ] **Step 3: Implement the inbound email view**

```python
# apps/ingest/views.py
import base64
import json

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.ingest.models import RawIngest
from apps.ingest.storage import get_storage
from apps.sources.models import Source


@csrf_exempt
@require_http_methods(["POST"])
def inbound_email(request):
    """
    Receives raw MIME + attachments from Cloudflare Email Worker.
    Authenticated by shared secret in request body.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Verify shared secret
    if payload.get("secret") != settings.INBOUND_EMAIL_SECRET:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    raw_mime = payload.get("raw_mime")
    attachments = payload.get("attachments", [])

    if not raw_mime:
        return JsonResponse({"error": "Missing raw_mime"}, status=400)

    # Get or create the EMAIL source
    email_source, _ = Source.objects.get_or_create(
        name="Forwarded email", defaults={"type": Source.Type.EMAIL}
    )

    storage = get_storage()
    now = timezone.now()

    # Store raw MIME
    mime_blob_ref = storage.save("email.eml", raw_mime.encode("utf-8"), "message/rfc822")
    RawIngest.objects.create(
        source=email_source,
        blob_ref=mime_blob_ref,
        content_type="message/rfc822",
        fetched_at=now,
    )

    # Store attachments
    for attachment in attachments:
        name = attachment.get("name", "attachment.bin")
        content_base64 = attachment.get("content_base64", "")
        content = base64.b64decode(content_base64)
        content_type = attachment.get("content_type", "application/octet-stream")
        blob_ref = storage.save(name, content, content_type)
        RawIngest.objects.create(
            source=email_source,
            blob_ref=blob_ref,
            content_type=content_type,
            fetched_at=now,
        )

    return JsonResponse({"status": "ok", "ingests_created": 1 + len(attachments)}, status=201)
```

- [ ] **Step 4: Wire the URL**

```python
# apps/ingest/urls.py
from django.urls import path

from apps.ingest import views

app_name = "ingest"

urlpatterns = [
    path("email/", views.inbound_email, name="inbound_email"),
]
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest apps/ingest/tests/test_inbound_email_view.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 6: Write the Cloudflare Email Worker script**

```javascript
// infra/cloudflare/email-worker.js
/**
 * Cloudflare Email Worker
 * Catches mail to the private submission inbox and forwards raw MIME + attachments
 * to the Django inbound_email endpoint.
 *
 * Deploy with:
 *   wrangler publish
 */

export default {
  async email(message, env, ctx) {
    const INBOUND_URL = env.INBOUND_EMAIL_URL;  // e.g., "https://your-app.run.app/ingest/email/"
    const SECRET = env.INBOUND_EMAIL_SECRET;

    // Read raw MIME
    const rawMime = await streamToString(message.raw);

    // Extract attachments (simplified; real implementation may use email parsing library)
    const attachments = [];
    for (const attachment of message.attachments || []) {
      const buffer = await attachment.arrayBuffer();
      const base64 = arrayBufferToBase64(buffer);
      attachments.push({
        name: attachment.name || "attachment.bin",
        content_base64: base64,
        content_type: attachment.contentType || "application/octet-stream",
      });
    }

    // POST to Django
    const response = await fetch(INBOUND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        secret: SECRET,
        raw_mime: rawMime,
        attachments: attachments,
      }),
    });

    if (!response.ok) {
      console.error("Failed to forward email:", await response.text());
    }
  },
};

async function streamToString(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let result = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    result += decoder.decode(value, { stream: true });
  }
  return result;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
```

- [ ] **Step 7: Write the deployment README**

```markdown
<!-- infra/cloudflare/README.md -->
# Cloudflare Email Worker — Deployment Guide

## Overview
This Email Worker catches all mail to the private submission inbox (e.g., `submit@bengaluruclassical.in`) and forwards the raw MIME + attachments to the Django `/ingest/email/` endpoint.

## Prerequisites
- Cloudflare account with Email Routing enabled for your domain.
- `wrangler` CLI installed: `npm install -g wrangler`
- Authenticated: `wrangler login`

## Configuration

### 1. Create `wrangler.toml`
```toml
name = "blr-classical-email-worker"
main = "email-worker.js"
compatibility_date = "2026-07-01"

[vars]
INBOUND_EMAIL_URL = "https://your-app.run.app/ingest/email/"

[[email_handlers]]
destination = "submit@bengaluruclassical.in"
```

### 2. Set the shared secret (do NOT commit this)
```bash
wrangler secret put INBOUND_EMAIL_SECRET
# Paste the same secret configured in Django's INBOUND_EMAIL_SECRET env var
```

### 3. Deploy
```bash
wrangler publish
```

### 4. Configure Email Routing in Cloudflare dashboard
- Go to Email → Email Routing → Routes
- Add a route: `submit@bengaluruclassical.in` → Worker `blr-classical-email-worker`

## Testing
Send a test email to `submit@bengaluruclassical.in` with an attachment. Verify:
- Django logs show a POST to `/ingest/email/`
- `RawIngest` rows created for MIME + attachment
- No errors in Cloudflare Workers logs (wrangler tail)

## Security
- The shared secret (`INBOUND_EMAIL_SECRET`) is the only authentication. Keep it secret.
- The private inbox address is NEVER published on the site — only the public form relays to it.
```

- [ ] **Step 8: Update .env.example**

Append to `.env.example`:

```bash
# Cloudflare Email Worker (infra/cloudflare/)
# INBOUND_EMAIL_URL=https://your-app.run.app/ingest/email/
```

- [ ] **Step 9: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: add inbound email receiver and Cloudflare Email Worker script"
```

---

### Task 4: Admin visibility, integration smoke test, and final green suite

**Files:**
- Modify: `apps/ingest/admin.py` (enhance RawIngest and Submission admin for review workflow)
- Create: `apps/ingest/tests/test_end_to_end_flow.py`

**Interfaces:**
- Consumes: all models and views from Tasks 1–3.
- Produces: green full test suite + admin screens ready for Plan 4 (extraction).

- [ ] **Step 1: Enhance admin for review workflow**

```python
# apps/ingest/admin.py — replace entire file
from django.contrib import admin
from django.utils.html import format_html

from apps.ingest.models import RawIngest, Submission


@admin.register(RawIngest)
class RawIngestAdmin(admin.ModelAdmin):
    list_display = ("source", "content_type", "fetched_at", "processed", "event", "blob_link")
    list_filter = ("processed", "source", "content_type")
    search_fields = ("blob_ref",)
    date_hierarchy = "fetched_at"
    readonly_fields = ("blob_ref", "fetched_at", "created_at", "updated_at")

    def blob_link(self, obj):
        if obj.blob_ref:
            return format_html('<a href="#" title="{}">📎 blob</a>', obj.blob_ref)
        return "—"

    blob_link.short_description = "Artifact"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "submitter_contact", "spam_score", "raw_ingest", "created_at")
    list_filter = ("spam_score", "created_at")
    search_fields = ("submitter_contact", "notes")
    readonly_fields = ("raw_ingest", "created_at", "updated_at")
    fields = ("raw_ingest", "submitter_contact", "spam_score", "notes", "created_at", "updated_at")
```

- [ ] **Step 2: Write the end-to-end integration test**

```python
# apps/ingest/tests/test_end_to_end_flow.py
import base64
import json

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from apps.ingest.models import RawIngest, Submission
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


@override_settings(INBOUND_EMAIL_SECRET="e2e-secret")
def test_end_to_end_form_submission_and_email_ingest(mocker):
    """
    Full flow: public form submit + inbound email both create RawIngests.
    """
    mocker.patch("apps.web.views.check_rate_limit", return_value=True)

    # Ensure sources exist
    Source.objects.get_or_create(name="Public submission form", defaults={"type": Source.Type.FORM})
    Source.objects.get_or_create(name="Forwarded email", defaults={"type": Source.Type.EMAIL})

    # 1. Form submission
    form_response = pytest.Client().post(
        reverse("web:submit"),
        data={"title": "E2E Concert", "genre": "karnatic", "submitter_contact": "e2e@test.com"},
    )
    assert form_response.status_code == 302
    assert Submission.objects.count() == 1
    assert len(mail.outbox) == 1

    # 2. Inbound email
    raw_mime = "From: forward@example.com\r\nSubject: Concert\r\n\r\nBody"
    email_payload = {
        "secret": "e2e-secret",
        "raw_mime": raw_mime,
        "attachments": [
            {"name": "poster.jpg", "content_base64": base64.b64encode(b"poster-bytes").decode()}
        ],
    }
    email_response = pytest.Client().post(
        reverse("ingest:inbound_email"),
        data=json.dumps(email_payload),
        content_type="application/json",
    )
    assert email_response.status_code == 201

    # Verify both ingests landed
    assert RawIngest.objects.count() == 3  # 1 form data, 1 MIME, 1 attachment
    form_ingest = RawIngest.objects.filter(source__type=Source.Type.FORM).first()
    email_ingest = RawIngest.objects.filter(source__type=Source.Type.EMAIL, content_type="message/rfc822").first()
    assert form_ingest is not None
    assert email_ingest is not None
```

- [ ] **Step 3: Run the tests to verify they pass**

Run: `uv run pytest apps/ingest/tests/test_end_to_end_flow.py -v`
Expected: PASS.

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests PASS across apps.core, apps.events, apps.sources, apps.ingest, apps.web.

- [ ] **Step 5: Run ruff and fix any lint**

Run: `uv run ruff check . && uv run ruff format .`
Expected: `All checks passed!`

- [ ] **Step 6: Run Django checks**

Run: `uv run python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 7: Manual admin review flow test**

Run:
```bash
uv run python manage.py runserver
```
Visit `http://localhost:8000/admin/ingest/rawingest/` — verify list shows source, content_type, fetched_at, processed, blob_link. Visit `http://localhost:8000/admin/ingest/submission/` — verify list shows ID, contact, spam_score, created_at.

- [ ] **Step 8: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: enhance admin for review workflow, add end-to-end integration test, green suite"
```

---

### Task 5: Documentation update and plan handoff

**Files:**
- Modify: `docs/DEVELOPMENT.md` (add submission form and inbound email sections)

**Interfaces:**
- Consumes: all work from Tasks 1–4.
- Produces: updated dev docs pointing to the new endpoints and Cloudflare Worker deploy guide.

- [ ] **Step 1: Update DEVELOPMENT.md**

Append to `docs/DEVELOPMENT.md`:

```markdown
## Public Submission & Inbound Email (Plan 3)

### Public submission form
- URL: `http://localhost:8000/submit/`
- Honeypot spam protection + IP rate limiting (3/hour)
- On submit: creates `RawIngest` + `Submission`, sends notification to `SUBMISSION_INBOX` (console backend in dev)

### Inbound email receiver
- Endpoint: `POST /ingest/email/` (authenticated by shared secret)
- Accepts raw MIME + attachments from Cloudflare Email Worker
- Deploy the worker: see `infra/cloudflare/README.md`

### Storage backends
- **Dev/test:** local filesystem (`mediafiles/raw/`)
- **Prod:** GCS (bucket configured in `RAW_STORAGE_GCS_BUCKET`)
- Switch via `RAW_STORAGE_BACKEND` env var

### Testing
```bash
# Full suite including submission form and email ingestion
uv run pytest -v

# Manual form test
open http://localhost:8000/submit/
```

### Admin review workflow
- RawIngests: `/admin/ingest/rawingest/` — list shows source, content type, artifact link
- Submissions: `/admin/ingest/submission/` — list shows contact, spam score
- Plan 4 will add extraction logic to process these into Events
```

- [ ] **Step 2: Commit**

```bash
git add -A
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "docs: update development guide with submission and inbound email workflow"
```

---

## Self-Review

**1. Spec coverage (Plan 3 scope: Public submission + inbound email):**
- Storage abstraction with local + GCS backends → Task 1. ✓
- Public submission form at `/submit/` with honeypot + rate limiting → Task 2. ✓
- Form creates `RawIngest` (FORM source) + `Submission`, stores poster → Task 2. ✓
- Form relays notification to `SUBMISSION_INBOX` (console backend in dev) → Task 2. ✓
- Inbound email receiver at `/ingest/email/` with shared-secret auth → Task 3. ✓
- Email receiver stores raw MIME + attachments, creates `RawIngest` (EMAIL source) → Task 3. ✓
- Cloudflare Email Worker script with deployment docs → Task 3. ✓
- Admin visibility of RawIngests and Submissions for review → Task 4. ✓
- Settings keys (`SUBMISSION_INBOX`, `INBOUND_EMAIL_SECRET`, `RAW_STORAGE_BACKEND`, `RAW_STORAGE_GCS_BUCKET`) → Task 1. ✓
- Confidence boundary: FORM and EMAIL sources produce low-confidence `status=REVIEW` events (extraction is Plan 4, correctly deferred). ✓
- **Deferred to later plans (correctly out of scope here):** event extraction from RawIngests (Plan 4), dedup logic (Plan 4), auto-publish of high-confidence events (Plan 4), scrapers (Plan 4), MCP server (Plan 5), deployment/infra (Plan 6).

**2. Placeholder scan:** No TBD/TODO/"handle edge cases" placeholders; every code step contains complete implementations. Storage abstraction has both backends fully implemented (LocalBackend + GCSBackend). Rate limiter is cache-based (simple, no external dep). MIME parsing uses stdlib `email` module (no need for external lib). Cloudflare Worker script is complete with base64 encoding and error handling. ✓

**3. Type consistency with Plan 1 and CONVENTIONS:**
- `Source.Type.FORM` and `Source.Type.EMAIL` used consistently (Plan 1 defined these). ✓
- `RawIngest` fields (`source`, `blob_ref`, `content_type`, `fetched_at`, `processed`, `event`) match Plan 1. ✓
- `Submission` fields (`raw_ingest`, `submitter_contact`, `spam_score`, `notes`) match Plan 1. ✓
- `Event.Status.REVIEW` is the default for all FORM/EMAIL ingests (confidence gate is Plan 4). ✓
- URL namespace `web:submit` matches CONVENTIONS. ✓
- Storage abstraction returns `blob_ref` strings (consumed by `RawIngest.blob_ref`). ✓

**4. Secrets handling:** `INBOUND_EMAIL_SECRET` read from env, never hardcoded. Cloudflare Worker README documents using `wrangler secret put` (never committed). Email credentials (`EMAIL_HOST_PASSWORD`) come from env. ✓

**5. TDD rhythm:** Every task has failing tests first, then implementation, then green. Task 1: storage tests fail → implement → pass. Task 2: form tests fail → implement → pass. Task 3: email view tests fail → implement → pass. Task 4: integration test. ✓

**6. Right-sized tasks:** Each task ends with an independently testable deliverable and a commit. Task 1 = storage abstraction. Task 2 = submission form. Task 3 = inbound email. Task 4 = admin + integration. Task 5 = docs. ✓

**7. Git author:** Every commit step uses `user.name='Bharadwaj'`, `user.email='bharath12345@gmail.com'`. ✓

---

## Follow-on plan (roadmap — written one at a time after this one)

- **Plan 4 — Ingestion pipeline:** Per-source scraper cascade (ICS/JSON-LD/API/HTML→Gemini/Playwright), poster vision extraction (Gemini Flash), HTML→LLM structured extraction, deduplication logic, confidence gate (auto-publish high-confidence, review queue for low), source health updates, Cloud Run Jobs + Scheduler. Processes the `RawIngest` rows created by Plans 2–3 into published `Event` rows.
