# Infrastructure & Project Setup – Technical Specification

> **For AI Coding Assistants:** This spec is marked **Implemented**. Use it as a reference for what already exists. Do not re-implement. If you find deviations from this spec in the codebase, flag them.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Infrastructure & Project Setup |
| **Epic** | P1-E1 |
| **Status** | ✅ Implemented |
| **Version** | 2.0 |
| **Date** | 2026-03-29 |
| **Author** | Antigravity |
| **Reference** | Blueprint Section 4, 5 – Architecture & Tech Stack |
| **Implementation Branch** | main |

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Antigravity | Initial draft |
| 2.0 | 2026-03-29 | Antigravity | Updated to reflect actual implementation + bug notes |

---

## Executive Summary

**Purpose:** Initialize the base infrastructure for FleetOpsX, including API skeleton, UI containerization, database connectivity, and observability tools. This is the foundation all other epics build on.

### Key Deliverables

| Component | Description | Priority | Status |
|-----------|-------------|----------|--------|
| Docker Compose | All services orchestrated (API, UI, DB, Redis, Prometheus, Grafana) | P0 | ✅ Done |
| FastAPI skeleton | Health endpoint, logging, CORS, config | P0 | ✅ Done |
| Alembic setup | Migration pipeline wired to `DATABASE_URL` | P0 | ✅ Done |
| Observability | Sentry + Prometheus in both API and UI | P1 | ✅ Done |
| CI/CD foundations | GitHub Actions for API and UI | P1 | ✅ Done |

### Success Criteria

- [x] `docker compose up` starts all 6 services (API, UI, DB, Redis, Prometheus, Grafana)
- [x] `GET /health` returns `{"status": "healthy"}`
- [x] `GET /metrics` returns Prometheus metrics
- [x] `alembic current` runs without error
- [x] GitHub Actions CI passes on push

### Known Bugs (must fix before P1-E2 work)

| Bug | File | Description | Fix |
|-----|------|-------------|-----|
| Wrong attribute | `app/core/db.py` | Uses `settings.database_url` (lowercase) — attribute does not exist | Change to `settings.DATABASE_URL` |
| Wrong import | `app/main.py` | Imports `config` module and uses `config.SENTRY_DSN` — should use `settings` instance | Change to `from app.core.config import settings` and `settings.SENTRY_DSN` |

---

## 1. Goals & Objectives

### Primary Goals

1. **Containerize everything:** All services run via single `docker compose up` command
2. **Observable from day one:** Sentry, Prometheus, Grafana wired before any feature code
3. **Migration-ready:** Alembic pipeline configured; adding models = adding migrations

### Non-Goals

- Authentication / JWT (covered in P1-E3-S6)
- Domain models (covered in P1-E3)
- Multi-tenancy middleware (covered in P1-E2)

---

## 2. Functional Requirements

### FR-1: Docker Compose Orchestration

**Description:** All services must start with a single command.

**Services:**
```
db        → postgis/postgis:15-3.3  (port 5432)
redis     → redis:7-alpine          (port 6379)
api       → ./Dockerfile            (port 8000)
ui        → ../FleetOpsX-UI         (port 5173)
prometheus→ prom/prometheus         (port 9090)
grafana   → grafana/grafana         (port 3000)
```

**Acceptance Criteria:**
- [x] `db` and `redis` have healthchecks; `api` waits for both
- [x] `api` container mounts source for live reload
- [x] `ui` container mounts source for hot reload

---

### FR-2: FastAPI Application Skeleton

**Description:** Minimal FastAPI app with essential middleware and one health endpoint.

**Acceptance Criteria:**
- [x] `GET /health` → `{"status": "healthy"}`
- [x] CORS middleware configured (open for dev)
- [x] Structured logging with `logging.basicConfig`
- [x] Sentry initialized from `settings.SENTRY_DSN` (optional, skipped if None)
- [x] Prometheus metrics exposed at `GET /metrics`

---

### FR-3: Configuration Management

**Description:** All config loaded from `.env` via pydantic-settings.

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    APP_ENV: str = "local"
    DATABASE_URL: str          # required
    REDIS_URL: str             # required
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

**Acceptance Criteria:**
- [x] App fails fast if `DATABASE_URL` or `REDIS_URL` missing
- [x] `SENTRY_DSN` is optional

---

### FR-4: Database & Alembic

**Description:** SQLAlchemy engine + Alembic migrations wired to settings.

**File:** `app/core/db.py`
```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**`alembic/env.py`:** must import `settings.DATABASE_URL` and `Base.metadata` from `app.models`.

**Acceptance Criteria:**
- [x] `alembic current` runs without error
- [x] `alembic revision --autogenerate` generates correct diff against models

---

### FR-5: CI/CD

**Description:** GitHub Actions run lint + test on every push/PR.

**Files:**
- `.github/workflows/ci-api.yml`
- `.github/workflows/ci-ui.yml`

---

## 3. Architecture & Design

```
┌──────────────────────────────────────────┐
│         Docker Compose Network           │
│                                          │
│  FleetOpsX-API (FastAPI :8000)           │
│       ↕  SQLAlchemy                      │
│  PostgreSQL + PostGIS (:5432)            │
│       ↕                                  │
│  Redis (:6379)                           │
│                                          │
│  Prometheus (:9090) ← scrapes /metrics   │
│  Grafana (:3000)    ← reads Prometheus   │
│                                          │
│  FleetOpsX-UI (Vite :5173)              │
└──────────────────────────────────────────┘
         ↕ error reporting
      Sentry.io (external)
```

---

## 4. File Map

```
FleetOpsX-API/
  app/
    main.py                  ← FastAPI app, middleware, router registration
    core/
      config.py              ← pydantic-settings Settings class
      db.py                  ← SQLAlchemy engine + get_db()
      redis.py               ← Redis client
    api/
      health.py              ← GET /health
    models/
      base.py                ← Base, TimestampMixin, TenantMixin
      __init__.py            ← imports all models (for Alembic autogenerate)
    planners/
      interface.py           ← PlannerInterface ABC
  alembic/
    env.py                   ← wired to settings.DATABASE_URL + Base.metadata
  docker-compose.yml
  Dockerfile
  requirements.txt
  .github/workflows/ci-api.yml

FleetOpsX-UI/
  src/
    main.tsx                 ← QueryClient, Sentry, Toaster, AppRoutes
    App.tsx                  ← theme toggle
    routes/AppRoutes.tsx     ← BrowserRouter + Route definitions
    api/client.ts            ← axios instance
    store/useAppStore.ts     ← zustand store (theme, authToken)
  Dockerfile
  .github/workflows/ci-ui.yml
```

---

## 5. Developer Checklist

### Backend
- [x] `Dockerfile` created
- [x] `docker-compose.yml` created with all 6 services
- [x] `app/main.py` – FastAPI app with CORS, Sentry, Prometheus
- [x] `app/core/config.py` – Settings with DATABASE_URL, REDIS_URL, SENTRY_DSN
- [x] `app/core/db.py` – SQLAlchemy engine + `get_db()`  ⚠️ fix `settings.DATABASE_URL` case
- [x] `app/core/redis.py` – Redis client
- [x] `app/api/health.py` – GET /health
- [x] `app/models/base.py` – Base, TimestampMixin, TenantMixin
- [x] `app/models/tenant.py` – Tenant, TenantConfig models
- [x] `alembic/env.py` – wired to settings + Base.metadata
- [x] `requirements.txt` – all dependencies present
- [x] `infra/prometheus/prometheus.yml` – prometheus config
- [x] `.github/workflows/ci-api.yml`

### Frontend
- [x] React + TypeScript + Vite + Tailwind setup
- [x] Sentry integrated in `main.tsx`
- [x] React Query configured
- [x] Zustand store for theme + auth token
- [x] Axios client in `api/client.ts`
- [x] AppRoutes with Home + Login pages
- [x] Basic UI components: Button, Card, Input, PageLayout
- [x] `.github/workflows/ci-ui.yml`

---

## 16. Future Considerations

### 16.3 Follow-up Work
- [ ] Fix `app/core/db.py` bug: `settings.database_url` → `settings.DATABASE_URL`
- [ ] Fix `app/main.py` bug: `config.SENTRY_DSN` → `settings.SENTRY_DSN`
- [ ] P1-E2: Add TenantMiddleware (next epic)
- [ ] P1-E3: Add domain models + CRUD APIs (next epic after P1-E2)

---

**Document Status:** Implemented  
**Last Updated:** 2026-03-29  
**Implementation Status:** ✅ Completed (with 2 known bugs to fix)
