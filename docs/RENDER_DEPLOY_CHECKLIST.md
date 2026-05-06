# Render + Supabase Deployment Checklist

Everything you need to do after adding new Phase 4 features to see them live on Render + Supabase.

---

## Step 1 — Run pending database migrations against Supabase

Six migrations have been added since the last deploy. Run once from local (with Supabase `DATABASE_URL`) or via the Render shell on your API service.

**From local machine:**
```bash
cd FleetOpsX-API
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres" \
  venv/bin/alembic upgrade head
```

**From Render shell (API service → Shell tab):**
```bash
alembic upgrade head
```

### Migrations applied

| Revision | What it creates | Phase |
|----------|----------------|-------|
| `c3d4e5f6a7b8` | `driver_availability`, `vehicle_status` | PP-E3 |
| `d4e5f6a7b8c9` | `chat_messages` | PP-E4 |
| `e5f6a7b8c9d0` | `tenant_db_routes` | P4-E1 |
| `f6a7b8c9d0e1` | `webhook_registrations`, `integration_logs` | P4-E2 |
| `0a1b2c3d4e5f` | `capacity_offers`, `capacity_requests`, `capacity_matches` | P4-E3 |
| `1b2c3d4e5f6a` | `audit_log_entries`, `rbac_roles` | P4-E4 |

---

## Step 2 — Provision Redis

Celery (webhook delivery, GDPR export, retention sweep, marketplace matching) requires Redis.

**Option A — Render Redis (recommended, stays in same network):**
1. Render dashboard → **New → Redis** → free tier
2. Copy the **Internal Redis URL**

**Option B — Upstash (free tier, external):**
1. upstash.com → Create database → Copy `rediss://` URL

---

## Step 3 — Set environment variables on the Render API service

Go to: API service → **Environment** tab

| Variable | Value | Required |
|----------|-------|----------|
| `DATABASE_URL` | Supabase connection string | ✅ Already set |
| `REDIS_URL` | Redis URL from Step 2 | ✅ New |
| `JWT_SECRET_KEY` | Long random secret (32+ chars) | ✅ Must match between API + worker |
| `LLM_PROVIDER` | `gemini` \| `openai` \| `anthropic` | ✅ Already set |
| `GEMINI_API_KEY` | Your Gemini key | If using Gemini |
| `OPENAI_API_KEY` | Your OpenAI key | If using OpenAI |
| `ANTHROPIC_API_KEY` | Your Anthropic key | If using Anthropic |
| `SENTRY_DSN` | Sentry project DSN | Optional |
| `PLANNER_TYPE` | `rule_based` \| `ortools` \| `multi_agent` | Optional (default: `rule_based`) |
| `TENANT_MODE` | `multi` \| `single` | Optional (default: `multi`) |

> **Important:** `JWT_SECRET_KEY` is used for Fernet encryption of webhook secrets and DB connection strings (P4-E1/P4-E2). It **must be the same** on the API service and the Celery worker.

---

## Step 4 — Add a Celery Background Worker service on Render

Without a Celery worker, async features silently queue tasks but never run:
- Webhook delivery to partners (P4-E2)
- Marketplace match-now trigger (P4-E3)
- GDPR data export (P4-E4)
- Daily retention sweep (P4-E4)

**Setup:**
1. Render dashboard → **New → Background Worker**
2. Connect the same repo as your API service
3. **Start Command:**
   ```
   celery -A app.workers.celery_app worker --loglevel=info
   ```
4. **Environment Variables:** copy all from your API service (same `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, LLM keys)

---

## Step 5 — Push code and redeploy

If auto-deploy is enabled, pushing to your branch triggers both services automatically. Otherwise trigger a manual deploy on each service.

**New API endpoints active after redeploy:**

| Endpoint | Feature |
|----------|---------|
| `POST/GET/DELETE /api/v1/integrations/webhooks` | Webhook registry (P4-E2) |
| `POST /api/v1/integrations/ingest` | Partner order ingestion (P4-E2) |
| `GET /api/v1/integrations/tracking-feed` | Tracking feed for partners (P4-E2) |
| `GET /api/v1/integrations/logs` | Integration logs (P4-E2) |
| `POST/GET/DELETE /api/v1/marketplace/offers` | Capacity offers (P4-E3) |
| `POST/GET /api/v1/marketplace/requests` | Capacity requests (P4-E3) |
| `GET/PATCH /api/v1/marketplace/matches` | Match management (P4-E3) |
| `POST /api/v1/marketplace/match-now` | Manual match trigger (P4-E3) |
| `GET /api/v1/audit/log` | Immutable audit log (P4-E4) |
| `POST /api/v1/governance/data-export` | GDPR export trigger (P4-E4) |
| `GET/PATCH /api/v1/governance/retention` | Retention policy (P4-E4) |
| `GET/POST/DELETE /api/v1/governance/roles` | RBAC role management (P4-E4) |

---

## Step 6 — Redeploy the frontend (Render Static Site)

Verify this environment variable is set on your frontend static site service:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://your-api-service.onrender.com` |

**New pages visible after redeploy:**

| Route | Feature |
|-------|---------|
| `/integrations` | Webhook registry + integration logs |
| `/marketplace` | Capacity marketplace — Offers / Requests / Matches |
| `/governance` | Audit log + GDPR export + RBAC roles |

---

## Step 7 — (Optional) Re-seed demo data

The seed script covers Phase 1–3 data (orders, drivers, vehicles, depots, routes). Run it after migrations if you want a full demo dataset:

```bash
# From Render shell or locally with DATABASE_URL set
python scripts/seed_data.py --clean
python scripts/seed_data.py --start-date $(date +%Y-%m-%d)
```

Audit log entries will populate automatically as dispatchers interact with AI suggestions. Marketplace offers/requests can be created manually via the UI.

---

## Quick-reference summary

```
1. alembic upgrade head          ← against Supabase
2. Provision Redis               ← Render Redis or Upstash
3. Add REDIS_URL + JWT_SECRET_KEY to Render API env vars
4. Create Celery Background Worker service on Render
5. Push code → API auto-redeploys
6. Verify VITE_API_URL on frontend static site → redeploys
7. (Optional) Re-run seed script
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Webhooks queue but never deliver | No Celery worker running | Add Background Worker (Step 4) |
| `500` on `/integrations` or `/marketplace` | Migration not run | Run `alembic upgrade head` |
| `500` on `/governance/data-export` | No Redis / no Celery worker | Steps 2 + 4 |
| Frontend shows old pages, no Integrations/Marketplace/Governance nav | `VITE_API_URL` wrong or old build | Verify env var, trigger redeploy |
| Fernet decryption error in logs | `JWT_SECRET_KEY` mismatch between API and worker | Make sure both services share the same key |
