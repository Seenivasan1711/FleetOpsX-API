# GENSPEC – Multi-Tenant Implementation

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Multi-Tenant Foundations (P1-E2) |
| **Status** | Draft |
| **Version** | 1.0 |
| **Date** | 2025-12-25 |
| **Author** | Antigravity |

---

## 1. Goal

Implement the core multi-tenancy logic in the FastAPI backend, including models, middleware, and database filtering.

---

## 2. Implementation Guide

### Checkpoint 1: Models & Migrations

**Tasks:**
- Create `app/models/tenant.py` with `Tenant` and `TenantConfig`.
- Create `Mixin` in `app/models/base.py`.
- Run `alembic revision --autogenerate -m "Add tenant models"`.

**Verification:**
- Migration file contains `tenants` and `tenant_configs` tables.

---

### Checkpoint 2: Tenant Context & Middleware

**Tasks:**
- Create `app/core/context.py` using `contextvars.ContextVar`.
- Create `app/core/middleware.py` with `TenantMiddleware`.
- Register middleware in `app/main.py`.

**Verification:**
- Middleware correctly fails if `X-Tenant-ID` is missing (or defaults to a system-level ID).

---

### Checkpoint 3: Tenant-Aware Database Session

**Tasks:**
- Update `app/core/db.py` to provide a session that knows about the current tenant.
- Implement a helper or hook to inject `tenant_id` into all `session.add()` calls.

**Verification:**
- New records automatically have the correct `tenant_id` without manually setting it.
