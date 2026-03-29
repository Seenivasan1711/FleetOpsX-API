# Phase 3 – Adaptive Multi-Agent System & Learning

> **Status:** Ready for implementation — detailed spec written after Phase 2 shipped.
> **Replaces:** planning section of `DEV_SPEC_P3_P4_multi_agent_enterprise_v1.md` (high-level only)

---

## Document Information

| Field | Value |
|-------|-------|
| **Phase** | Phase 3 |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | Phase 1 ✅ + Phase 2 ✅ fully complete |
| **Author** | Engineering Team |

---

## Phase Goal

FleetOpsX becomes **self-improving**. Historical delivery data is captured and analysed, multiple specialized AI agents collaborate to produce better plans, and the system proactively surfaces suggestions before problems occur — instead of waiting for a dispatcher to ask.

> Investor milestone: **"AI Moat"** — the system learns from its own history and acts before problems happen.

---

## Source Document Alignment Notes

> Records how this spec relates to original product/HLD docs and decisions made at spec-time.

| Note | Detail |
|------|--------|
| **APScheduler instead of Celery (P3-E1)** | `task_wise_plan.md §5.1` and `architecture.md §2` mention "Celery or RQ" for async workers. Phase 3 uses **APScheduler** (runs inside the existing FastAPI process) for ETL and background monitoring jobs. Reason: Celery requires a separate worker process, broker config, and supervision — unnecessary complexity for jobs that run once/day or every 5 min. Celery remains the correct path for Phase 4 when job volume and reliability SLAs increase. |
| **No external ML model in Forecast Agent** | `scope.md §3.2.2` describes using "ML models to predict travel times". Phase 3 uses **statistical forecasting** (day-of-week averages + zone-level baselines from `DeliveryAnalytics`). A dedicated ML model (scikit-learn, or LLM with RAG over historical data) is Phase 4. Keeps Phase 3 deliverable without a separate ML pipeline. |
| **Multi-Agent extends P2 LangGraph planner** | Phase 2 delivers a single 3-node LangGraph pipeline (fetch → optimize → explain). Phase 3 adds a 4th node (Forecast Agent runs pre-plan) and adds a background Monitor Agent that runs independently via APScheduler. The `PLANNER_TYPE=multi_agent` flag routes to the new orchestrator; `langgraph` continues to work unchanged. |
| **Monitor Agent is proactive, not just reactive** | `scope.md §3.2.1` describes a Monitor Agent that "watches real-time operations; detects anomalies". This extends P2's reactive SLA endpoint (`GET /sla/at-risk`) into a proactive background job that fires every 5 minutes and writes `AgentSuggestion` rows without waiting for a dispatcher request. |
| **`AgentSuggestion` model is new** | `scope.md §3.2.3` references a "Suggested actions feed with one-click approval". No model or API exists yet. P3-E2 introduces `AgentSuggestion` table and P3-E3 wires the Accept/Dismiss UI. |
| **`DeliveryEvent` model already exists** | `app/models/route_plan.py` has `DeliveryEvent` with `event_type` values: ASSIGNED, STARTED, ARRIVED, DELIVERED, FAILED, DELAYED, CANCELLED. ETL in P3-E1 reads these to compute on-time rate and actual arrival times for analytics. No model change needed. |
| **recharts for analytics charts** | `task_wise_plan.md §5.2` mentions recharts. Confirmed as the chart library for Phase 3 Analytics page. |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 3 Architecture                             │
│                                                                         │
│  Dispatcher Dashboard                                                   │
│  ┌──────────┬──────────────┬─────────────────┬───────────────────────┐ │
│  │Analytics │ Suggested    │ Live Map        │ Planning + Agent Feed │ │
│  │  Charts  │ Actions Feed │ (from P2)       │ (extended from P2)    │ │
│  └────┬─────┴──────┬───────┴─────────────────┴───────────────────────┘ │
│       │            │ HTTP                                               │
│  ┌────▼────────────▼──────────────────────────────────────────────────┐ │
│  │                         FastAPI Backend                             │ │
│  │                                                                     │ │
│  │  /analytics/kpis          ◄─── AnalyticsService (P3-E1)            │ │
│  │  /analytics/driver-perf   ◄─── AnalyticsService (P3-E1)            │ │
│  │  /agent/suggestions       ◄─── AgentSuggestion table (P3-E2)       │ │
│  │  PATCH /agent/suggestions/{id}  (accept / dismiss) (P3-E3)         │ │
│  │                                                                     │ │
│  │  PLANNER_TYPE=multi_agent → MultiAgentPlanner (P3-E2)              │ │
│  │       │                                                             │ │
│  │  LangGraph Orchestrator ─── Forecast Agent (P3-E2)                 │ │
│  │       │                 └── Planner Agent  (P2 core)               │ │
│  │       │                 └── Explainer Agent (P2 core)              │ │
│  │                                                                     │ │
│  │  APScheduler (background, in-process)                               │ │
│  │    ├── ETL Job     @ 01:00 daily → DeliveryAnalytics (P3-E1)       │ │
│  │    └── Monitor Job @ every 5 min → AgentSuggestion (P3-E3)         │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  New DB Tables: delivery_analytics, driver_performance_scores,          │
│                 agent_suggestions                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Epic Summary

| Epic | Area | Description | Depends On |
|------|------|-------------|-----------|
| **P3-E1** | Backend + FE | Historical Analytics & Feature Store — ETL, KPIs, charts | P2 complete |
| **P3-E2** | Backend | Multi-Agent Orchestration — Forecast, Monitor, Planner, Explainer | P3-E1 |
| **P3-E3** | Backend + FE | Proactive Planning — background monitor, suggested actions, Accept/Dismiss | P3-E2 |

---

---

## Epic P3-E1: Historical Analytics & Feature Store

### Goal
Build the data layer that enables learning. ETL operational data into analytics tables every night. Expose KPI APIs. Show charts and driver leaderboard in the UI.

### Key Design Decisions
- Analytics tables are **denormalized fact tables** separate from operational tables — fast reads, no joins needed for charting.
- ETL reads from `delivery_events` (existing), `route_stops`, `routes`, `orders`, and `route_plans`.
- `on_time = actual_arrival_time <= order.time_window_end` (NULL time_window_end → always on-time for metrics).
- `delay_minutes = max(0, actual_arrival - time_window_end)` in minutes.
- ETL is **idempotent** — running it twice on the same date does not create duplicates (upsert on `order_id`).
- APScheduler runs the ETL job at 01:00 local time daily via a startup lifespan event.

### New Dependencies
```
apscheduler>=3.10
recharts      # (frontend, npm install)
```

### New Models

#### `DeliveryAnalytics`
```python
# app/models/analytics.py
class DeliveryAnalytics(Base, TimestampMixin, TenantMixin):
    __tablename__ = "delivery_analytics"
    # Unique: one row per order per completed delivery
    id             = UUID PK
    order_id       = UUID FK → orders (unique, for upsert)
    driver_id      = UUID FK → drivers
    route_plan_id  = UUID FK → route_plans (nullable)
    delivery_date  = Date           # plan_date
    day_of_week    = Integer        # 0=Mon … 6=Sun
    hour_of_day    = Integer        # hour delivery completed
    zone           = String(100)    # delivery_address zone prefix (first word or city)
    planned_eta    = Time (nullable)  # order.time_window_end
    actual_arrival = DateTime (nullable)  # from DeliveryEvent(DELIVERED)
    delay_minutes  = Integer        # max(0, actual - planned) in minutes, NULL if no window
    was_on_time    = Boolean        # True if delay_minutes == 0
    priority       = String(20)     # CRITICAL / HIGH / NORMAL / LOW
```

#### `DriverPerformanceScore`
```python
# app/models/analytics.py (same file)
class DriverPerformanceScore(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_performance_scores"
    # Unique: one row per driver per date (upsert)
    id               = UUID PK
    driver_id        = UUID FK → drivers
    score_date       = Date
    total_deliveries = Integer
    on_time_count    = Integer
    on_time_rate     = Float        # on_time_count / total_deliveries
    avg_delay_min    = Float        # average of delay_minutes where > 0
    total_delay_min  = Integer
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | Update | Add `apscheduler>=3.10` |
| `app/models/analytics.py` | **New** | `DeliveryAnalytics` + `DriverPerformanceScore` models |
| `app/models/__init__.py` | Update | Register both models |
| `alembic/versions/` | **New** | Migration for both analytics tables |
| `app/services/analytics_service.py` | **New** | ETL function + KPI aggregation queries |
| `app/workers/scheduler.py` | **New** | APScheduler setup + register ETL job |
| `app/main.py` | Update | Start scheduler in FastAPI lifespan |
| `app/api/v1/analytics.py` | **New** | `GET /analytics/kpis` + `GET /analytics/driver-performance` |
| `app/api/router.py` | Update | Register analytics router |
| `src/api/analytics.ts` | **New** | `fetchKpis(planDate)`, `fetchDriverPerformance(since)` |
| `src/pages/Analytics.tsx` | **New** | KPI cards + recharts bar/line + driver leaderboard |
| `src/routes/AppRoutes.tsx` | Update | Add `/analytics` protected dispatcher route |
| `src/components/layout/AppLayout.tsx` | Update | Add "Analytics" nav item |

### API Endpoints

#### `GET /api/v1/analytics/kpis?since=YYYY-MM-DD&until=YYYY-MM-DD`
```json
{
  "period": { "since": "2026-03-01", "until": "2026-03-29" },
  "total_deliveries": 850,
  "on_time_rate": 0.84,
  "avg_delay_minutes": 12.3,
  "deliveries_by_day": [
    { "date": "2026-03-01", "total": 30, "on_time": 26 }
  ],
  "deliveries_by_zone": [
    { "zone": "Koramangala", "total": 120, "on_time_rate": 0.91 }
  ]
}
```

#### `GET /api/v1/analytics/driver-performance?since=YYYY-MM-DD`
```json
[
  {
    "driver_id": "...",
    "driver_name": "Ravi Kumar",
    "total_deliveries": 142,
    "on_time_rate": 0.92,
    "avg_delay_minutes": 7.1
  }
]
```

### ETL Logic (pseudo-code)
```python
def run_etl(db: Session, tenant_id: str, date: date):
    # 1. Find all route_stops with status DELIVERED on this date
    # 2. For each stop: get order, driver, route_plan
    # 3. Find DeliveryEvent(DELIVERED) for this route_stop → actual_arrival
    # 4. Compute delay_minutes, was_on_time, zone (parse from delivery_address)
    # 5. Upsert DeliveryAnalytics row (on_conflict order_id → update)
    # 6. Aggregate per driver → upsert DriverPerformanceScore row
```

### Verification
- Run ETL manually via `POST /analytics/run-etl?plan_date=YYYY-MM-DD` (dispatcher-only)
- GET /analytics/kpis returns populated data
- Analytics page shows charts with real data

---

---

## Epic P3-E2: Multi-Agent Orchestration

### Goal
Extend the Phase 2 LangGraph 3-node pipeline into a proper 4-agent orchestrated system. Add a Forecast Agent (runs pre-plan using `DeliveryAnalytics`) and split the existing nodes into clearly scoped agent files. New `PLANNER_TYPE=multi_agent` flag activates the full pipeline.

### Agent Responsibilities

| Agent | When it runs | Input | Output |
|-------|-------------|-------|--------|
| **Forecast Agent** | Pre-plan, before OR-Tools | `DeliveryAnalytics` for same day-of-week | Demand forecast per zone, risk zones |
| **Planner Agent** | After forecast | Orders + drivers + forecast | RoutePlan (via OR-Tools) |
| **Explainer Agent** | After plan | Plan result + forecast context | Human-readable plan summary |
| **Monitor Agent** | Background (APScheduler every 5 min) | Active route stops + Redis GPS pings | `AgentSuggestion` rows |

> **Note:** The Monitor Agent does NOT run inside the `plan_day` LangGraph graph. It is a separate background job. This separation is intentional — mixing real-time monitoring into the planning graph would make both harder to test and reason about.

### LangGraph Orchestrator Pipeline (plan_day)
```
START
  └─► Forecast Agent
        └─► Planner Agent   (calls ORToolsPlanner internally)
              └─► Explainer Agent
                    └─► END
```

### New Model: `AgentSuggestion`
```python
# app/models/agent_suggestion.py
class AgentSuggestion(Base, TimestampMixin, TenantMixin):
    __tablename__ = "agent_suggestions"

    id           = UUID PK
    plan_date    = Date               # which day this applies to
    suggestion_type = String(50)
    # REPLAN_DRIVER | EARLY_SLA_WARNING | DEMAND_WARNING | RESCHEDULE_STOP
    status       = String(20)         # PENDING | ACCEPTED | DISMISSED
    priority     = String(20)         # HIGH | NORMAL
    title        = String(200)        # short human-readable title
    detail       = Text               # full explanation
    context      = JSON               # structured data (driver_id, stop_id, order_ids, etc.)
    expires_at   = DateTime           # suggestion is stale after this time
    acted_by     = String(100) (nullable)  # user who accepted/dismissed
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/models/agent_suggestion.py` | **New** | `AgentSuggestion` model |
| `app/models/__init__.py` | Update | Register `AgentSuggestion` |
| `alembic/versions/` | **New** | Migration for `agent_suggestions` |
| `app/planners/agents/__init__.py` | **New** | Empty init |
| `app/planners/agents/forecast_agent.py` | **New** | `_node_forecast()` — queries `DeliveryAnalytics` for day-of-week baseline |
| `app/planners/agents/monitor_agent.py` | **New** | `run_monitor_scan()` — standalone function called by APScheduler |
| `app/planners/orchestrator.py` | **New** | LangGraph `StateGraph` wiring all 4 nodes |
| `app/planners/multi_agent_planner.py` | **New** | `MultiAgentPlanner(PlannerInterface)` — `PLANNER_TYPE=multi_agent` |
| `app/services/planning_service.py` | Update | Add `multi_agent` case to `get_planner()` |
| `.env` | Update | Add `PLANNER_TYPE=multi_agent` option docs |
| `app/api/v1/agent_suggestions.py` | **New** | `GET /agent/suggestions`, `PATCH /agent/suggestions/{id}` |
| `app/api/router.py` | Update | Register agent_suggestions router |
| `app/schemas/agent_suggestion.py` | **New** | `AgentSuggestionOut`, `AgentSuggestionUpdate` schemas |

### Forecast Agent Logic
```python
def _node_forecast(state: AgentState) -> AgentState:
    """
    Query DeliveryAnalytics for the same day-of-week over the last 4 weeks.
    Compute:
      - expected_order_count per zone
      - high_risk_zones (zones with on_time_rate < 0.75)
      - recommended_driver_count (ceil(expected_orders / 12))
    Returns forecast dict added to state["forecast"].
    """
```

### Monitor Agent Logic
```python
def run_monitor_scan(db: Session, tenant_id: str, plan_date: date):
    """
    Called by APScheduler every 5 min during business hours (07:00–20:00).
    For each active PENDING/IN_TRANSIT stop with time_window_end:
      1. Get driver's last Redis ping
      2. Compute travel time (haversine at 30 km/h)
      3. If ETA > time_window_end - 30 min AND no PENDING suggestion exists → create AgentSuggestion
    """
```

### API Endpoints

#### `GET /api/v1/agent/suggestions?plan_date=YYYY-MM-DD&status=PENDING`
```json
[
  {
    "id": "...",
    "suggestion_type": "EARLY_SLA_WARNING",
    "status": "PENDING",
    "priority": "HIGH",
    "title": "Ravi Kumar may miss 3 deliveries by 12:00",
    "detail": "Driver is currently 42 min from next stop. Time window closes in 28 min.",
    "context": { "driver_id": "...", "stop_ids": ["..."] },
    "expires_at": "2026-03-29T11:30:00",
    "created_at": "2026-03-29T11:02:00"
  }
]
```

#### `PATCH /api/v1/agent/suggestions/{id}`
Request:
```json
{ "status": "ACCEPTED" }   // or "DISMISSED"
```
Response: Updated `AgentSuggestionOut`.

- Accepting a `REPLAN_DRIVER` suggestion triggers `POST /plan/replan` internally with the `driver_id` from `context`.
- Accepting an `EARLY_SLA_WARNING` suggestion marks the stop as DELAYED in `DeliveryEvent` and dispatches a notification (future: SMS/email — for now, log only).

### Verification
- `PLANNER_TYPE=multi_agent` → plan_day response includes `"planner": "multi_agent"`, `"forecast"` key in response
- Agent logs show 4 steps: `forecast`, `call_optimizer`, `explain` (+ Monitor logs are separate)
- GET /agent/suggestions returns PENDING suggestions created by Monitor Agent

---

---

## Epic P3-E3: Proactive Planning & Suggested Actions UI

### Goal
Surface the Monitor Agent's suggestions in the UI so dispatchers can act on them with one click. Add demand warning shown the evening before on the Dashboard.

### Key Features
- **Suggested Actions panel** on Dashboard — shows PENDING suggestions with Accept / Dismiss buttons, polls every 60s
- **Accept action** for `REPLAN_DRIVER` triggers replan silently in background, marks suggestion ACCEPTED
- **Dismiss action** marks suggestion DISMISSED, removes from panel
- **Demand Warning** — if Forecast Agent identified high-risk zones or low driver coverage for tomorrow, show a warning card on Dashboard at end of day
- **Planning page badge** — if there are PENDING suggestions for the plan date, show a red badge on the "Generate Plan" button

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/workers/scheduler.py` | Update | Register Monitor Agent scan job (every 5 min, 07:00–20:00) |
| `src/api/agentSuggestions.ts` | **New** | `fetchSuggestions(planDate, status)`, `respondToSuggestion(id, status)` |
| `src/components/shared/SuggestedActions.tsx` | **New** | Collapsible panel, suggestion cards, Accept/Dismiss buttons |
| `src/pages/Dashboard.tsx` | Update | Add `SuggestedActions` below SLA panel |
| `src/pages/Planning.tsx` | Update | Red badge on Generate Plan button when PENDING suggestions exist |
| `src/types/index.ts` | Update | Add `AgentSuggestion` type |

### `SuggestedActions` Component Behaviour
```
┌─ AI Suggestions (2 pending) ──────────────────────────────── ▼ ┐
│                                                                   │
│  🔴 HIGH  Ravi Kumar may miss 3 deliveries by 12:00               │
│          Driver 42 min away, window closes in 28 min.             │
│          [ Accept — Replan Driver ]   [ Dismiss ]                 │
│                                                                   │
│  🟡 NORM  High demand in Koramangala tomorrow (est. 35 orders)    │
│          Historical avg is 22. Consider scheduling 2 extra drivers│
│          [ Accept — Noted ]          [ Dismiss ]                  │
└───────────────────────────────────────────────────────────────────┘
```

### Accept Flow (REPLAN_DRIVER)
```
User clicks Accept
  → PATCH /agent/suggestions/{id} { status: "ACCEPTED" }
  → Backend: check suggestion_type == REPLAN_DRIVER
  → Backend: call ORToolsPlanner().plan_day(db, tenant_id, plan_date)
             scoped to driver_id from context
  → Backend: mark suggestion ACCEPTED + acted_by = current_user.email
  → Frontend: toast "Replan triggered for Ravi Kumar"
  → SuggestedActions removes card
```

### Scheduler Registration
```python
# app/workers/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

def init_scheduler(app):
    """Called from FastAPI lifespan startup."""
    scheduler.add_job(
        func=run_all_tenant_etl,
        trigger=CronTrigger(hour=1, minute=0),    # 01:00 daily
        id="daily_etl",
        replace_existing=True,
    )
    scheduler.add_job(
        func=run_all_tenant_monitor_scan,
        trigger=CronTrigger(hour="7-20", minute="*/5"),  # every 5 min, 07–20
        id="monitor_scan",
        replace_existing=True,
    )
    scheduler.start()
```

### Verification
- Monitor scan runs → PENDING suggestions created for at-risk stops
- Dashboard shows SuggestedActions panel with correct count
- Accept → replan triggered, suggestion marked ACCEPTED, removed from panel
- Dismiss → suggestion marked DISMISSED, removed from panel
- Suggestions expire after `expires_at` and are filtered out automatically

---

---

## New DB Tables Summary

| Table | Epic | Purpose |
|-------|------|---------|
| `delivery_analytics` | P3-E1 | Denormalized delivery facts for analytics |
| `driver_performance_scores` | P3-E1 | Daily per-driver KPI rollup |
| `agent_suggestions` | P3-E2 | Proactive AI suggestions pending dispatcher action |

---

## New Dependencies

| Package | Where | Purpose |
|---------|-------|---------|
| `apscheduler>=3.10` | `requirements.txt` | Background ETL + monitor scan jobs |
| `recharts` | `package.json` (npm) | Analytics charts in React |

---

## New API Endpoints Summary

| Method | Path | Epic | Auth | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/analytics/kpis` | P3-E1 | dispatcher | On-time rate, delay metrics, by-zone breakdown |
| GET | `/api/v1/analytics/driver-performance` | P3-E1 | dispatcher | Driver leaderboard with on-time rate |
| POST | `/api/v1/analytics/run-etl` | P3-E1 | dispatcher | Manually trigger ETL for a date (debug/backfill) |
| GET | `/api/v1/agent/suggestions` | P3-E2 | dispatcher | List suggestions (filter by status, plan_date) |
| PATCH | `/api/v1/agent/suggestions/{id}` | P3-E3 | dispatcher | Accept or dismiss a suggestion |

---

## New Frontend Pages & Components

| File | Epic | Description |
|------|------|-------------|
| `src/pages/Analytics.tsx` | P3-E1 | KPI cards, recharts bar/line, driver leaderboard |
| `src/components/shared/SuggestedActions.tsx` | P3-E3 | Collapsible suggestion panel with Accept/Dismiss |

---

## Implementation Order

```
P3-E1 first — without analytics data, Forecast Agent has nothing to query.
P3-E2 second — multi-agent needs analytics tables + AgentSuggestion model.
P3-E3 third — UI requires the backend suggestion APIs from P3-E2.
```

Within each epic, implement in this order:
1. Model + migration
2. Service / agent logic
3. API endpoint
4. Frontend

---

## Key Design Invariants

- **`PlannerInterface` is unchanged.** `MultiAgentPlanner.plan_day()` has the same signature as `ORToolsPlanner` and `LangGraphPlanner`. No API changes.
- **ETL is idempotent.** Upsert on `order_id` in `delivery_analytics`. Safe to re-run.
- **Suggestions expire.** Monitor Agent sets `expires_at = now + 60 min`. Dashboard filters out expired suggestions automatically.
- **Monitor Agent is stateless.** It queries DB + Redis on every scan. No in-memory state. Safe to restart.
- **Accept replan is scoped.** Accepting a `REPLAN_DRIVER` suggestion only replans that driver's stops, not the full fleet.
