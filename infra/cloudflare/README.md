# Cloudflare Email Worker — Deployment Guide

## Overview

This Email Worker catches all mail to the private submission inbox (e.g.,
`submit@bengaluruclassical.in`) and forwards the raw MIME + attachments to the
Django `/ingest/email/` endpoint.

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

## Security

- The shared secret (`INBOUND_EMAIL_SECRET`) is the only authentication. Keep it secret.
- The private inbox address is NEVER published on the site — only the public form relays to it.
