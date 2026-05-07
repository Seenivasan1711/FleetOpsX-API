# Phase 2 – Autonomous Dispatch & Route Optimization

> **Status:** Spec ready. Do NOT implement until Phase 1 is fully working and demo-ed.

---

## Document Information

| Field | Value |
|-------|-------|
| **Phase** | Phase 2 |
| **Status** | ⬜ Spec Only — Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | Phase 1 fully complete + real operational data collected |

---

## Phase Goal

Move from **human-confirmed suggestions** to **fully autonomous dispatch** with real route optimization. The planner generates optimal multi-stop routes (not just single assignments), handles in-day changes, and flags SLA risks automatically.

---

## Epic P2-E1: OR-Tools VRPTW Route Optimization

### Goal
Replace the haversine greedy planner with a real Vehicle Routing Problem solver. Given N orders and M drivers, find the globally optimal assignment and stop sequence.

### Key Changes
- Add `ortools` to `requirements.txt`
- Create `app/planners/ortools_planner.py` implementing `PlannerInterface`
- Accepts capacity constraints (weight, volume) and time windows per stop
- Returns optimized route per driver with ordered stops
- Enable via feature flag: `PLANNER_TYPE=ortools` in `.env`

### Files
| File | Action |
|------|--------|
| `requirements.txt` | Add `ortools` |
| `app/planners/ortools_planner.py` | New — VRPTW solver |
| `app/services/planning_service.py` | Read `PLANNER_TYPE` from config, instantiate correct planner |
| `app/core/config.py` | Add `PLANNER_TYPE: str = "rule_based"` |

### VRPTW Solver Pattern
```python
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

class ORToolsPlanner(PlannerInterface):
    def plan_day(self, db, tenant_id, plan_date):
        # 1. Fetch orders + drivers (same as RuleBasedPlanner)
        # 2. Build distance matrix (N×N Haversine or Maps API)
        # 3. Build OR-Tools RoutingModel
        # 4. Add time window constraints
        # 5. Add capacity constraints
        # 6. Solve with TIME_LIMIT_MS=10000
        # 7. Parse solution → create RoutePlan/Route/RouteStop records
        # 8. Return same dict format as RuleBasedPlanner
```

### Acceptance Criteria
- [ ] Solver returns valid routes within 10 second time limit
- [ ] Routes respect time windows
- [ ] Routes respect vehicle capacity
- [ ] Same `/plan/day` endpoint works with no API changes

---

## Epic P2-E2: LangGraph Planner Agent

### Goal
Wrap the planning workflow in a LangGraph agent so it can use tools, explain decisions, and handle multi-step reasoning. The agent calls the OR-Tools solver as a tool rather than embedding the logic directly.

### New Dependencies
```
langchain
langgraph
langchain-openai
```

### Agent Architecture
```
LangGraph Planner Agent
├── Tool: fetch_unassigned_orders(tenant_id, date)
├── Tool: fetch_available_drivers(tenant_id, date)
├── Tool: call_optimizer(orders, drivers, constraints)
├── Tool: write_assignments(plan_result)
└── Tool: explain_plan(plan_result) → human-readable summary
```

### Files
| File | Action |
|------|--------|
| `requirements.txt` | Add langchain, langgraph, langchain-openai |
| `app/planners/langgraph_agent.py` | New — LangGraph-based planner |
| `app/planners/tools/` | New folder — each tool as a Python function |
| `app/core/config.py` | Add `OPENAI_API_KEY`, update `PLANNER_TYPE` to support `langgraph` |
| `.env` | Add `OPENAI_API_KEY=`, `PLANNER_TYPE=langgraph` |

### Feature Flag
`PLANNER_TYPE` in `.env`:
- `rule_based` → RuleBasedPlanner (Phase 1)
- `ortools` → ORToolsPlanner
- `langgraph` → LangGraphPlanner

### Acceptance Criteria
- [ ] Agent calls tools in correct order
- [ ] Agent produces same structured output as rule-based planner
- [ ] Agent generates a human-readable explanation of the plan
- [ ] Falls back to rule-based if `OPENAI_API_KEY` is not set
- [ ] No API endpoint changes

---

## Epic P2-E3: Real-Time Tracking & Re-planning

### Goal
Accept GPS pings from drivers. Track their current location. Detect delays. Trigger re-plan if needed.

### New Endpoint
```
POST /api/v1/tracking/ping
Body: { driver_id, latitude, longitude, timestamp }
```

### New Model: `app/models/tracking.py`
```python
class DriverLocationPing(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_location_pings"
    id = Column(UUID, PK)
    driver_id = Column(UUID, FK drivers.id)
    latitude = Column(Float)
    longitude = Column(Float)
    recorded_at = Column(DateTime)
```

### Re-planning Trigger
- Background task checks every 5 minutes: any stop where ETA is > time_window_end?
- If yes → flag as SLA_AT_RISK → call replan() on PlannerInterface
- Return updated route suggestions (human confirms)

### Files
| File | Action |
|------|--------|
| `app/models/tracking.py` | New |
| `app/api/v1/tracking.py` | New — POST /tracking/ping |
| `app/services/tracking_service.py` | New |
| `app/workers/replan_worker.py` | New — periodic Celery task |
| `requirements.txt` | Add celery |
| `docker-compose.yml` | Add celery worker service |

---

## Epic P2-E4: SLA Risk Alerts

### Goal
When an order is at risk of missing its time window, alert the dispatcher in the UI and optionally send a notification.

### Backend
- `app/services/sla_service.py` — compute risk score per stop
- New endpoint: `GET /api/v1/sla/at-risk?plan_date=` returns list of at-risk stops
- Risk calculated as: current_time + remaining_travel_time > time_window_end

### Frontend
- Dashboard shows "At-Risk Deliveries" panel with count badge
- Clicking shows list of at-risk stops with driver name and ETA

---

## Phase 2 File Summary

| File | Epic | Status |
|------|------|--------|
| `app/planners/ortools_planner.py` | P2-E1 | ⬜ |
| `app/planners/langgraph_agent.py` | P2-E2 | ⬜ |
| `app/planners/tools/*.py` | P2-E2 | ⬜ |
| `app/models/tracking.py` | P2-E3 | ⬜ |
| `app/api/v1/tracking.py` | P2-E3 | ⬜ |
| `app/workers/replan_worker.py` | P2-E3 | ⬜ |
| `app/services/sla_service.py` | P2-E4 | ⬜ |
| `app/api/v1/sla.py` | P2-E4 | ⬜ |

---

**Document Status:** Spec Only  
**Last Updated:** 2026-03-29  
**When to Start:** After Phase 1 demo is complete and signed off
