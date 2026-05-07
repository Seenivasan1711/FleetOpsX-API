# Phase 4 – Fleet Intelligence Platform

> **Status:** Ready for implementation — detailed spec written after Phase 3 shipped.
> **Supersedes:** P4 section of `DEV_SPEC_P3_P4_multi_agent_enterprise_v1.md` (high-level only)

---

## Document Information

| Field | Value |
|-------|-------|
| **Phase** | Phase 4 |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | Phase 1 ✅ + Phase 2 ✅ + Phase 3 ✅ fully complete |
| **Author** | Engineering Team |

---

## Phase Goal

FleetOpsX becomes an **enterprise-grade SaaS fleet intelligence platform**. Multi-region infrastructure, external ecosystem integrations, a capacity marketplace, enterprise governance, and strategic multi-day planning with scenario simulation. This is the phase that wins large contracts and Series A conversations.

> Investor milestone: **"Enterprise Scale"** — large fleets, partner integrations, marketplace, and strategic planning tools that no point solution offers.

---

## Source Document Alignment Notes

> Records how this spec relates to original product/HLD docs and decisions made at spec-time.

| Note | Detail |
|------|--------|
| **APScheduler → Celery in P4** | `DEV_SPEC_P3_adaptive_multi_agent_v1.md` documents that APScheduler was chosen for Phase 3 because Celery is unnecessary complexity for a few in-process jobs. Phase 4 reverses this: marketplace matching, ETL at scale, and partner webhook retries need a proper distributed task queue. P4-E2 introduces Celery + Redis broker. |
| **Per-tenant DB routing** | `architecture.md §3` describes shared DB with tenant isolation as Phase 1–3 strategy. Phase 4 implements the per-tenant DB routing planned from day one (`Shared DB with tenant_id — simplest start; per-tenant DB routing in Phase 4`). Migration is backwards-compatible: default still hits `SessionLocal()`. |
| **RBAC/ABAC replaces current role check** | Current auth uses a simple `role` string (`dispatcher` / `driver`). Phase 4 replaces this with fine-grained RBAC with resource-scoped permissions. Existing `require_dispatcher` / `require_driver` deps continue working as role shorthands. |
| **Scenario Simulator is a new UI page** | `scope.md §4.2.2` describes scenario simulation ("What if we open a new depot?", "What if 30% EV fleet?"). No backend or frontend component exists yet. P4-E5 introduces the `ScenarioRun` model, simulation service, and React simulation wizard. |
| **Multi-day planning extends ORToolsPlanner** | `scope.md §4.2.1` describes multi-day horizon. P4-E5 extends `ORToolsPlanner` with a rolling-horizon solver (multiple plan_dates in one call). Not a rewrite — `PlannerInterface` signature adds optional `horizon_days` parameter. |
| **Marketplace is cross-tenant** | `CapacityMatch` records have no `tenant_id` — they join two tenants. Multi-tenant middleware must be bypassed for marketplace endpoints. Scope: platform-admin + participating tenants only. |
| **Webhooks use Celery retry** | Partner webhook delivery uses Celery tasks with exponential backoff (3 retries, max 1 hour). In-process delivery is acceptable for Phase 3's small volume but not for P4 enterprise SLAs. |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           Phase 4 Architecture                                  │
│                                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                     FleetOpsX Frontend (React)                          │    │
│  │  Dashboard │ Analytics │ Planning │ Scenario Simulator (P4-E5 new)      │    │
│  │  Governance Audit Log  │ Marketplace │ Admin — Partner Config           │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                              │ HTTP / WebSocket                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                          FastAPI Backend                                  │   │
│  │                                                                           │   │
│  │  /integrations/*   ← Partner ingest + webhook registry (P4-E2)          │   │
│  │  /marketplace/*    ← Capacity offers + matching (P4-E3)                 │   │
│  │  /audit/*          ← Immutable audit log (P4-E4)                        │   │
│  │  /scenarios/*      ← Scenario run + results (P4-E5)                     │   │
│  │  /plan/multi-day   ← Rolling-horizon VRPTW (P4-E5)                      │   │
│  │                                                                           │   │
│  │  DB Routing layer: get_db_for_tenant() → dedicated | shared (P4-E1)     │   │
│  │                                                                           │   │
│  │  Celery Workers (P4-E2+)                                                 │   │
│  │    ├── webhook_delivery_task (retry x3, backoff)                         │   │
│  │    ├── marketplace_match_task (every 5 min)                              │   │
│  │    └── scenario_run_task (async, results pushed to Redis pub/sub)        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌───────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐  │
│  │  Shared Postgres   │   │  Per-tenant Postgres  │   │  Redis (Celery +     │  │
│  │  (default tenants) │   │  (enterprise tenants) │   │   cache + pub/sub)   │  │
│  └───────────────────┘   └──────────────────────┘   └──────────────────────┘  │
│                                                                                 │
│  New DB Tables:                                                                 │
│    tenant_db_routes, webhook_registrations, integration_logs,                  │
│    capacity_offers, capacity_requests, capacity_matches,                        │
│    audit_log_entries, scenario_runs, scenario_results                          │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Epic Summary

| Epic | Area | Description | Depends On |
|------|------|-------------|-----------|
| **P4-E1** | Backend | Multi-Region & Per-Tenant DB Routing | P3 complete |
| **P4-E2** | Backend + FE | Partner APIs & Webhook Integration (ERP/WMS/TMS) | P4-E1 |
| **P4-E3** | Backend + FE | Capacity Marketplace | P4-E1 |
| **P4-E4** | Backend + FE | Governance, Compliance & Audit | P4-E1 |
| **P4-E5** | Backend + FE | Multi-Day Strategic Planning & Scenario Simulator | P4-E1 + P3-E1 |

---

---

## Epic P4-E1: Multi-Region & Per-Tenant DB Routing

### Goal
Enable enterprise tenants to have dedicated database instances while keeping the shared DB for smaller tenants. Support on-prem and single-tenant deployment mode. Zero downtime migration path for existing tenants.

### Key Design Decisions
- `get_db_for_tenant(tenant_id)` is the central routing function — all endpoints use it via the existing `get_db` dependency.
- A `TenantDbRoute` table maps `tenant_id → connection_string` for dedicated tenants.
- The routing table is loaded into a module-level dict at startup and refreshed every 60s (no restart needed to add a dedicated tenant).
- `TENANT_MODE=single` env var collapses multi-tenancy — all requests resolve to the single DB, useful for on-prem deployment.
- Region config is stored as a `TenantConfig` key (`config_key="region"`) — no new model needed.

### New Model

#### `TenantDbRoute`
```python
# app/models/tenant_db_route.py
class TenantDbRoute(Base, TimestampMixin):
    __tablename__ = "tenant_db_routes"

    id                = UUID PK
    tenant_id         = UUID unique FK → tenants
    connection_string = String(500)   # encrypted at rest
    region            = String(100)   # "us-east-1", "ap-south-1", etc.
    is_active         = Boolean default True
    max_pool_size     = Integer default 10
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/models/tenant_db_route.py` | **New** | `TenantDbRoute` model |
| `app/models/__init__.py` | Update | Register `TenantDbRoute` |
| `alembic/versions/` | **New** | Migration for `tenant_db_routes` |
| `app/core/db.py` | Update | `get_db_for_tenant(tenant_id)` router + session pool map |
| `app/core/config.py` | Update | `TENANT_MODE: str = "multi"` + `DB_ROUTE_REFRESH_INTERVAL: int = 60` |
| `app/api/deps.py` | Update | `get_db` uses `get_db_for_tenant(current_tenant_id)` |
| `app/api/v1/admin.py` | **New** | `POST /admin/tenant-db-routes` (platform admin only) |
| `app/workers/scheduler.py` | Update | Add route refresh job every 60s |

### Routing Logic (pseudo-code)
```python
# app/core/db.py
_route_cache: dict[str, sessionmaker] = {}  # tenant_id → session factory

def _refresh_route_cache(db: Session):
    routes = db.query(TenantDbRoute).filter_by(is_active=True).all()
    for r in routes:
        engine = create_engine(decrypt(r.connection_string), pool_size=r.max_pool_size)
        _route_cache[str(r.tenant_id)] = sessionmaker(engine)

def get_db_for_tenant(tenant_id: str) -> Session:
    if settings.TENANT_MODE == "single":
        return SessionLocal()
    factory = _route_cache.get(tenant_id)
    if factory:
        return factory()
    return SessionLocal()  # shared DB fallback
```

### API Endpoints

#### `POST /api/v1/admin/tenant-db-routes`
Request:
```json
{ "tenant_id": "...", "connection_string": "postgresql://...", "region": "ap-south-1" }
```
Response: `TenantDbRouteOut` (connection_string masked).

### Verification
- Default tenant hits shared DB
- Dedicated tenant hits its own DB (different `pg_database()` result)
- Route refresh picks up new route without restart

---

---

## Epic P4-E2: Partner APIs & Webhook Integration

### Goal
Enterprise customers push orders from ERP/WMS/TMS directly into FleetOpsX without manual CSV import. Delivery status and ETAs are streamed back to partner systems via webhooks. Celery handles webhook delivery reliability.

### Key Design Decisions
- **Ingest API** normalizes partner payloads to the canonical `Order` model via adapter pattern.
- **Adapters** are plug-in classes (`BaseAdapter.transform(raw) → OrderCreate`) — easy to add new integrations.
- **Webhook registry** stores partner callback URLs per event type.
- **Celery** replaces APScheduler for webhook delivery — needs retry semantics that APScheduler lacks.
- Idempotency: each ingest request carries a `partner_order_id`; duplicate ingests are detected and skipped.

### New Models

#### `WebhookRegistration`
```python
# app/models/integration.py
class WebhookRegistration(Base, TimestampMixin, TenantMixin):
    __tablename__ = "webhook_registrations"

    id          = UUID PK
    url         = String(500)       # partner callback URL
    event_types = ARRAY(String)     # ["order.delivered", "order.delayed", "route.updated"]
    secret      = String(200)       # HMAC signing secret (hashed)
    is_active   = Boolean default True
    last_error  = Text (nullable)
```

#### `IntegrationLog`
```python
class IntegrationLog(Base, TimestampMixin, TenantMixin):
    __tablename__ = "integration_logs"

    id              = UUID PK
    partner_order_id = String(200) unique    # idempotency key
    source_system   = String(100)           # "SAP", "Shopify", "generic"
    raw_payload     = JSON                  # original partner data
    normalized      = Boolean               # successfully mapped to Order
    order_id        = UUID FK → orders (nullable)
    error_message   = Text (nullable)
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | Update | Add `celery>=5.3`, `flower>=2.0` (Celery monitoring) |
| `app/models/integration.py` | **New** | `WebhookRegistration` + `IntegrationLog` models |
| `app/models/__init__.py` | Update | Register integration models |
| `alembic/versions/` | **New** | Migration for integration tables |
| `app/integrations/__init__.py` | **New** | Empty init |
| `app/integrations/base_adapter.py` | **New** | `BaseAdapter(ABC)` with `transform(raw: dict) → OrderCreate` |
| `app/integrations/adapters/sap_adapter.py` | **New** | Maps SAP IDOC/JSON fields to `OrderCreate` |
| `app/integrations/adapters/shopify_adapter.py` | **New** | Maps Shopify order webhook to `OrderCreate` |
| `app/integrations/adapters/generic_adapter.py` | **New** | Flexible field-mapping via config dict |
| `app/integrations/ingest_service.py` | **New** | Adapter selector + idempotency check + `Order` creation |
| `app/integrations/webhook_service.py` | **New** | `dispatch_event(event_type, payload, db, tenant_id)` |
| `app/workers/celery_app.py` | **New** | Celery app init (Redis broker + backend) |
| `app/workers/tasks.py` | **New** | `deliver_webhook_task` (Celery task, retry x3, backoff 30s/5min/1hr) |
| `app/api/v1/integrations.py` | **New** | Ingest, tracking feed, webhook CRUD endpoints |
| `app/api/router.py` | Update | Register integrations router |
| `app/schemas/integration.py` | **New** | `WebhookRegistrationIn/Out`, `IngestRequest`, `IngestResult` |
| `src/api/integrations.ts` | **New** | `fetchWebhooks()`, `createWebhook()`, `deleteWebhook()`, `fetchIntegrationLogs()` |
| `src/pages/Integrations.tsx` | **New** | Webhook registry table + log viewer + test fire button |
| `src/routes/AppRoutes.tsx` | Update | Add `/integrations` route |
| `src/components/layout/AppLayout.tsx` | Update | Add "Integrations" nav item |

### API Endpoints

#### `POST /api/v1/integrations/ingest`
```json
// Request
{
  "source_system": "SAP",
  "partner_order_id": "SAP-12345",
  "payload": { ...raw SAP fields... }
}

// Response
{ "order_id": "...", "status": "created", "idempotent": false }
// idempotent: true if order already existed (duplicate ingest skipped)
```

#### `GET /api/v1/integrations/tracking-feed?order_ids[]=...`
```json
[
  { "order_id": "...", "status": "IN_TRANSIT", "driver_name": "Ravi", "eta_minutes": 12, "last_ping_at": "..." }
]
```

#### `POST /api/v1/integrations/webhooks`
```json
{ "url": "https://partner.example.com/fleet-events", "event_types": ["order.delivered", "order.delayed"], "secret": "..." }
```

#### `GET /api/v1/integrations/logs?since=YYYY-MM-DD`
Returns recent `IntegrationLog` rows for audit/debugging.

### Webhook Delivery
```
Delivery event fires (e.g. stop marked DELIVERED in driver app)
  → webhook_service.dispatch_event("order.delivered", payload, db, tenant_id)
  → Queries WebhookRegistration for matching event_type
  → For each matching webhook: deliver_webhook_task.apply_async(args=[webhook_id, payload])
  → Celery task: POST to url with HMAC-SHA256 signature header
  → On failure: retry after 30s → 5min → 1hr → give up, log error
```

### Adapter Pattern
```python
# app/integrations/base_adapter.py
class BaseAdapter(ABC):
    @abstractmethod
    def transform(self, raw: dict) -> OrderCreate:
        """Normalize partner payload to canonical Order schema."""

# app/integrations/adapters/sap_adapter.py
class SAPAdapter(BaseAdapter):
    def transform(self, raw: dict) -> OrderCreate:
        return OrderCreate(
            delivery_address=raw["ADRC"]["CITY1"] + ", " + raw["ADRC"]["STREET"],
            priority=_map_sap_priority(raw.get("VSART")),
            ...
        )
```

### Verification
- POST `/integrations/ingest` with SAP payload → Order created in DB
- Duplicate ingest with same `partner_order_id` → idempotent=true, no duplicate order
- Mark stop delivered → webhook fires to registered URL (test with ngrok or webhook.site)
- Celery worker retry: kill the target URL → task retries 3x with backoff

---

---

## Epic P4-E3: Capacity Marketplace

### Goal
Fleets with excess capacity can offer driver-hours to other tenants. Fleets with overflow orders can request coverage. Platform matches offers to requests and tracks cross-tenant settlement. Fully opt-in — tenants must explicitly list and request capacity.

### Key Design Decisions
- `CapacityMatch` has no `tenant_id` — it is a cross-tenant record owned by the platform.
- Matching runs as a Celery periodic task every 5 minutes during business hours.
- Matching algorithm: greedy closest-zone match (Phase 4); auction-based matching is Phase 5.
- Settlement tracking is reporting-only in Phase 4 — no payment processing.
- Offers and requests expire (`expires_at`) — stale entries auto-archived.

### New Models

#### `CapacityOffer`
```python
# app/models/marketplace.py
class CapacityOffer(Base, TimestampMixin, TenantMixin):
    __tablename__ = "capacity_offers"

    id               = UUID PK
    offer_date       = Date             # which day capacity is available
    driver_count     = Integer          # number of available driver-slots
    vehicle_type     = String(50)       # "VAN", "TRUCK", "BIKE" (nullable = any)
    zone             = String(100)      # city/region where capacity is located
    rate_per_stop    = Float (nullable) # pricing hint (display only, no payment)
    status           = String(20)       # OPEN | MATCHED | CANCELLED | EXPIRED
    expires_at       = DateTime
```

#### `CapacityRequest`
```python
class CapacityRequest(Base, TimestampMixin, TenantMixin):
    __tablename__ = "capacity_requests"

    id            = UUID PK
    request_date  = Date
    order_count   = Integer    # how many additional orders need coverage
    zone          = String(100)
    priority      = String(20) # HIGH | NORMAL — influences match priority
    status        = String(20) # OPEN | MATCHED | CANCELLED | EXPIRED
    expires_at    = DateTime
```

#### `CapacityMatch`
```python
class CapacityMatch(Base, TimestampMixin):
    __tablename__ = "capacity_matches"
    # No TenantMixin — cross-tenant record

    id             = UUID PK
    offer_id       = UUID FK → capacity_offers
    request_id     = UUID FK → capacity_requests
    offering_tenant_id  = UUID FK → tenants
    requesting_tenant_id = UUID FK → tenants
    matched_orders = Integer  # how many orders covered
    status         = String(20)  # PENDING_ACCEPTANCE | ACCEPTED | REJECTED | COMPLETED
    settled_at     = DateTime (nullable)
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/models/marketplace.py` | **New** | `CapacityOffer`, `CapacityRequest`, `CapacityMatch` |
| `app/models/__init__.py` | Update | Register marketplace models |
| `alembic/versions/` | **New** | Migration for marketplace tables |
| `app/services/marketplace_service.py` | **New** | Offer/request CRUD + match engine |
| `app/workers/tasks.py` | Update | Add `marketplace_match_task` Celery periodic task |
| `app/api/v1/marketplace.py` | **New** | Offers, requests, matches CRUD + accept/reject |
| `app/api/router.py` | Update | Register marketplace router |
| `app/schemas/marketplace.py` | **New** | `CapacityOfferIn/Out`, `CapacityRequestIn/Out`, `CapacityMatchOut` |
| `src/api/marketplace.ts` | **New** | `fetchOffers()`, `createOffer()`, `fetchMatches()`, `respondToMatch()` |
| `src/pages/Marketplace.tsx` | **New** | Offer board + My Requests + Matched deals table |
| `src/routes/AppRoutes.tsx` | Update | Add `/marketplace` route |
| `src/components/layout/AppLayout.tsx` | Update | Add "Marketplace" nav item |

### API Endpoints

#### `POST /api/v1/marketplace/offers`
```json
{ "offer_date": "2026-04-15", "driver_count": 3, "zone": "Koramangala", "vehicle_type": "VAN", "rate_per_stop": 45.0 }
```

#### `POST /api/v1/marketplace/requests`
```json
{ "request_date": "2026-04-15", "order_count": 28, "zone": "Koramangala", "priority": "HIGH" }
```

#### `GET /api/v1/marketplace/matches?status=PENDING_ACCEPTANCE`
Returns matches where current tenant is `requesting_tenant_id`.

#### `PATCH /api/v1/marketplace/matches/{id}`
```json
{ "status": "ACCEPTED" }
```

### Match Engine Logic
```python
def run_match_engine(db: Session):
    """Run by Celery every 5 min. Greedy zone-match."""
    open_requests = db.query(CapacityRequest).filter_by(status="OPEN").order_by(priority_desc, created_at).all()
    for req in open_requests:
        # Find OPEN offer in same zone with enough drivers
        offer = db.query(CapacityOffer).filter(
            zone == req.zone,
            status == "OPEN",
            offer_date == req.request_date,
            driver_count >= ceil(req.order_count / 12),
        ).first()
        if offer:
            create_match(offer, req)
            offer.status = "MATCHED"
            req.status = "MATCHED"
```

### Verification
- Tenant A creates offer; Tenant B creates matching request → match created within 5 min
- Tenant B accepts match → status ACCEPTED
- Expired offers/requests auto-archived (expires_at < now)
- Marketplace page shows offer board and incoming matches

---

---

## Epic P4-E4: Governance, Compliance & Audit

### Goal
Enterprise-grade security and compliance features required for large contracts. Immutable audit log of all AI decisions and dispatcher actions. RBAC with resource-scoped permissions. GDPR-compliant data export and retention policies.

### Key Design Decisions
- **AuditLog is append-only** — no UPDATE or DELETE on `audit_log_entries`. Enforced at service layer + PostgreSQL row-level security (RLS).
- **RBAC** replaces the current binary role check. Permissions are stored as a JSON set per role. Existing `require_dispatcher` / `require_driver` deps become aliases for the most common permission sets.
- **SSO** (SAML/OAuth) is a config-layer addition — the auth flow accepts an external JWT/assertion and creates/maps a local `User` record. Full SAML implementation is via `python3-saml` library.
- **Data export** generates a ZIP containing JSON dumps of all tenant data. Runs as a Celery task (large tenants).
- **Retention policy** is a daily Celery job that soft-deletes records older than `retention_days` (configurable per tenant via `TenantConfig`).

### New Models

#### `AuditLogEntry`
```python
# app/models/audit_log.py
class AuditLogEntry(Base, TenantMixin):
    __tablename__ = "audit_log_entries"
    # No TimestampMixin — created_at is set once, never updated

    id            = UUID PK default gen_random_uuid()
    created_at    = DateTime server_default=func.now()   # immutable
    actor_email   = String(200)   # who performed the action
    actor_role    = String(50)    # their role at time of action
    action        = String(100)   # "plan.generate", "suggestion.accept", "order.create", etc.
    resource_type = String(100)   # "route_plan", "agent_suggestion", "order"
    resource_id   = UUID (nullable)
    before_state  = JSON (nullable)  # snapshot before change
    after_state   = JSON (nullable)  # snapshot after change
    ip_address    = String(50) (nullable)
    user_agent    = String(200) (nullable)
    ai_context    = JSON (nullable)  # for AI decisions: planner type, agent logs summary
```

#### `RbacRole`
```python
# app/models/rbac.py
class RbacRole(Base, TimestampMixin, TenantMixin):
    __tablename__ = "rbac_roles"

    id          = UUID PK
    name        = String(100)           # "dispatcher", "driver", "analyst", "admin"
    permissions = ARRAY(String)         # ["plan:generate", "order:read", "driver:manage", ...]
    is_system   = Boolean default False # system roles cannot be deleted
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/models/audit_log.py` | **New** | `AuditLogEntry` model |
| `app/models/rbac.py` | **New** | `RbacRole` model |
| `app/models/__init__.py` | Update | Register audit + rbac models |
| `alembic/versions/` | **New** | Migration for audit + rbac tables |
| `app/services/audit_service.py` | **New** | `log_action(actor, action, resource_type, resource_id, before, after, ai_context)` |
| `app/services/rbac_service.py` | **New** | `check_permission(user, permission)`, `assign_role(user_id, role_name)` |
| `app/core/security.py` | Update | Inject `audit_service.log_action` on destructive ops |
| `app/api/deps.py` | Update | `require_permission(permission: str)` dep |
| `app/api/v1/audit.py` | **New** | `GET /audit/log?action=&since=&resource_type=` |
| `app/api/v1/governance.py` | **New** | Data export trigger, retention config, RBAC role management |
| `app/api/router.py` | Update | Register audit + governance routers |
| `app/schemas/audit.py` | **New** | `AuditLogEntryOut`, `DataExportRequest`, `RetentionConfigOut` |
| `app/workers/tasks.py` | Update | Add `data_export_task`, `retention_sweep_task` (daily) |
| `src/api/audit.ts` | **New** | `fetchAuditLog(filters)`, `requestDataExport()` |
| `src/pages/AuditLog.tsx` | **New** | Filterable audit log table with AI context expandable |
| `src/routes/AppRoutes.tsx` | Update | Add `/audit` route (admin-only) |
| `src/components/layout/AppLayout.tsx` | Update | Add "Audit" nav item (admin role) |

### API Endpoints

#### `GET /api/v1/audit/log`
Query params: `action`, `actor_email`, `resource_type`, `since`, `until`, `page`, `limit`
```json
{
  "total": 1240,
  "items": [
    {
      "id": "...",
      "created_at": "2026-04-10T14:32:11Z",
      "actor_email": "dispatcher@acmecorp.com",
      "action": "suggestion.accept",
      "resource_type": "agent_suggestion",
      "resource_id": "...",
      "ai_context": { "suggestion_type": "REPLAN_DRIVER", "planner": "multi_agent" }
    }
  ]
}
```

#### `POST /api/v1/governance/data-export`
Triggers async export. Returns a `task_id`. Poll `GET /governance/data-export/{task_id}` for download URL.

#### `PATCH /api/v1/governance/retention`
```json
{ "retention_days": 365 }
```
Stored as `TenantConfig` key `retention_days`.

#### `GET|POST|DELETE /api/v1/governance/roles`
RBAC role management (platform-admin + tenant-admin only).

### Audit Injection Pattern
```python
# Every service method that mutates data calls audit_service:
async def accept_suggestion(suggestion_id, current_user, db):
    before = suggestion.dict()
    suggestion.status = "ACCEPTED"
    after = suggestion.dict()
    audit_service.log_action(
        actor=current_user,
        action="suggestion.accept",
        resource_type="agent_suggestion",
        resource_id=suggestion_id,
        before=before,
        after=after,
        ai_context={"suggestion_type": suggestion.suggestion_type},
    )
```

### Verification
- Dispatcher accepts suggestion → AuditLogEntry created with before/after
- GET /audit/log returns entries with correct actor and ai_context
- Data export task returns downloadable ZIP
- Retention sweep soft-deletes records older than configured days

---

---

## Epic P4-E5: Multi-Day Strategic Planning & Scenario Simulator

### Goal
Dispatchers and operations managers can plan across multiple days (rolling horizon) and run "what if" simulations before committing to strategic decisions. This is the feature that differentiates FleetOpsX from point solutions at enterprise scale.

### Key Design Decisions
- **Multi-day planner** extends `ORToolsPlanner.plan_day()` with a new `plan_horizon(dates: list[date])` method. Each day is solved sequentially using OR-Tools; driver shift carry-over and vehicle maintenance gaps are injected as constraints.
- **Scenario runs are async** — large simulations (7-day horizon, 5 scenarios) can take 10–60 seconds. Celery task + Redis pub/sub for progress streaming.
- **Scenario parameters** are stored as JSON in `ScenarioRun.parameters` — flexible, no schema migration per scenario type.
- `ScenarioResult` stores per-day aggregated KPIs — not full route data (too large). Detailed routes are available on demand via `GET /scenarios/{id}/day/{date}`.
- **Scenario types** in scope for Phase 4: `new_depot`, `ev_fleet_mix`, `driver_count_change`, `demand_surge`. Others are Phase 5.

### New Models

#### `ScenarioRun`
```python
# app/models/scenario.py
class ScenarioRun(Base, TimestampMixin, TenantMixin):
    __tablename__ = "scenario_runs"

    id              = UUID PK
    name            = String(200)       # user-given name
    scenario_type   = String(50)        # "new_depot" | "ev_fleet_mix" | "driver_count_change" | "demand_surge"
    parameters      = JSON              # scenario-specific params (see below)
    horizon_start   = Date
    horizon_days    = Integer           # 1–14
    status          = String(20)        # QUEUED | RUNNING | COMPLETED | FAILED
    baseline_kpis   = JSON (nullable)   # baseline run KPIs for comparison
    created_by      = String(100)       # actor email
    completed_at    = DateTime (nullable)
```

#### `ScenarioResult`
```python
class ScenarioResult(Base, TimestampMixin, TenantMixin):
    __tablename__ = "scenario_results"

    id              = UUID PK
    scenario_run_id = UUID FK → scenario_runs
    plan_date       = Date
    total_routes    = Integer
    assigned_orders = Integer
    on_time_rate    = Float
    avg_delay_min   = Float
    total_distance_km = Float
    fleet_utilization = Float   # assigned_driver_hours / available_driver_hours
    kpi_delta       = JSON      # diff vs baseline: { "on_time_rate": +0.05, ... }
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/models/scenario.py` | **New** | `ScenarioRun` + `ScenarioResult` |
| `app/models/__init__.py` | Update | Register scenario models |
| `alembic/versions/` | **New** | Migration for scenario tables |
| `app/planners/ortools_planner.py` | Update | Add `plan_horizon(dates, parameters)` method |
| `app/services/scenario_service.py` | **New** | `create_run()`, `run_baseline()`, `run_scenario()`, `compare()` |
| `app/workers/tasks.py` | Update | Add `scenario_run_task` (async, progress via Redis pub/sub) |
| `app/api/v1/scenarios.py` | **New** | Scenario CRUD + status + results endpoints |
| `app/api/v1/planning.py` | Update | Add `POST /plan/multi-day` endpoint |
| `app/api/router.py` | Update | Register scenarios router |
| `app/schemas/scenario.py` | **New** | `ScenarioRunIn/Out`, `ScenarioResultOut`, `MultiDayPlanRequest/Result` |
| `src/api/scenarios.ts` | **New** | `createScenario()`, `fetchScenarios()`, `fetchScenarioResults()`, `streamProgress()` |
| `src/pages/Scenarios.tsx` | **New** | Scenario wizard (type → params → horizon → run) + results comparison charts |
| `src/routes/AppRoutes.tsx` | Update | Add `/scenarios` route |
| `src/components/layout/AppLayout.tsx` | Update | Add "Scenarios" nav item |

### Scenario Parameter Schemas

```json
// new_depot
{ "lat": 12.9716, "lng": 77.5946, "depot_name": "Whitefield Hub", "capacity": 50 }

// ev_fleet_mix
{ "ev_percentage": 30, "ev_range_km": 200 }

// driver_count_change
{ "delta": -5 }     // negative = remove drivers; positive = add

// demand_surge
{ "zone": "Koramangala", "surge_factor": 1.4 }   // 40% more orders in that zone
```

### Multi-Day Plan Endpoint

#### `POST /api/v1/plan/multi-day`
```json
// Request
{
  "start_date": "2026-04-14",
  "horizon_days": 5,
  "parameters": {}     // optional scenario overrides
}

// Response
{
  "days": [
    { "plan_date": "2026-04-14", "assigned_orders": 42, "total_routes": 5, "plan_id": "..." },
    { "plan_date": "2026-04-15", "assigned_orders": 38, "total_routes": 4, "plan_id": "..." }
  ],
  "summary": {
    "total_orders": 200,
    "total_assigned": 192,
    "avg_on_time_rate": 0.87
  }
}
```

### Scenario API Endpoints

#### `POST /api/v1/scenarios`
```json
{
  "name": "Add Whitefield Depot",
  "scenario_type": "new_depot",
  "parameters": { "lat": 12.97, "lng": 77.75, "depot_name": "Whitefield", "capacity": 40 },
  "horizon_start": "2026-04-14",
  "horizon_days": 7
}
```
Returns `ScenarioRunOut` with `status: "QUEUED"`.

#### `GET /api/v1/scenarios/{id}/status`
```json
{ "status": "RUNNING", "progress": 3, "total": 7, "current_date": "2026-04-16" }
```

#### `GET /api/v1/scenarios/{id}/results`
```json
[
  {
    "plan_date": "2026-04-14",
    "on_time_rate": 0.91,
    "kpi_delta": { "on_time_rate": +0.06, "avg_delay_min": -4.2, "fleet_utilization": +0.08 }
  }
]
```

### Scenario Simulator UI

```
┌─ Scenario Simulator ──────────────────────────────────────────────────────┐
│                                                                             │
│  Step 1: Scenario Type                                                      │
│  ○ New Depot  ○ EV Fleet Mix  ○ Driver Count Change  ○ Demand Surge       │
│                                                                             │
│  Step 2: Parameters                                                         │
│  [Depot Name: Whitefield Hub]  [Lat: 12.97]  [Lng: 77.75]  [Cap: 40]    │
│                                                                             │
│  Step 3: Planning Horizon                                                   │
│  Start: [2026-04-14]   Days: [7]                                           │
│                                                                             │
│  [ Run Scenario ]                                                           │
│                                                                             │
│ ─────────────────────────────────────────────────────────────────────────  │
│  Results: "Add Whitefield Depot" vs Baseline                               │
│                                                                             │
│  On-Time Rate:   Baseline 81%  →  Scenario 91%  (+10%)                    │
│  Avg Delay:      Baseline 18m  →  Scenario 12m  (-6 min)                  │
│  Fleet Util.:    Baseline 72%  →  Scenario 80%  (+8%)                     │
│                                                                             │
│  [recharts LineChart — 7-day comparison — baseline vs scenario]            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Multi-Day Planner Extension
```python
# app/planners/ortools_planner.py — new method
def plan_horizon(
    self,
    db: Session,
    tenant_id: str,
    dates: list[date],
    parameters: dict = {},
) -> list[PlanResult]:
    """
    Solve for each date sequentially.
    Driver shift carry-over: if a driver was assigned >8h on day N,
    mark them unavailable for the first 4h of day N+1.
    Scenario parameters: inject virtual depot / fleet constraints before each solve.
    """
    results = []
    carry_over = {}    # driver_id → unavailable_until_hour
    for d in dates:
        result = self._plan_single_day(db, tenant_id, d, carry_over, parameters)
        carry_over = self._compute_carry_over(result)
        results.append(result)
    return results
```

### Verification
- `POST /plan/multi-day` with 3-day horizon → 3 `PlanResult` objects, each with correct plan_date
- Create scenario run → status QUEUED → RUNNING → COMPLETED
- `GET /scenarios/{id}/results` returns per-day KPIs with `kpi_delta` vs baseline
- Scenario page renders comparison chart
- Driver shift carry-over: driver with 12 assigned stops on day 1 has reduced availability on day 2

---

---

## New DB Tables Summary

| Table | Epic | Purpose |
|-------|------|---------|
| `tenant_db_routes` | P4-E1 | Maps enterprise tenants to dedicated DB connections |
| `webhook_registrations` | P4-E2 | Partner webhook callback URLs and event subscriptions |
| `integration_logs` | P4-E2 | Partner order ingest idempotency + error log |
| `capacity_offers` | P4-E3 | Tenant-listed available driver capacity |
| `capacity_requests` | P4-E3 | Tenant requests for additional fleet coverage |
| `capacity_matches` | P4-E3 | Cross-tenant capacity match records (no tenant_id) |
| `audit_log_entries` | P4-E4 | Immutable action audit trail (AI + human decisions) |
| `rbac_roles` | P4-E4 | Fine-grained permission sets per role |
| `scenario_runs` | P4-E5 | Strategic planning scenario metadata + status |
| `scenario_results` | P4-E5 | Per-day KPI results for each scenario run |

---

## New Dependencies

| Package | Where | Purpose |
|---------|-------|---------|
| `celery>=5.3` | `requirements.txt` | Distributed task queue (webhooks, marketplace match, scenarios, exports) |
| `flower>=2.0` | `requirements.txt` | Celery monitoring UI (dev/ops) |
| `python3-saml>=1.16` | `requirements.txt` | SAML 2.0 SSO support (P4-E4) |

---

## New API Endpoints Summary

| Method | Path | Epic | Auth | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/admin/tenant-db-routes` | P4-E1 | platform-admin | Register dedicated DB for a tenant |
| POST | `/api/v1/integrations/ingest` | P4-E2 | dispatcher | Ingest partner orders (idempotent) |
| GET | `/api/v1/integrations/tracking-feed` | P4-E2 | dispatcher | Real-time order status feed for partners |
| POST/GET/DELETE | `/api/v1/integrations/webhooks` | P4-E2 | dispatcher | Webhook registry CRUD |
| GET | `/api/v1/integrations/logs` | P4-E2 | dispatcher | Partner ingest audit log |
| POST | `/api/v1/marketplace/offers` | P4-E3 | dispatcher | List available capacity |
| POST | `/api/v1/marketplace/requests` | P4-E3 | dispatcher | Request additional capacity |
| GET | `/api/v1/marketplace/matches` | P4-E3 | dispatcher | View matched capacity deals |
| PATCH | `/api/v1/marketplace/matches/{id}` | P4-E3 | dispatcher | Accept or reject a match |
| GET | `/api/v1/audit/log` | P4-E4 | admin | Filtered audit log |
| POST | `/api/v1/governance/data-export` | P4-E4 | admin | Trigger GDPR data export |
| PATCH | `/api/v1/governance/retention` | P4-E4 | admin | Set data retention policy |
| GET/POST/DELETE | `/api/v1/governance/roles` | P4-E4 | admin | RBAC role management |
| POST | `/api/v1/plan/multi-day` | P4-E5 | dispatcher | Rolling-horizon multi-day plan |
| POST | `/api/v1/scenarios` | P4-E5 | dispatcher | Create and queue a scenario run |
| GET | `/api/v1/scenarios/{id}/status` | P4-E5 | dispatcher | Poll scenario progress |
| GET | `/api/v1/scenarios/{id}/results` | P4-E5 | dispatcher | Per-day KPI results + delta vs baseline |

---

## New Frontend Pages & Components

| File | Epic | Description |
|------|------|-------------|
| `src/pages/Integrations.tsx` | P4-E2 | Webhook registry + ingest log viewer |
| `src/pages/Marketplace.tsx` | P4-E3 | Capacity offer board + match management |
| `src/pages/AuditLog.tsx` | P4-E4 | Filterable audit log with AI context panel |
| `src/pages/Scenarios.tsx` | P4-E5 | Scenario wizard + results comparison charts |

---

## Implementation Order

```
P4-E1 first — DB routing is infrastructure; everything else builds on stable multi-tenant DB layer.
P4-E2 second — Webhooks introduce Celery; P4-E3 and P4-E5 reuse Celery workers.
P4-E3 and P4-E4 are independent — can run in parallel after P4-E1 + P4-E2.
P4-E5 last — requires P4-E1 stable DB + P3-E1 analytics data for baseline KPIs.
```

Within each epic, implement in this order:
1. Model + migration
2. Service + Celery task (if applicable)
3. API endpoint
4. Frontend page

---

## Key Design Invariants

- **`PlannerInterface` is unchanged.** `plan_horizon()` is an additional method on `ORToolsPlanner`, not a change to the interface. Existing `plan_day()` calls continue working.
- **AuditLog is append-only.** No UPDATE or DELETE on `audit_log_entries`. Service layer enforces this; Postgres RLS adds a second layer.
- **Marketplace is opt-in.** Tenants must explicitly create offers/requests. No automatic sharing of data or capacity.
- **Scenario runs are non-destructive.** They never write to operational tables (`route_plans`, `orders`, `route_stops`). They use in-memory plan results that are summarized into `ScenarioResult`.
- **DB routing is backwards-compatible.** Tenants without a `TenantDbRoute` record continue hitting the shared DB. No migration needed for existing tenants.
- **Celery uses the existing Redis.** No new broker — Redis is already in the stack from Phase 2 GPS tracking.

---

## Investor Pitch Milestones

| Milestone | Phase | What You Show |
|-----------|-------|---------------|
| Demo Ready | Phase 1 | Login → plan → driver delivers |
| Pilot Ready | Phase 2 | Optimized routes, SLA alerts, live tracking |
| AI Moat | Phase 3 | Self-learning, proactive suggestions |
| **Enterprise Scale** | **Phase 4** | **Multi-tenant SaaS, partner integrations, marketplace, strategic planning** |
