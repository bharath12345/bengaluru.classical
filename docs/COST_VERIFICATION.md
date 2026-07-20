# Cost Verification Checklist

Target: **< ₹500/month** (see `docs/technical.md` §8).

| Item | Expected |
|---|---|
| Cloud Run (scale-to-zero) + Scheduler + GCS | ~₹0–low single digits |
| Supabase Postgres free (Mumbai) | ₹0 |
| Cloudflare Email Routing + CDN | ₹0 |
| Gemini free tier / low volume | ₹0–few ₹ |
| Domain `.in` | ~₹70/mo amortized |
| Warm Cloud Run instance | **OFF** (would be ~₹900/mo) |

## Verify monthly

1. GCP Billing → project `bengaluru-classical` → last 30 days.
2. Confirm min instances = 0 on Cloud Run.
3. Confirm no paid Instagram scrapers enabled.
4. Gemini usage within free quota.
