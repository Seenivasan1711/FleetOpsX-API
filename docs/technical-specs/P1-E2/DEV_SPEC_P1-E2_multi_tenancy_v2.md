# Multi-Tenant Foundations – Technical Specification

> **For AI Coding Assistants:** Implement the checkpoints in order. Each checkpoint has a verification step — do not proceed to the next until verification passes. All code must follow the patterns defined in this spec exactly.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Multi-Tenant Foundations |
| **Epic** | P1-E2 |
| **Status** | 🔄 In Progress |
| **Version** | 2.0 |
| **Date** | 2026-03-29 |
| **Author** | Antigravity |
| **Reference** | Blueprint Section 6 – Multi-Tenancy Design; HLD_multi_tenancy.md |
| **Depends On** | P1-E1 (Infrastructure) – must be complete first |
| **Implementation Branch** | feat/p1-e2-multi-tenancy |

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Antigravity | Initial draft |
| 2.0 | 2026-03-29 | Antigravity | Full implementation spec with code, file paths, verification |

---

## Executive Summary

**Purpose:** Implement the core multi-tenancy foundation in the FastAPI backend. Every request will carry a tenant identity, every DB record will be scoped to a tenant, and all domain APIs will automatically filter by tenant. This is required before any domain CRUD (P1-E3) can be built.

### Key Deliverables

| Component | File | Priority | Status |
|-----------|------|----------|--------|
| Tenant context (ContextVar) | `app/core/context.py` | P0 | ⬜ Not started |
| Tenant middleware | `app/core/middleware.py` | P0 | ⬜ Not started |
| FastAPI deps (tenant + DB) | `app/api/deps.py` | P0 | ⬜ Not started |
| Register middleware in main | `app/main.py` | P0 | ⬜ Not started |
| First Alembic migration | `alembic/versions/` | P0 | ⬜ Not started |

### Success Criteria

- [ ] All requests to domain endpoints without `X-Tenant-ID` header return HTTP 400
- [ ] `GET /health` and `GET /metrics` do NOT require `X-Tenant-ID`
- [ ] `alembic upgrade head` creates `tenants` and `tenant_configs` tables
- [ ] `tenant_id` is stored in a per-request `ContextVar` accessible throughout the call stack

### Dependencies

| Dependency | Type | Status | Impact |
|------------|------|--------|--------|
| P1-E1 Infrastructure | Internal | ✅ Done | Provides FastAPI app, config, db session |
| Bug fix: `db.py` | Internal | ⬜ Needed | `settings.DATABASE_URL` case bug must be fixed first |
| Bug fix: `main.py` | Internal | ⬜ Needed | `settings.SENTRY_DSN` import bug must be fixed first |

---

## Pre-Work: Fix Existing Bugs

Before implementing P1-E2, fix these two bugs from P1-E1:

### Bug Fix 1: `app/core/db.py`

Replace entire file:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Bug Fix 2: `app/main.py`

Change import at top of file:
```python
# BEFORE (wrong):
from app.core import config
# ... later: config.SENTRY_DSN

# AFTER (correct):
from app.core.config import settings
# ... later: settings.SENTRY_DSN
```

### Bug Fix 3: `app/planners/interface.py`

Replace with properly typed ABC:

```python
from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from sqlalchemy.orm import Session


class PlannerInterface(ABC):

    @abstractmethod
    def plan_day(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
    ) -> dict[str, Any]:
        """
        Execute planning for a tenant on a given date.
        Returns dict with 'assignments' list and metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def replan(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Re-plan based on real-time context (delays, new orders, cancellations).
        """
        raise NotImplementedError
```

---

## 1. Goals & Objectives

### Primary Goals

1. **Per-request tenant isolation:** Every request has a tenant_id available to all layers without passing it manually
2. **Automatic DB scoping:** All domain queries are filtered by `tenant_id` — no service can accidentally read another tenant's data
3. **Clean abstraction:** Tenant context injected via FastAPI dependencies, not global state

### Non-Goals

- JWT authentication (covered in P1-E3-S6)
- Per-tenant dedicated databases (Phase 4 concern)
- Row-Level Security at the Postgres level (future hardening)

---

## 2. Functional Requirements

### FR-1: Tenant ContextVar

**Description:** Store current request's tenant_id in a Python `ContextVar` so it's accessible anywhere in the call stack without being passed as a parameter.

**File:** `app/core/context.py`

```python
from contextvars import ContextVar
from typing import Optional

tenant_context: ContextVar[Optional[str]] = ContextVar(
    "tenant_context", default=None
)

def get_current_tenant_id() -> Optional[str]:
    return tenant_context.get()

def set_current_tenant_id(tenant_id: str) -> None:
    tenant_context.set(tenant_id)
```

**Acceptance Criteria:**
- [ ] `get_current_tenant_id()` returns `None` when called outside a request
- [ ] `set_current_tenant_id("abc")` followed by `get_current_tenant_id()` returns `"abc"`

---

### FR-2: Tenant Middleware

**Description:** Extract `X-Tenant-ID` from every incoming request header and store it in the ContextVar. Skip tenant resolution for system paths.

**File:** `app/core/middleware.py`

```python
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.context import set_current_tenant_id

logger = logging.getLogger(__name__)

EXCLUDED_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            set_current_tenant_id(tenant_id)
            logger.debug(f"Tenant context set: {tenant_id}")
        else:
            logger.debug("No X-Tenant-ID header present")

        return await call_next(request)
```

**Acceptance Criteria:**
- [ ] `GET /health` works without `X-Tenant-ID` header
- [ ] `GET /api/v1/depots/` without header → returns HTTP 400 (enforced by deps, not middleware)
- [ ] Middleware does not block requests; enforcement is in `require_tenant_id` dep

---

### FR-3: FastAPI Dependencies

**Description:** Provide reusable FastAPI dependency functions that extract tenant_id from headers and inject it into route handlers.

**File:** `app/api/deps.py`

```python
import logging
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db

logger = logging.getLogger(__name__)


def get_tenant_id(
    x_tenant_id: Optional[str] = Header(default=None),
) -> Optional[str]:
    """Returns tenant_id or None. Use where tenant is optional."""
    return x_tenant_id


def require_tenant_id(
    tenant_id: Optional[str] = Depends(get_tenant_id),
) -> str:
    """Raises HTTP 400 if X-Tenant-ID header is missing. Use on all domain endpoints."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )
    return tenant_id
```

**Acceptance Criteria:**
- [ ] Route using `Depends(require_tenant_id)` returns 400 when header is missing
- [ ] Route using `Depends(require_tenant_id)` returns `tenant_id` string when header is present
- [ ] `get_db` is re-exported from deps for convenience in routers

---

### FR-4: Register Middleware in main.py

**Description:** Register `TenantMiddleware` in the FastAPI app after CORS middleware.

**Update `app/main.py`** — add these lines:

```python
from app.core.middleware import TenantMiddleware
from app.api.router import api_router

# After CORSMiddleware:
app.add_middleware(TenantMiddleware)

# Replace existing health router include with:
app.include_router(api_router)
```

**Final middleware order in main.py:**
```python
app.add_middleware(CORSMiddleware, ...)   # 1st - outermost
app.add_middleware(TenantMiddleware)      # 2nd - runs after CORS
```

---

### FR-5: API Router

**Description:** Create a central router that all domain routers plug into.

**File:** `app/api/router.py`

```python
from fastapi import APIRouter
from app.api import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
# Domain routers added here in P1-E3:
# api_router.include_router(depots.router, prefix="/api/v1")
# api_router.include_router(drivers.router, prefix="/api/v1")
# etc.
```

---

### FR-6: Alembic Migration for Tenant Models

**Description:** Generate and apply the first migration that creates `tenants` and `tenant_configs` tables.

**Command:**
```bash
alembic revision --autogenerate -m "P1_E2_add_tenant_models"
alembic upgrade head
```

**Expected tables after migration:**
- `tenants` — id (UUID PK), name, slug (unique), is_active, created_at, updated_at
- `tenant_configs` — id (UUID PK), tenant_id (FK), config_key, config_value (JSON), created_at, updated_at

**Acceptance Criteria:**
- [ ] Migration file generated in `alembic/versions/`
- [ ] `alembic upgrade head` runs without error
- [ ] `alembic current` shows `(head)`
- [ ] Both tables visible in Postgres

---

## 3. Architecture & Design

### Tenant Resolution Flow

```
Incoming Request
      │
      ▼
CORSMiddleware
      │
      ▼
TenantMiddleware
  ├── path in EXCLUDED_PATHS? → skip, call_next
  └── read X-Tenant-ID header
        ├── present → set_current_tenant_id(id) → call_next
        └── missing → call_next (enforcement is in deps, not here)
              │
              ▼
         Route Handler
              │
              ├── Depends(require_tenant_id)
              │     ├── header present → return tenant_id ✅
              │     └── header missing → HTTP 400 ❌
              │
              └── Depends(get_db) → SQLAlchemy Session
                    │
                    └── service layer receives (db, tenant_id)
                          └── all queries: WHERE tenant_id = :id
```

### Why middleware + deps (not just deps)?

The middleware sets the ContextVar so that any code in the call stack (including code that doesn't receive the tenant_id as a parameter) can call `get_current_tenant_id()`. The FastAPI dep is the explicit, type-safe enforcement layer for route handlers.

---

## 4. Data Model

### Table: `tenants`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Display name (e.g. "Amazon Logistics India") |
| `slug` | VARCHAR(255) | UNIQUE, INDEX | URL-safe identifier (e.g. "amazon-logistics") |
| `is_active` | BOOLEAN | default TRUE | Soft disable a tenant |
| `created_at` | TIMESTAMP | default now | |
| `updated_at` | TIMESTAMP | default now, on update | |

### Table: `tenant_configs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | |
| `tenant_id` | UUID | FK(tenants.id) CASCADE, INDEX | Owner tenant |
| `config_key` | VARCHAR(100) | NOT NULL, INDEX | e.g. `business_vertical`, `capacity_unit` |
| `config_value` | JSONB | NOT NULL | e.g. `"LAST_MILE_PARCEL"`, `{"unit": "kg"}` |
| `created_at` | TIMESTAMP | default now | |
| `updated_at` | TIMESTAMP | default now, on update | |

### Standard Config Keys

| Key | Example Value | Description |
|-----|---------------|-------------|
| `business_vertical` | `"LAST_MILE_PARCEL"` | `LAST_MILE_PARCEL`, `DAIRY_MILK`, `GROCERY`, `PHARMA` |
| `capacity_unit` | `"WEIGHT_KG"` | `WEIGHT_KG`, `VOLUME_L`, `CRATES`, `BOXES` |
| `time_window_style` | `"STRICT"` | `STRICT`, `SLOTS`, `RECURRING` |
| `features_enabled` | `["tracking", "sla_alerts"]` | Feature flags |

---

## 5. File Checklist

| Action | File | Status |
|--------|------|--------|
| FIX | `app/core/db.py` | ⬜ |
| FIX | `app/main.py` | ⬜ |
| FIX | `app/planners/interface.py` | ⬜ |
| CREATE | `app/core/context.py` | ⬜ |
| CREATE | `app/core/middleware.py` | ⬜ |
| CREATE | `app/api/deps.py` | ⬜ |
| CREATE | `app/api/router.py` | ⬜ |
| MODIFY | `app/main.py` | ⬜ |
| RUN | `alembic revision --autogenerate -m "P1_E2_add_tenant_models"` | ⬜ |
| RUN | `alembic upgrade head` | ⬜ |

---

## 6. Verification

Run these after implementation to confirm everything works:

```bash
# 1. Start services
docker compose up db redis -d

# 2. Apply migration
alembic upgrade head
# Expected: INFO [alembic.runtime.migration] Running upgrade -> xxxx, P1_E2_add_tenant_models

# 3. Check migration applied
alembic current
# Expected: xxxx (head)

# 4. Start API
docker compose up api -d

# 5. Health (no tenant header needed)
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# 6. Domain endpoint without header (must return 400)
curl http://localhost:8000/api/v1/depots/
# Expected: {"detail": "X-Tenant-ID header is required"}

# 7. Metrics (no tenant header needed)
curl http://localhost:8000/metrics | head -5
# Expected: prometheus metrics output
```

---

## 17. Developer Checklist

### Backend Tasks
- [ ] Fix `db.py` bug
- [ ] Fix `main.py` bug
- [ ] Fix `planners/interface.py` stub
- [ ] Create `app/core/context.py`
- [ ] Create `app/core/middleware.py`
- [ ] Create `app/api/deps.py`
- [ ] Create `app/api/router.py`
- [ ] Update `app/main.py` to register middleware + api_router
- [ ] Run alembic migration
- [ ] Verify all 7 curl checks pass

---

**Document Status:** In Progress  
**Last Updated:** 2026-03-29  
**Implementation Status:** ⬜ Not Started
