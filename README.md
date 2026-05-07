# FleetOpsX — Agentic Fleet Operations Platform

> **Autonomy for every fleet.** FleetOpsX is a multi-tenant AI platform that centralises last-mile fleet operations — order management, driver dispatch, route planning, and real-time delivery tracking — evolving from rule-based heuristics today to autonomous multi-agent orchestration in Phase 2.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker — Recommended)](#quick-start-docker--recommended)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Seed Demo Data](#seed-demo-data)
- [Local Development (without Docker)](#local-development-without-docker)
- [API Reference](#api-reference)
- [Observability](#observability)
- [Demo Walkthrough](#demo-walkthrough)
- [Renewing the Render Free-Tier Database](#renewing-the-render-free-tier-database)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FleetOpsX Platform                       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Dispatcher  │    │  Driver App  │    │   API Docs    │  │
│  │  Dashboard   │    │  (Mobile Web)│    │  /docs        │  │
│  │  :5173       │    │  /driver     │    │  :8000        │  │
│  └──────┬───────┘    └──────┬───────┘    └───────────────┘  │
│         │                   │                                │
│         └──────────┬────────┘                                │
│                    ▼                                         │
│         ┌──────────────────┐                                 │
│         │   FastAPI (BE)   │  ← JWT Auth, Multi-Tenant       │
│         │     :8000        │  ← Rule-Based Planner (v1)      │
│         └────┬────────┬────┘  ← LangGraph Agent (Phase 2)   │
│              │        │                                      │
│    ┌─────────▼──┐  ┌──▼──────────┐                          │
│    │ PostgreSQL │  │    Redis     │                          │
│    │  PostGIS   │  │   Cache      │                          │
│    │   :5600    │  │   :6379      │                          │
│    └────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
FleetOpsX-API/                  ← This repo (backend + docker-compose)
├── app/
│   ├── api/
│   │   ├── v1/                 ← Route handlers (auth, orders, planning, driver, …)
│   │   └── deps.py             ← JWT dependency injection
│   ├── core/
│   │   ├── config.py           ← Pydantic Settings
│   │   ├── db.py               ← SQLAlchemy engine + session
│   │   ├── middleware.py       ← Multi-tenant middleware
│   │   └── security.py        ← JWT + bcrypt
│   ├── models/                 ← SQLAlchemy ORM models
│   ├── planners/
│   │   ├── interface.py        ← Pluggable PlannerInterface (ABC)
│   │   └── rule_based.py       ← Greedy nearest-driver planner (Phase 1)
│   ├── schemas/                ← Pydantic request/response schemas
│   └── services/               ← Business logic layer
├── alembic/                    ← Database migrations
├── scripts/
│   ├── seed_data.py            ← Bangalore demo data generator
│   └── render_db_renew.sh      ← Renew expiring Render free-tier DB
├── docker-compose.yml          ← Full stack (DB, Redis, API, UI, Prometheus, Grafana)
├── Dockerfile                  ← API container
└── .env                        ← Local environment variables

FleetOpsX-UI/                   ← Frontend repo (sibling directory)
├── src/
│   ├── api/                    ← Axios API clients
│   ├── components/             ← Shared UI components + layout
│   ├── pages/                  ← Route-level page components
│   ├── routes/                 ← Protected routing
│   ├── store/                  ← Zustand state (auth + theme)
│   └── types/                  ← TypeScript interfaces
└── Dockerfile
```

---

## Tech Stack

### Backend
| Layer | Technology |
|-------|------------|
| API Framework | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 + PostGIS 3.3 |
| ORM & Migrations | SQLAlchemy 2 + Alembic |
| Caching | Redis 7 |
| Authentication | JWT (python-jose) + bcrypt |
| Task Queue | Celery 5 + Redis broker (webhook delivery, marketplace) |
| Scheduler | APScheduler (ETL, monitor scan, route cache, match engine) |
| Observability | Sentry, Prometheus, Grafana, Loguru |
| Planner v1 | Rule-based greedy (Haversine distance) |
| Planner v2 *(Phase 2)* | LangGraph multi-agent + OR-Tools VRPTW |

### Frontend
| Layer | Technology |
|-------|------------|
| Framework | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS |
| State | Zustand (persist) + TanStack React Query v5 |
| Forms | react-hook-form + Zod validation |
| Routing | React Router v7 |
| Notifications | react-hot-toast |

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker | 24+ | Required for the full stack |
| Docker Compose | v2 | Bundled with Docker Desktop |
| Python | 3.11+ | Only needed for local dev / migrations |
| Node.js | 20+ | Only needed for local frontend dev |

---

## Quick Start (Docker — Recommended)

The `docker-compose.yml` in this repository starts the **entire stack** with a single command — no separate terminal windows needed.

### Step 1 — Clone both repositories (sibling directories)

```bash
git clone <api-repo-url> FleetOpsX-API
git clone <ui-repo-url>  FleetOpsX-UI
```

> Both repos must be sibling directories. The docker-compose.yml references `../FleetOpsX-UI`.

### Step 2 — Configure environment

Create a `.env` file in `FleetOpsX-API/`:

```bash
cp .env.example .env   # or create manually — see Environment Variables below
```

### Step 3 — Build and start all services

```bash
cd FleetOpsX-API
docker compose up -d
```

This starts six services:

| Service | URL | Description |
|---------|-----|-------------|
| **UI** | http://localhost:5173 | React dispatcher dashboard |
| **API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **Database** | localhost:5600 | PostgreSQL + PostGIS |
| **Redis** | localhost:6379 | Cache + Celery broker |
| **Prometheus** | http://localhost:9090 | Metrics scraper |
| **Grafana** | http://localhost:3000 | Dashboards (admin / admin) |

> **Celery worker** (for webhook delivery + marketplace matching) is not started by `docker compose up` by default. See [Celery Worker](#celery-worker) below.

### Step 4 — Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### Step 5 — Seed demo data

```bash
docker compose exec api python scripts/seed_data.py --start-date $(date +%Y-%m-%d)
```

The script prints a **Tenant ID** at the end — copy it, you need it to log in.

```
🎉 Done! Tenant ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Step 6 — Open the app

Go to **http://localhost:5173/login** and sign in with:

| Role | Email | Password | Tenant ID |
|------|-------|----------|-----------|
| Dispatcher | dispatcher@demo.com | demo1234 | *(from seed output)* |
| Driver | driver@demo.com | demo1234 | *(from seed output)* |

---

## Celery Worker

Celery handles **webhook delivery** (partner integrations) and **marketplace matching**. Without a running worker, these features queue tasks silently — they will execute once a worker comes online.

### Local setup

Open a **second terminal** after starting the API:

```bash
cd FleetOpsX-API
source venv/bin/activate

# Start Celery worker (processes tasks from Redis queue)
celery -A app.workers.celery_app worker --loglevel=info

# Optional: Flower monitoring UI → http://localhost:5555
celery -A app.workers.celery_app flower
```

The worker uses the same `REDIS_URL` from `.env`. No extra config needed.

### Docker Compose setup

Add a worker service to `docker-compose.yml` (or run alongside the API container):

```bash
# One-liner: run the worker in the same container as the API
docker compose exec api celery -A app.workers.celery_app worker --loglevel=info
```

Or add a dedicated service in `docker-compose.yml`:

```yaml
celery-worker:
  build: .
  command: celery -A app.workers.celery_app worker --loglevel=info
  env_file: .env
  depends_on:
    - db
    - redis
  restart: unless-stopped
```

### Render setup

In your Render dashboard, add a **Background Worker** service pointing to the same Docker image:

1. **Render Dashboard → New → Background Worker**
2. **Source:** same Git repo as your API service
3. **Start Command:** `celery -A app.workers.celery_app worker --loglevel=info`
4. **Environment Variables:** copy all from your API service (same `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, LLM keys)
5. **Plan:** Starter (the free tier sleeps and won't process tasks reliably)

> **Redis on Render:** Use [Render Redis](https://render.com/docs/redis) or [Upstash](https://upstash.com) (free tier). Set `REDIS_URL` to the external Redis URL in both the API service and the Celery worker service.

**Minimal Render environment for the worker:**

```env
DATABASE_URL=postgresql://...   # same as API
REDIS_URL=redis://...           # same Redis instance
JWT_SECRET_KEY=...              # same secret (for webhook HMAC key derivation)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | Full PostgreSQL connection string |
| `REDIS_URL` | Yes | — | Redis connection string |
| `JWT_SECRET_KEY` | Yes | `change-me-in-production` | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | No | `1440` | Token lifetime (24 hours) |
| `PLANNER_TYPE` | No | `rule_based` | Planner to use (`rule_based` or `langgraph`) |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |
| `MAPS_API_KEY` | No | — | Google Maps API key (enables real routing) |

**Example `.env`:**

```env
DATABASE_URL=postgresql+psycopg2://fleetuser:fleetpass@localhost:5600/fleetopsx
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-here
JWT_EXPIRE_MINUTES=1440
PLANNER_TYPE=rule_based
```

---

## Database Migrations

Migrations are managed with Alembic. The migration history:

| Revision | Description |
|----------|-------------|
| `69965e83503f` | P1-E2 — Tenant + TenantConfig tables |
| `9cfd8384148b` | P1-E3 — All 13 core domain tables |
| `486e6906d442` | P2-E3 — Agent logs |
| `3abca364f966` | P2-E4 — Driver location pings |
| `a1b2c3d4e5f6` | P3-E1 — Analytics tables |
| `b2c3d4e5f6a7` | P3-E2 — Agent suggestions |
| `c3d4e5f6a7b8` | PP-E3 — Driver availability + vehicle status |
| `d4e5f6a7b8c9` | PP-E4 — Chat messages |
| `e5f6a7b8c9d0` | P4-E1 — Tenant DB routes |
| `f6a7b8c9d0e1` | P4-E2 — Webhook registrations + integration logs |
| `0a1b2c3d4e5f` | P4-E3 — Capacity marketplace tables |

```bash
# Apply all pending migrations
venv/bin/alembic upgrade head

# Check current migration state
venv/bin/alembic current

# Create a new migration (after model changes)
venv/bin/alembic revision --autogenerate -m "description"

# Roll back one step
venv/bin/alembic downgrade -1
```

---

## Seed Demo Data

The seed script generates a complete Bangalore-based fleet dataset for demos and testing.

```bash
# Seed 3 days of data starting today
venv/bin/python scripts/seed_data.py

# Seed a specific date range
venv/bin/python scripts/seed_data.py --start-date 2026-03-29 --days 5

# Wipe demo data and re-seed
venv/bin/python scripts/seed_data.py --clean
venv/bin/python scripts/seed_data.py --start-date 2026-03-29
```

**What the seed script creates:**

| Resource | Count | Details |
|----------|-------|---------|
| Tenant | 1 | "FleetOpsX Demo" |
| Depots | 2 | Koramangala + Whitefield |
| Drivers | 20 | Across 2 depots, shifts 08:00–18:00 |
| Vehicles | 20 | Mix of VANs and BIKEs |
| Customers | 50 | Across 15 Bangalore neighbourhoods |
| Orders | 33/day | Priority mix: NORMAL 60%, HIGH 25%, LOW 10%, CRITICAL 5% |
| Users | 2 | dispatcher@demo.com + driver@demo.com |

---

## Local Development (without Docker)

### Backend

```bash
cd FleetOpsX-API

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL + Redis (Docker only, not the full stack)
docker compose up -d db redis

# Run migrations
alembic upgrade head

# Seed demo data
python scripts/seed_data.py --start-date $(date +%Y-%m-%d)

# Start API with hot-reload
uvicorn app.main:app --reload
```

**Optional — Celery worker** (second terminal, for webhooks + marketplace):

```bash
cd FleetOpsX-API
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Flower task monitor → http://localhost:5555
celery -A app.workers.celery_app flower
```

### Frontend

```bash
cd FleetOpsX-UI

npm install
npm run dev
```

---

## API Reference

The full interactive API documentation is available at **http://localhost:8000/docs** when the server is running.

### Key Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | — | Login — returns JWT token |
| `POST` | `/api/v1/auth/register` | — | Register a new user |
| `GET` | `/api/v1/orders/` | JWT | List orders (filterable by date, status) |
| `POST` | `/api/v1/orders/` | JWT | Create an order |
| `POST` | `/api/v1/plan/day` | JWT (dispatcher) | Generate route plan for a date |
| `GET` | `/api/v1/driver/my-stops` | JWT (driver) | Get today's assigned stops |
| `PATCH` | `/api/v1/driver/stops/{id}/status` | JWT (driver) | Update stop status |
| `GET` | `/api/v1/depots/` | JWT | List depots |
| `GET` | `/api/v1/drivers/` | JWT | List drivers |
| `GET` | `/api/v1/vehicles/` | JWT | List vehicles |
| `GET` | `/health` | — | Health check |
| `GET` | `/metrics` | — | Prometheus metrics |

### Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

The token is obtained from `POST /api/v1/auth/login` and contains the `tenant_id` — no separate header needed.

---

## Observability

| Tool | URL | Credentials |
|------|-----|-------------|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Sentry | *(cloud)* | Set `SENTRY_DSN` in `.env` |

API request metrics are automatically exported via `prometheus-fastapi-instrumentator` at `/metrics`.

---

## Demo Walkthrough

See **[DEMO_GUIDE.md](./DEMO_GUIDE.md)** for the full step-by-step investor demo script with screenshots prompts and talking points.

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Complete | Rule-based planner, multi-tenant CRUD, dispatcher dashboard, driver mobile view |
| **Phase 2** | ✅ Complete | OR-Tools VRPTW optimisation, LangGraph autonomous dispatch agent, real-time GPS + re-planning |
| **Phase 3** | ✅ Complete | Adaptive multi-agent orchestration, SLA risk alerts, proactive planning, historical analytics |
| **Phase P** | ✅ Complete | Planning AI enhancements, multi-plan options, driver/vehicle availability, Chat AI, Excel export/import, route map overlay, UI polish |
| **Phase 4** | 🔵 In Progress | P4-E1 (per-tenant DB routing) ✅ · P4-E2 (webhook integrations) ✅ · P4-E3 (capacity marketplace) ✅ · P4-E4 (governance/audit) · P4-E5 (multi-day planning) |

---

## Remote Database Seeding (Render Deployment)

If you have deployed the application to Render using Docker (which does not provide Shell access on the free tier), you can run initial database migrations and seed data directly from your local machine.

1. Copy the **External Database URL** from your Render PostgreSQL instance dashboard.
2. In your local `FleetOpsX-API` folder, activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Export the database URL and run the Alembic and seeder commands:
   ```bash
   export DATABASE_URL="YOUR_RENDER_EXTERNAL_DB_URL"
   alembic upgrade head
   python scripts/seed_data.py
   ```

---

## Renewing the Render Free-Tier Database

Render free PostgreSQL instances are deleted after **90 days**. Use `scripts/render_db_renew.sh` to dump the expiring database, delete it, create a fresh one, and restore the dump — all in one command.

### Prerequisites

`pg_dump` must be **≥ the server's Postgres version** (Render currently runs **Postgres 18**).

```bash
# macOS — install pg_dump / pg_restore matching Render's server version
brew install postgresql@18
```

Then set `PG_BIN` so the script uses the right binaries:

```bash
export PG_BIN=/opt/homebrew/opt/postgresql@18/bin
```

> If you're on Apple Silicon the path is `/opt/homebrew/...`; on Intel Mac it's `/usr/local/opt/...`.
> Run `brew --prefix postgresql@18` to confirm the exact path on your machine.

### Find your Render IDs

You need three values before running the script:

| Value | Where to find it |
|-------|-----------------|
| `RENDER_API_KEY` | Render dashboard → **Account Settings → API Keys** |
| `RENDER_OWNER_ID` | Render dashboard URL: `https://dashboard.render.com/u/usr_xxxx` — copy the `usr_xxxx` part |
| `OLD_DB_SERVICE_ID` | Run the command below to list DBs and grab the `"id"` of the expiring one |
| `OLD_DB_CONN` | Render dashboard → your PostgreSQL service → **Connect** → **External Connection String** |

```bash
# List all postgres services to find OLD_DB_SERVICE_ID
curl -fsSL -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.render.com/v1/postgres?ownerId=YOUR_OWNER_ID" | python3 -m json.tool
```

> **Note:** The Render API does not return the connection string — you must copy `OLD_DB_CONN` manually from the dashboard.

### Run the renewal script

```bash
export RENDER_API_KEY="rnd_xxxx"
export RENDER_OWNER_ID="usr_xxxx"
export OLD_DB_SERVICE_ID="dpg_xxxx"
export OLD_DB_CONN="postgresql://fleetuser:password@host/fleetopsx"   # from Render dashboard → Connect
export NEW_DB_NAME="fleetopsx-db"
export PG_BIN=$(brew --prefix postgresql@18)/bin                      # must match Render's PG version
export RENDER_DB_PLAN="free"                                           # free | starter | standard | pro

./scripts/render_db_renew.sh
```

### What happens

1. Fetches the expiring DB's connection string via Render API
2. Dumps to `/tmp/fleetopsx_<timestamp>.dump` using `pg_dump`
3. Deletes the old database on Render
4. Creates a fresh database (same name, user, region) and waits for it to be ready (~5–10 min)
5. Restores the dump with `pg_restore`
6. Prints the new `DATABASE_URL`

### After the script completes

Copy the printed `DATABASE_URL` and update it in your Render web service:

**Render dashboard → FleetOpsX API service → Environment → `DATABASE_URL` → Save → Restart service**

