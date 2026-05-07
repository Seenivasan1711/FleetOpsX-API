# Phase 3 & Phase 4 – High-Level Specification

> **Status:** Planning only. Detailed GENSPECs to be written after Phase 2 ships.
> These specs capture intent, architecture decisions, and key deliverables — enough to plan investor roadmap and team hiring.

---

## Document Information

| Field | Value |
|-------|-------|
| **Phases** | Phase 3 & Phase 4 |
| **Status** | ⬜ Planning Only |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |

---

# PHASE 3 – Adaptive Multi-Agent System & Learning

## Phase Goal

The system becomes **self-improving**. Multiple specialized AI agents collaborate, learn from historical data, and proactively prevent problems before they happen. This is where FleetOpsX goes from "good software" to "AI platform with a moat."

---

## Epic P3-E1: Historical Analytics & Feature Store

### Goal
Build the data layer that enables learning. Capture every plan outcome (on time, delayed, failed) and build the feature store that ML models will use.

### Key Deliverables
- Analytics schema (separate from operational OLTP) — materialized views or separate tables
- ETL jobs (Celery beat tasks) to move operational data → analytics
- Basic KPI metrics: on-time rate, utilization %, avg delay per zone, driver performance scores
- Simple dashboards in the UI (charts using recharts or similar)

### New Models
```python
class DeliveryAnalytics(Base):
    # Denormalized fact table for analytics
    order_id, driver_id, zone, planned_eta, actual_arrival
    delay_minutes, was_on_time, date, day_of_week, hour_of_day

class DriverPerformanceScore(Base):
    driver_id, date, on_time_rate, avg_delay, total_deliveries
```

### Files
- `app/models/analytics.py`
- `app/workers/etl_worker.py` — daily ETL job
- `app/services/analytics_service.py`
- `app/api/v1/analytics.py`
- `src/pages/Analytics.tsx` — charts + KPIs

---

## Epic P3-E2: Multi-Agent System

### Goal
Replace the single Planner agent with a **crew of collaborating agents**, each with a specific role.

### Agent Roles

| Agent | Responsibility | Input | Output |
|-------|----------------|-------|--------|
| **Planner Agent** | Creates the daily plan | Orders, drivers, constraints | RoutePlan |
| **Monitor Agent** | Watches live operations | Location pings, stop statuses | Risk alerts, replan triggers |
| **Forecast Agent** | Predicts demand and delays | Historical data, date, weather | Expected order count, delay risk by zone |
| **Explainer Agent** | Makes decisions transparent | Plan + decision logs | Human-readable explanation |

### Architecture
```
Orchestrator (LangGraph StateGraph)
├── START → Forecast Agent (pre-plan)
│     └── output: demand forecast, risk zones
├── → Planner Agent (uses forecast + OR-Tools)
│     └── output: RoutePlan draft
├── → Explainer Agent (generates plan summary)
│     └── output: natural language explanation
└── END → return plan + explanation to dispatcher
```

### Files
- `app/planners/agents/planner_agent.py`
- `app/planners/agents/monitor_agent.py`
- `app/planners/agents/forecast_agent.py`
- `app/planners/agents/explainer_agent.py`
- `app/planners/orchestrator.py` — LangGraph StateGraph
- `app/planners/multi_agent_planner.py` — implements PlannerInterface

---

## Epic P3-E3: Proactive Planning

### Goal
System acts before problems occur rather than reacting after.

### Key Features
- **Pre-day forecast:** Night before, Forecast Agent estimates next day's demand per zone → recommends how many drivers to schedule
- **Early SLA warning:** Monitor Agent detects likely SLA breach 30 min in advance → suggests driver reallocation
- **Suggested actions feed:** Dispatcher sees a feed of AI-generated suggestions with one-click approval

### New UI Component
`src/components/SuggestedActions.tsx` — card showing AI recommendations with Accept/Dismiss buttons

---

## Phase 3 File Summary

| File | Epic | Status |
|------|------|--------|
| `app/models/analytics.py` | P3-E1 | ⬜ |
| `app/workers/etl_worker.py` | P3-E1 | ⬜ |
| `app/planners/agents/*.py` | P3-E2 | ⬜ |
| `app/planners/orchestrator.py` | P3-E2 | ⬜ |
| `app/planners/multi_agent_planner.py` | P3-E2 | ⬜ |
| `src/pages/Analytics.tsx` | P3-E1 | ⬜ |
| `src/components/SuggestedActions.tsx` | P3-E3 | ⬜ |

---

---

# PHASE 4 – Fleet Intelligence Platform & Marketplace

## Phase Goal

FleetOpsX becomes an **enterprise-grade SaaS platform** that large logistics companies and third-party partners integrate with. Multi-region, multi-depot, marketplace for capacity sharing.

---

## Epic P4-E1: Multi-Region & Per-Tenant DB

### Goal
Support very large enterprise customers who need dedicated infrastructure.

### Key Features
- **Per-tenant DB routing** — `get_db_for_tenant(tenant_id)` returns different connection for big tenants
- **Region configuration** per tenant (depot clustering by city/region)
- **On-prem deployment mode** — same Docker image, single-tenant mode via `TENANT_MODE=single`

### Architecture Change
```python
# app/core/db.py — updated
def get_db_for_tenant(tenant_id: str) -> Session:
    if tenant_id in DEDICATED_TENANT_DB_MAP:
        return dedicated_sessions[tenant_id]()
    return SessionLocal()  # shared DB fallback
```

---

## Epic P4-E2: Partner APIs (ERP / WMS / TMS Integration)

### Goal
Enterprise customers push orders from their ERP/WMS directly into FleetOpsX. Real-time order syncing without manual CSV import.

### New Endpoints
```
POST /api/v1/integrations/ingest-orders    ← webhook for ERP pushes
GET  /api/v1/integrations/tracking-feed    ← real-time delivery status stream
POST /api/v1/integrations/webhooks         ← register webhook URLs
```

### Ingestion Adapters
- `app/integrations/adapters/sap_adapter.py`
- `app/integrations/adapters/shopify_adapter.py`
- `app/integrations/adapters/generic_csv_adapter.py`

All adapters normalize to the canonical `Order` model.

---

## Epic P4-E3: Capacity Marketplace

### Goal
Fleets can share excess capacity with each other — if Tenant A has too many orders and Tenant B has idle drivers, they can exchange capacity via the marketplace.

### Key Concepts
- **Capacity offer** — Tenant A lists N available driver-hours
- **Capacity request** — Tenant B requests coverage for M orders
- **Match engine** — platform matches offers to requests
- **Settlement** — revenue split tracked and reported

### New Models
```python
class CapacityOffer(Base, TenantMixin)
class CapacityRequest(Base, TenantMixin)
class CapacityMatch(Base)  # no tenant_id — cross-tenant record
```

---

## Epic P4-E4: Governance, Compliance & Audit

### Goal
Enterprise-grade security and compliance features needed for large contracts.

### Key Features
- **RBAC/ABAC** — fine-grained permissions per user (e.g. dispatcher can plan but not manage drivers)
- **Immutable audit log** — every action recorded with user, timestamp, before/after state
- **Data export** — GDPR-compliant data export per tenant
- **Data retention** — configurable retention policies per tenant
- **SSO** — SAML/OAuth for enterprise identity providers

---

## Phase 4 File Summary

| File | Epic | Status |
|------|------|--------|
| `app/core/db.py` (routing update) | P4-E1 | ⬜ |
| `app/integrations/adapters/*.py` | P4-E2 | ⬜ |
| `app/api/v1/integrations.py` | P4-E2 | ⬜ |
| `app/models/marketplace.py` | P4-E3 | ⬜ |
| `app/api/v1/marketplace.py` | P4-E3 | ⬜ |
| `app/models/audit_log.py` | P4-E4 | ⬜ |
| `app/services/audit_service.py` | P4-E4 | ⬜ |

---

## Investor Pitch Milestone Map

| Milestone | Phase | What You Show |
|-----------|-------|---------------|
| **Demo Ready** | End of Phase 1 | Login → generate plan → driver sees stops → marks delivered |
| **Pilot Ready** | End of Phase 2 | Real optimized routes, SLA alerts, live tracking |
| **AI Moat** | End of Phase 3 | System learns from history, proactively prevents delays |
| **Enterprise Scale** | End of Phase 4 | Multi-tenant SaaS, partner integrations, marketplace |

---

**Document Status:** Planning Only  
**Last Updated:** 2026-03-29  
**When to Detail:** After Phase 2 ships, write full GENSPECs for each P3 and P4 epic
