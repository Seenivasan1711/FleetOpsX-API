# Phase 2 – Autonomous Dispatch & Route Optimization

> **Status:** Active — Implementation in progress
> **Replaces:** `DEV_SPEC_P2_autonomous_dispatch_v1.md` (high-level only)

---

## Document Information

| Field | Value |
|-------|-------|
| **Phase** | Phase 2 |
| **Version** | 2.0 |
| **Date** | 2026-03-29 |
| **Depends On** | Phase 1 fully complete ✅ |
| **Author** | Engineering Team |

---

## Phase Goal

Evolve FleetOpsX from a rule-based assisted dispatch tool into an AI-powered autonomous dispatch platform. A tenant-configurable LLM agent (LangGraph) calls OR-Tools to produce optimal routes, explains its decisions, and tracks drivers in real time — all while letting each tenant bring their own LLM API key.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Phase 2 Architecture                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Dispatcher Dashboard                      │   │
│  │  Live Map (Leaflet)  │  Agent Feed  │  SLA Alerts  │  Plan   │   │
│  └────────────────────────────┬─────────────────────────────────┘   │
│                               │ HTTP poll / REST                     │
│  ┌────────────────────────────▼─────────────────────────────────┐   │
│  │                        FastAPI Backend                        │   │
│  │                                                               │   │
│  │   /plan/day ──► PlanningService ──► Planner (feature flag)   │   │
│  │                                         │                     │   │
│  │              ┌──────────────────────────┼──────────────────┐ │   │
│  │              │ rule_based  │  ortools   │   langgraph      │ │   │
│  │              └─────────────┴────────────┴──────────────────┘ │   │
│  │                                         │                     │   │
│  │   LangGraph Agent ◄────────────────────►│                     │   │
│  │       │                                 │                     │   │
│  │   LLMProviderFactory                    │                     │   │
│  │       │                                 │                     │   │
│  │   ┌───┴──────────────┐                  │                     │   │
│  │   │  Per-Tenant LLM  │                  │                     │   │
│  │   │  claude / openai │                  │                     │   │
│  │   │  gemini / other  │                  │                     │   │
│  │   └──────────────────┘                  │                     │   │
│  │                                         │                     │   │
│  │   /tracking/ping ──► Redis (latest pos) │                     │   │
│  │   /tracking/live ──► positions + routes │                     │   │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Driver App ──► POST /tracking/ping (every 30s)                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Epic Summary

| Epic | Area | Description | Depends On |
|------|------|-------------|-----------|
| **P2-E1** | Backend | OR-Tools VRPTW solver — replace greedy planner | P1 complete |
| **P2-E2** | Backend | Multi-LLM Provider — per-tenant Claude/OpenAI/Gemini | P2-E1 |
| **P2-E3** | Backend | LangGraph Dispatch Agent using multi-LLM provider | P2-E2 |
| **P2-E4** | Backend | Real-Time GPS Tracking — driver pings + Redis cache | P1 complete |
| **P2-E5** | Frontend | Live Map — Leaflet + OpenStreetMap + driver markers | P2-E4 |
| **P2-E6** | Frontend | Agent Activity Feed — what the agent decided and why | P2-E3 |
| **P2-E7** | Backend + FE | SLA Risk Alerts — at-risk stops + dispatcher alerts | P2-E4 |

---

---

## Epic P2-E1: OR-Tools VRPTW Route Optimization

### Goal
Replace the Phase 1 haversine greedy planner with Google OR-Tools to solve the Vehicle Routing Problem with Time Windows (VRPTW). Same `/plan/day` API endpoint, better results.

### Key Concepts
- **VRPTW**: Given N orders with time windows and M drivers with capacity constraints, find the globally optimal route for each driver.
- **Distance matrix**: Haversine for Phase 2 demo; plug in Google Maps Distance Matrix API later.
- **Time limit**: 10 seconds max solve time — always returns best-found solution.
- **Feature flag**: `PLANNER_TYPE=ortools` in `.env` — no code changes to switch.

### New Dependencies
```
ortools>=9.8
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | Update | Add `ortools>=9.8` |
| `app/core/config.py` | Update | Add `PLANNER_TYPE: str = "rule_based"` setting |
| `app/planners/ortools_planner.py` | **New** | Full VRPTW implementation |
| `app/services/planning_service.py` | Update | Read `PLANNER_TYPE`, instantiate correct planner |

### Implementation: `app/planners/ortools_planner.py`

```python
import math
from datetime import datetime, timedelta
from typing import Optional
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from sqlalchemy.orm import Session

from app.planners.interface import PlannerInterface
from app.models.order import Order
from app.models.driver import Driver
from app.models.route_plan import RoutePlan, Route, RouteStop
from app.core.config import settings

DEPOT_LAT = 12.9716   # fallback depot coords (Bangalore centre)
DEPOT_LNG = 77.5946
TIME_LIMIT_SECONDS = 10
SCALE = 100_000        # convert float coords to int for OR-Tools

class ORToolsPlanner(PlannerInterface):

    def _haversine_minutes(self, lat1, lng1, lat2, lng2) -> int:
        """Return travel time in minutes (assumes 30 km/h avg speed)."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
            math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        km = R * 2 * math.asin(math.sqrt(a))
        return max(1, int((km / 30) * 60))

    def _build_distance_matrix(self, locations: list[tuple]) -> list[list[int]]:
        """NxN matrix of travel-time in minutes (scaled to int)."""
        n = len(locations)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self._haversine_minutes(
                        locations[i][0], locations[i][1],
                        locations[j][0], locations[j][1]
                    )
        return matrix

    def _time_to_minutes(self, t: Optional[str]) -> int:
        """'HH:MM' string → minutes since midnight. None → 0 or 1440."""
        if not t:
            return 0
        h, m = map(int, t.split(':'))
        return h * 60 + m

    def plan_day(self, db: Session, tenant_id: str, plan_date: str) -> dict:
        from app.models.order import Order
        from app.models.driver import Driver, DriverShift
        from app.models.vehicle import Vehicle

        plan_dt = datetime.strptime(plan_date, "%Y-%m-%d").date()

        # Fetch unassigned orders
        orders = db.query(Order).filter(
            Order.tenant_id == tenant_id,
            Order.status == 'PENDING',
            Order.scheduled_date >= datetime.combine(plan_dt, datetime.min.time()),
            Order.scheduled_date < datetime.combine(plan_dt + timedelta(days=1), datetime.min.time()),
        ).all()

        if not orders:
            return {"plan_id": None, "assignments": [], "total_orders": 0,
                    "assigned_orders": 0, "total_routes": 0}

        # Fetch active drivers with vehicles
        drivers = db.query(Driver).filter(
            Driver.tenant_id == tenant_id,
            Driver.is_active == True,
        ).all()

        if not drivers:
            return {"plan_id": None, "assignments": [], "total_orders": len(orders),
                    "assigned_orders": 0, "total_routes": 0}

        # Build node list: index 0 = depot, then orders
        depot_lat = DEPOT_LAT
        depot_lng = DEPOT_LNG
        if drivers[0].home_depot_id:
            from app.models.depot import Depot
            depot = db.query(Depot).filter(Depot.id == drivers[0].home_depot_id).first()
            if depot and depot.latitude:
                depot_lat, depot_lng = depot.latitude, depot.longitude

        locations = [(depot_lat, depot_lng)]
        for o in orders:
            lat = o.delivery_latitude or depot_lat
            lng = o.delivery_longitude or depot_lng
            locations.append((lat, lng))

        distance_matrix = self._build_distance_matrix(locations)
        num_locations = len(locations)
        num_vehicles = len(drivers)
        depot_index = 0

        # OR-Tools setup
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, depot_index)
        routing = pywrapcp.RoutingModel(manager)

        # Distance callback
        def distance_callback(from_idx, to_idx):
            return distance_matrix[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

        transit_callback_idx = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_idx)

        # Time window dimension
        routing.AddDimension(
            transit_callback_idx,
            slack_max=60,          # allow 60 min wait at a stop
            capacity=8 * 60,       # 8-hour shift
            fix_start_cumul_to_zero=True,
            name='Time'
        )
        time_dimension = routing.GetDimensionOrDie('Time')

        # Apply time windows per order node
        for order_idx, order in enumerate(orders):
            node = order_idx + 1  # +1 because 0 is depot
            index = manager.NodeToIndex(node)
            tw_start = self._time_to_minutes(order.time_window_start) if order.time_window_start else 0
            tw_end = self._time_to_minutes(order.time_window_end) if order.time_window_end else 8 * 60
            time_dimension.CumulVar(index).SetRange(tw_start, tw_end)

        # Search parameters
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.seconds = TIME_LIMIT_SECONDS

        solution = routing.SolveWithParameters(search_params)

        if not solution:
            # Fallback: import and use rule-based
            from app.planners.rule_based import RuleBasedPlanner
            return RuleBasedPlanner().plan_day(db, tenant_id, plan_date)

        # Parse solution and write DB records
        plan = RoutePlan(
            tenant_id=tenant_id,
            plan_date=plan_dt,
            status='DRAFT',
            planner_version='ortools_v1',
        )
        db.add(plan)
        db.flush()

        assignments = []
        for vehicle_idx, driver in enumerate(drivers):
            index = routing.Start(vehicle_idx)
            stop_sequence = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != depot_index:
                    stop_sequence.append(orders[node - 1])
                index = solution.Value(routing.NextVar(index))

            if not stop_sequence:
                continue

            route = Route(
                tenant_id=tenant_id,
                route_plan_id=plan.id,
                driver_id=driver.id,
                status='ASSIGNED',
                total_stops=len(stop_sequence),
            )
            db.add(route)
            db.flush()

            route_stops = []
            for seq, order in enumerate(stop_sequence):
                stop = RouteStop(
                    tenant_id=tenant_id,
                    route_id=route.id,
                    order_id=order.id,
                    sequence=seq + 1,
                    status='PENDING',
                )
                db.add(stop)
                order.status = 'ASSIGNED'
                route_stops.append({
                    "order_id": str(order.id),
                    "sequence": seq + 1,
                    "address": order.delivery_address,
                })

            assignments.append({
                "driver_id": str(driver.id),
                "driver_name": driver.full_name,
                "route_id": str(route.id),
                "stops": route_stops,
            })

        db.commit()

        return {
            "plan_id": str(plan.id),
            "plan_date": plan_date,
            "status": "DRAFT",
            "total_orders": len(orders),
            "assigned_orders": sum(len(a["stops"]) for a in assignments),
            "total_routes": len(assignments),
            "assignments": assignments,
            "planner": "ortools",
        }
```

### Update: `app/core/config.py`
Add to `Settings` class:
```python
PLANNER_TYPE: str = "rule_based"   # options: rule_based | ortools | langgraph
```

### Update: `app/services/planning_service.py`
```python
from app.core.config import settings

def get_planner():
    if settings.PLANNER_TYPE == "ortools":
        from app.planners.ortools_planner import ORToolsPlanner
        return ORToolsPlanner()
    elif settings.PLANNER_TYPE == "langgraph":
        from app.planners.langgraph_agent import LangGraphPlanner
        return LangGraphPlanner()
    else:
        from app.planners.rule_based import RuleBasedPlanner
        return RuleBasedPlanner()
```

### Acceptance Criteria
- [ ] `PLANNER_TYPE=ortools` in `.env` → OR-Tools solver used
- [ ] `/plan/day` returns same response shape as Phase 1
- [ ] OR-Tools falls back to rule_based if solution not found
- [ ] Routes respect time windows where possible
- [ ] Solve completes within 10 seconds

---

---

## Epic P2-E2: Multi-LLM Provider System

### Goal
Let each tenant configure their own LLM provider (Claude / OpenAI / Gemini / extensible) and API key via tenant config. The LangGraph agent uses this abstraction. No hardcoded API keys anywhere.

### Design Principles
- **Per-tenant**: each tenant stores `llm_provider`, `llm_api_key`, `llm_model` in `TenantConfig`
- **Fallback chain**: tenant config → system env var → `rule_based` planner
- **Extensible**: adding a new provider = one new `elif` in the factory
- **LangChain standard**: all providers return a `BaseChatModel` — same interface for LangGraph

### Supported Providers (Phase 2)

| Provider | Package | Default Model | Free Tier |
|----------|---------|---------------|-----------|
| `gemini` | `langchain-google-genai` | `gemini-2.0-flash` | ✅ Yes |
| `openai` | `langchain-openai` | `gpt-4o-mini` | ❌ Paid |
| `anthropic` | `langchain-anthropic` | `claude-haiku-4-5-20251001` | ❌ Paid |

### New Dependencies
```
langchain>=0.3
langgraph>=0.2
langchain-openai>=0.2
langchain-anthropic>=0.3
langchain-google-genai>=2.0
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | Update | Add langchain stack |
| `app/models/tenant.py` | Update | Add LLM fields to TenantConfig |
| `app/schemas/tenant.py` | Update | Expose LLM config fields |
| `app/api/v1/tenants.py` | Update | PATCH endpoint to update LLM config |
| `app/core/llm_factory.py` | **New** | `LLMProviderFactory` — returns BaseChatModel |
| `alembic/versions/` | **New** | Migration: add llm fields to tenant_configs |

### DB Schema Addition: `tenant_configs` table

Add three columns:
```sql
ALTER TABLE tenant_configs ADD COLUMN llm_provider  VARCHAR(50)  DEFAULT 'gemini';
ALTER TABLE tenant_configs ADD COLUMN llm_api_key   TEXT         DEFAULT NULL;
ALTER TABLE tenant_configs ADD COLUMN llm_model     VARCHAR(100) DEFAULT NULL;
```

### Implementation: `app/core/llm_factory.py`

```python
"""
LLM Provider Factory — returns a LangChain BaseChatModel for any supported provider.

Supported providers: gemini, openai, anthropic
Extensible: add new elif block for additional providers.

Resolution order:
  1. tenant_config.llm_provider + tenant_config.llm_api_key  (per-tenant)
  2. System env var (GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY)
  3. Returns None → caller falls back to rule_based planner
"""
import os
from typing import Optional
from langchain_core.language_models import BaseChatModel


def get_llm_for_tenant(
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str] = None,
) -> Optional[BaseChatModel]:
    """
    Returns a configured BaseChatModel or None if not configured.

    Args:
        provider: 'gemini' | 'openai' | 'anthropic' | None
        api_key:  The tenant's API key (or None to fall back to env var)
        model:    Optional model override. Falls back to provider default.
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            return None
        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash",
            google_api_key=key,
            temperature=0,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=key,
            temperature=0,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        return ChatAnthropic(
            model=model or "claude-haiku-4-5-20251001",
            api_key=key,
            temperature=0,
        )

    # Future providers: add elif blocks here
    # elif provider == "mistral": ...
    # elif provider == "azure_openai": ...

    return None
```

### Update: `app/models/tenant.py`
Add to `TenantConfig` model:
```python
llm_provider = Column(String(50), default='gemini')   # gemini | openai | anthropic
llm_api_key  = Column(Text, nullable=True)             # encrypted at rest (Phase 3)
llm_model    = Column(String(100), nullable=True)      # optional model override
```

### New API endpoint: `PATCH /api/v1/tenants/config/llm`
Allows dispatcher/admin to save their LLM API key from the UI settings page.

```python
@router.patch("/config/llm", response_model=TenantConfigOut)
def update_llm_config(
    payload: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_dispatcher),
):
    config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == current_user.tenant_id
    ).first()
    if not config:
        raise HTTPException(404, "Tenant config not found")
    if payload.llm_provider is not None:
        config.llm_provider = payload.llm_provider
    if payload.llm_api_key is not None:
        config.llm_api_key = payload.llm_api_key
    if payload.llm_model is not None:
        config.llm_model = payload.llm_model
    db.commit()
    db.refresh(config)
    return config
```

### `.env` additions
```
# System-level LLM fallback (tenant config takes priority)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_free_gemini_key_here
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Acceptance Criteria
- [ ] `TenantConfig` has `llm_provider`, `llm_api_key`, `llm_model` columns
- [ ] `LLMProviderFactory.get_llm_for_tenant()` returns correct client per provider
- [ ] Returns `None` (not error) when no key configured — planner falls back gracefully
- [ ] `PATCH /tenants/config/llm` saves config per tenant
- [ ] Adding a new provider requires only one `elif` block in factory

---

---

## Epic P2-E3: LangGraph Dispatch Agent

### Goal
Wrap the planning workflow in a LangGraph agent. The agent uses tools to fetch data, call OR-Tools, write assignments, and produce a human-readable explanation — all in a structured, auditable way. Uses the multi-LLM provider from P2-E2.

### Agent Design

```
LangGraph State Machine
────────────────────────────────────────────────────────────────────
  START
    │
    ▼
  fetch_context        ← Tool: get orders, drivers, constraints
    │
    ▼
  analyze              ← LLM: understand the routing problem
    │
    ▼
  call_optimizer       ← Tool: call ORToolsPlanner.plan_day()
    │
    ▼
  validate             ← LLM: check for issues, SLA conflicts
    │
    ▼
  write_assignments    ← Tool: persist plan to DB (OR-Tools already did this)
    │
    ▼
  explain              ← LLM: generate human-readable summary
    │
    ▼
  END → returns PlanResult + explanation
────────────────────────────────────────────────────────────────────
```

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/planners/tools/__init__.py` | **New** | Package init |
| `app/planners/tools/fetch_context.py` | **New** | Fetch orders + drivers for plan date |
| `app/planners/tools/call_optimizer.py` | **New** | Wraps ORToolsPlanner |
| `app/planners/tools/explain_plan.py` | **New** | Formats plan for LLM explanation |
| `app/planners/langgraph_agent.py` | **New** | Full LangGraph agent |
| `app/models/agent_log.py` | **New** | Stores agent reasoning steps |
| `app/api/v1/agent_logs.py` | **New** | `GET /agent-logs?plan_id=` |
| `app/schemas/agent_log.py` | **New** | AgentLogOut schema |

### Implementation: `app/models/agent_log.py`

```python
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base
from app.models.mixins import TimestampMixin, TenantMixin

class AgentLog(Base, TimestampMixin, TenantMixin):
    __tablename__ = "agent_logs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id    = Column(UUID(as_uuid=True), ForeignKey("route_plans.id"), nullable=True)
    step       = Column(String(100))       # e.g. "fetch_context", "analyze", "explain"
    role       = Column(String(20))        # "agent" | "tool" | "llm"
    content    = Column(Text)              # the message / reasoning / tool result
    llm_provider = Column(String(50), nullable=True)  # which provider was used
```

### Implementation: `app/planners/langgraph_agent.py`

```python
"""
LangGraph Planner Agent — wraps OR-Tools with LLM reasoning and explanation.

Falls back to ORToolsPlanner (no LLM) if tenant has no LLM configured.
Falls back to RuleBasedPlanner if OR-Tools fails.
"""
from __future__ import annotations
import json
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.planners.interface import PlannerInterface
from app.core.llm_factory import get_llm_for_tenant
from app.models.agent_log import AgentLog


class AgentState(TypedDict):
    tenant_id: str
    plan_date: str
    db: object            # Session (not serialised — stays in memory)
    llm: object           # BaseChatModel
    context: dict         # fetched orders/drivers summary
    plan_result: dict     # output from ORToolsPlanner
    explanation: str      # LLM-generated summary
    logs: list            # list of AgentLog entries to persist


class LangGraphPlanner(PlannerInterface):

    def plan_day(self, db: Session, tenant_id: str, plan_date: str) -> dict:
        from app.models.tenant import TenantConfig
        config = db.query(TenantConfig).filter(
            TenantConfig.tenant_id == tenant_id
        ).first()

        llm = None
        if config:
            llm = get_llm_for_tenant(
                provider=config.llm_provider,
                api_key=config.llm_api_key,
                model=config.llm_model,
            )

        if llm is None:
            # No LLM configured — use OR-Tools directly (still better than rule_based)
            from app.planners.ortools_planner import ORToolsPlanner
            return ORToolsPlanner().plan_day(db, tenant_id, plan_date)

        graph = self._build_graph()
        result = graph.invoke({
            "tenant_id": tenant_id,
            "plan_date": plan_date,
            "db": db,
            "llm": llm,
            "context": {},
            "plan_result": {},
            "explanation": "",
            "logs": [],
        })

        # Persist agent logs
        for log_entry in result.get("logs", []):
            log = AgentLog(
                tenant_id=tenant_id,
                plan_id=result["plan_result"].get("plan_id"),
                step=log_entry["step"],
                role=log_entry["role"],
                content=log_entry["content"],
                llm_provider=config.llm_provider if config else None,
            )
            db.add(log)
        db.commit()

        plan = result["plan_result"]
        plan["explanation"] = result.get("explanation", "")
        plan["planner"] = "langgraph"
        return plan

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("fetch_context", _node_fetch_context)
        workflow.add_node("call_optimizer", _node_call_optimizer)
        workflow.add_node("explain", _node_explain)
        workflow.set_entry_point("fetch_context")
        workflow.add_edge("fetch_context", "call_optimizer")
        workflow.add_edge("call_optimizer", "explain")
        workflow.add_edge("explain", END)
        return workflow.compile()


# ─── Graph Nodes ──────────────────────────────────────────────────────────────

def _node_fetch_context(state: AgentState) -> AgentState:
    db = state["db"]
    tenant_id = state["tenant_id"]
    plan_date = state["plan_date"]
    from app.models.order import Order
    from app.models.driver import Driver
    from datetime import datetime, timedelta

    plan_dt = datetime.strptime(plan_date, "%Y-%m-%d").date()
    orders = db.query(Order).filter(
        Order.tenant_id == tenant_id,
        Order.status == 'PENDING',
        Order.scheduled_date >= datetime.combine(plan_dt, datetime.min.time()),
        Order.scheduled_date < datetime.combine(plan_dt + timedelta(days=1), datetime.min.time()),
    ).all()
    drivers = db.query(Driver).filter(
        Driver.tenant_id == tenant_id,
        Driver.is_active == True,
    ).all()

    context = {
        "total_orders": len(orders),
        "total_drivers": len(drivers),
        "orders_with_time_windows": sum(1 for o in orders if o.time_window_start),
        "high_priority_orders": sum(1 for o in orders if o.priority in ('HIGH', 'CRITICAL')),
        "plan_date": plan_date,
    }
    log = {"step": "fetch_context", "role": "tool",
           "content": f"Fetched {len(orders)} orders and {len(drivers)} drivers for {plan_date}"}
    return {**state, "context": context, "logs": state["logs"] + [log]}


def _node_call_optimizer(state: AgentState) -> AgentState:
    from app.planners.ortools_planner import ORToolsPlanner
    result = ORToolsPlanner().plan_day(state["db"], state["tenant_id"], state["plan_date"])
    log = {
        "step": "call_optimizer",
        "role": "tool",
        "content": (
            f"OR-Tools assigned {result.get('assigned_orders', 0)} of "
            f"{result.get('total_orders', 0)} orders across "
            f"{result.get('total_routes', 0)} routes."
        ),
    }
    return {**state, "plan_result": result, "logs": state["logs"] + [log]}


def _node_explain(state: AgentState) -> AgentState:
    llm = state["llm"]
    ctx = state["context"]
    plan = state["plan_result"]
    prompt = (
        f"You are a fleet dispatch AI. Summarize this routing plan in 2-3 sentences "
        f"for a dispatcher. Be concise and professional.\n\n"
        f"Date: {ctx.get('plan_date')}\n"
        f"Orders: {plan.get('total_orders', 0)} total, "
        f"{plan.get('assigned_orders', 0)} assigned\n"
        f"Routes: {plan.get('total_routes', 0)} drivers assigned\n"
        f"High priority: {ctx.get('high_priority_orders', 0)}\n"
        f"Time-windowed: {ctx.get('orders_with_time_windows', 0)}\n"
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        explanation = response.content
    except Exception as e:
        explanation = f"Plan generated: {plan.get('assigned_orders', 0)} orders assigned to {plan.get('total_routes', 0)} drivers."

    log = {"step": "explain", "role": "llm", "content": explanation}
    return {**state, "explanation": explanation, "logs": state["logs"] + [log]}
```

### New API: `GET /api/v1/agent-logs`
```python
@router.get("/agent-logs")
def get_agent_logs(
    plan_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(require_dispatcher),
):
    q = db.query(AgentLog).filter(AgentLog.tenant_id == current_user.tenant_id)
    if plan_id:
        q = q.filter(AgentLog.plan_id == plan_id)
    return q.order_by(AgentLog.created_at.desc()).limit(limit).all()
```

### Updated `PlanResult` response shape
Add two optional fields to the `/plan/day` response:
```python
class PlanResult(BaseModel):
    # ... existing fields ...
    planner: str = "rule_based"          # "rule_based" | "ortools" | "langgraph"
    explanation: Optional[str] = None    # LLM-generated summary (langgraph only)
```

### Acceptance Criteria
- [ ] `PLANNER_TYPE=langgraph` uses agent flow
- [ ] Agent falls back to OR-Tools if no LLM configured
- [ ] Agent logs stored in `agent_logs` table
- [ ] `GET /agent-logs?plan_id=` returns step-by-step reasoning
- [ ] `explanation` field returned in plan result when langgraph used
- [ ] Switching LLM provider = change `llm_provider` in tenant config, no code change

---

---

## Epic P2-E4: Real-Time GPS Tracking

### Goal
Driver app pings location every 30 seconds. Dispatcher dashboard shows live driver positions. Latest position stored in Redis for fast reads; full history in Postgres.

### New Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/tracking/ping` | driver | Receive GPS ping from driver app |
| `GET` | `/api/v1/tracking/live` | dispatcher | Get latest position of all active drivers |
| `GET` | `/api/v1/tracking/history/{driver_id}` | dispatcher | Full ping history for a driver |

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/models/tracking.py` | **New** | `DriverLocationPing` model |
| `app/schemas/tracking.py` | **New** | Ping request/response schemas |
| `app/api/v1/tracking.py` | **New** | All 3 tracking endpoints |
| `app/services/tracking_service.py` | **New** | Business logic: write ping, read latest |
| `app/api/router.py` | Update | Register tracking router |
| `alembic/versions/` | **New** | Migration: driver_location_pings table |

### Implementation: `app/models/tracking.py`

```python
import uuid
from sqlalchemy import Column, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base
from app.models.mixins import TimestampMixin, TenantMixin
from datetime import datetime

class DriverLocationPing(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_location_pings"
    __table_args__ = (
        Index("ix_dlp_driver_recorded", "driver_id", "recorded_at"),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id   = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    latitude    = Column(Float, nullable=False)
    longitude   = Column(Float, nullable=False)
    accuracy_m  = Column(Float, nullable=True)     # GPS accuracy in metres
    speed_kmh   = Column(Float, nullable=True)     # optional from device
    heading_deg = Column(Float, nullable=True)     # 0-360 degrees
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
```

### Implementation: `app/services/tracking_service.py`

```python
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.tracking import DriverLocationPing
from app.core.db import get_redis   # returns Redis client

REDIS_TTL_SECONDS = 3600  # 1 hour

def record_ping(db: Session, tenant_id: str, driver_id: str,
                lat: float, lng: float, accuracy: float = None,
                speed: float = None, heading: float = None):
    # 1. Write to Postgres for history
    ping = DriverLocationPing(
        tenant_id=tenant_id,
        driver_id=driver_id,
        latitude=lat,
        longitude=lng,
        accuracy_m=accuracy,
        speed_kmh=speed,
        heading_deg=heading,
        recorded_at=datetime.utcnow(),
    )
    db.add(ping)
    db.commit()

    # 2. Cache latest position in Redis
    redis = get_redis()
    key = f"driver:{driver_id}:location"
    payload = json.dumps({
        "driver_id": driver_id,
        "latitude": lat,
        "longitude": lng,
        "accuracy_m": accuracy,
        "speed_kmh": speed,
        "heading_deg": heading,
        "recorded_at": ping.recorded_at.isoformat(),
    })
    redis.setex(key, REDIS_TTL_SECONDS, payload)
    return ping


def get_live_positions(db: Session, tenant_id: str) -> list[dict]:
    """Return latest position for every active driver in tenant."""
    from app.models.driver import Driver
    drivers = db.query(Driver).filter(
        Driver.tenant_id == tenant_id,
        Driver.is_active == True,
    ).all()

    redis = get_redis()
    positions = []
    for driver in drivers:
        key = f"driver:{driver.id}:location"
        raw = redis.get(key)
        if raw:
            pos = json.loads(raw)
            pos["driver_name"] = driver.full_name
            positions.append(pos)
    return positions
```

### Add `get_redis()` to `app/core/db.py`
```python
import redis as redis_lib
from app.core.config import settings

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client
```

### Driver app: auto-ping from DriverView
In `src/pages/DriverView.tsx`, add a `useEffect` that calls `POST /api/v1/tracking/ping` every 30 seconds using the browser Geolocation API.

```typescript
// In DriverView.tsx
useEffect(() => {
  if (!navigator.geolocation) return
  const interval = setInterval(() => {
    navigator.geolocation.getCurrentPosition((pos) => {
      pingLocation({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy_m: pos.coords.accuracy,
      })
    })
  }, 30_000)
  return () => clearInterval(interval)
}, [])
```

### Acceptance Criteria
- [ ] `POST /tracking/ping` from driver app stores ping in DB + Redis
- [ ] `GET /tracking/live` returns latest position for all active drivers within 1s
- [ ] Driver app pings every 30s when on DriverView page
- [ ] Redis key `driver:{id}:location` updated on each ping
- [ ] Redis TTL = 1 hour (driver goes offline → position expires)

---

---

## Epic P2-E5: Live Map Dashboard (Frontend)

### Goal
Dispatcher sees a live map with driver markers and their assigned routes. Free tile provider (OpenStreetMap) — no API key required. Architecture makes it trivial to swap to Mapbox/Google Maps later.

### Map Library Choice

| Library | Tiles | Cost | Swap-friendliness |
|---------|-------|------|-------------------|
| **Leaflet + react-leaflet** | OpenStreetMap (free forever) | Free | Change 1 line for Mapbox |
| Mapbox GL JS | Mapbox | Free tier limited | N/A |
| Google Maps React | Google Maps | $$ | N/A |

**Decision: react-leaflet + OpenStreetMap**

Swapping to Mapbox later = change the `tileUrl` constant in one file.

### New Dependencies (Frontend)
```json
"leaflet": "^1.9.x",
"react-leaflet": "^4.2.x",
"@types/leaflet": "^1.9.x"
```

### New Files (Frontend)

| File | Description |
|------|-------------|
| `src/api/tracking.ts` | `fetchLivePositions()`, `pingLocation()` |
| `src/components/map/FleetMap.tsx` | Main map component |
| `src/components/map/DriverMarker.tsx` | Custom driver marker with popup |
| `src/components/map/RoutePolyline.tsx` | Draws route lines from stop coords |
| `src/pages/LiveMap.tsx` | Full page — map + sidebar driver list |

### Implementation: `src/components/map/FleetMap.tsx`

```typescript
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import DriverMarker from './DriverMarker'
import RoutePolyline from './RoutePolyline'

// To swap to Mapbox later: change TILE_URL and add accessToken
const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTRIBUTION = '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'

interface Props {
  positions: DriverPosition[]
  routes?: RouteOverlay[]
  center?: [number, number]
  zoom?: number
}

export default function FleetMap({ positions, routes = [], center = [12.9716, 77.5946], zoom = 12 }: Props) {
  return (
    <MapContainer center={center} zoom={zoom} className="w-full h-full rounded-lg">
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      {positions.map(p => <DriverMarker key={p.driver_id} position={p} />)}
      {routes.map((r, i) => <RoutePolyline key={i} route={r} />)}
    </MapContainer>
  )
}
```

### Implementation: `src/pages/LiveMap.tsx`

```typescript
import { useQuery } from '@tanstack/react-query'
import AppLayout from '../components/layout/AppLayout'
import FleetMap from '../components/map/FleetMap'
import { fetchLivePositions } from '../api/tracking'

export default function LiveMap() {
  const { data: positions = [] } = useQuery({
    queryKey: ['live-positions'],
    queryFn: fetchLivePositions,
    refetchInterval: 10_000,   // poll every 10 seconds
  })

  return (
    <AppLayout>
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-bold dark:text-white">Live Fleet Map</h2>
          <p className="text-sm text-gray-500">{positions.length} drivers active · updates every 10s</p>
        </div>
        <div className="h-[calc(100vh-180px)] w-full">
          <FleetMap positions={positions} center={[12.9716, 77.5946]} zoom={12} />
        </div>
      </div>
    </AppLayout>
  )
}
```

### Router Update (`src/routes/AppRoutes.tsx`)
Add route: `<Route path="/map" element={<ProtectedRoute><LiveMap /></ProtectedRoute>} />`

### Sidebar Update (`AppLayout.tsx`)
Add nav item: `{ icon: Map, label: 'Live Map', path: '/map' }`

### Acceptance Criteria
- [ ] Map renders on `/map` page with OpenStreetMap tiles (no API key)
- [ ] Driver markers appear when `GET /tracking/live` returns data
- [ ] Map auto-refreshes every 10 seconds
- [ ] Marker popup shows driver name + last update time
- [ ] Swapping tile provider = change `TILE_URL` constant only

---

---

## Epic P2-E6: Agent Activity Feed (Frontend)

### Goal
After generating a plan with the LangGraph agent, the dispatcher sees a collapsible feed of what the agent did — fetch, optimize, explain — with timestamps and reasoning. Builds trust in AI decision-making.

### New Files

| File | Description |
|------|-------------|
| `src/api/agentLogs.ts` | `fetchAgentLogs(planId)` |
| `src/components/shared/AgentFeed.tsx` | Renders agent step-by-step log |
| Update `src/pages/Planning.tsx` | Show AgentFeed below plan result |

### Implementation: `src/components/shared/AgentFeed.tsx`

```typescript
import { Bot, Wrench, Brain } from 'lucide-react'

interface AgentLogEntry {
  id: string
  step: string
  role: 'agent' | 'tool' | 'llm'
  content: string
  created_at: string
  llm_provider?: string
}

interface Props {
  logs: AgentLogEntry[]
  isLoading?: boolean
}

const ROLE_CONFIG = {
  tool:  { icon: Wrench, color: 'text-blue-500',  bg: 'bg-blue-50 dark:bg-blue-900/20' },
  llm:   { icon: Brain,  color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20' },
  agent: { icon: Bot,    color: 'text-green-500',  bg: 'bg-green-50 dark:bg-green-900/20' },
}

export default function AgentFeed({ logs, isLoading }: Props) {
  if (isLoading) return <div className="text-sm text-gray-400 animate-pulse">Loading agent reasoning...</div>
  if (!logs.length) return null

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
        <Bot size={14} /> Agent Reasoning
      </h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {logs.map(log => {
          const cfg = ROLE_CONFIG[log.role] || ROLE_CONFIG.agent
          const Icon = cfg.icon
          return (
            <div key={log.id} className={`flex gap-2 p-2 rounded text-xs ${cfg.bg}`}>
              <Icon size={13} className={`${cfg.color} shrink-0 mt-0.5`} />
              <div>
                <span className="font-mono text-gray-500 mr-2">{log.step}</span>
                <span className="text-gray-700 dark:text-gray-300">{log.content}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

### Planning page update
After plan generation (when `planResult` is set), fetch agent logs and show `<AgentFeed>` below the assignments table.

### Acceptance Criteria
- [ ] AgentFeed visible on Planning page after plan generated
- [ ] Shows fetch → optimize → explain steps with icons
- [ ] LLM explanation shown prominently at top of feed
- [ ] Hidden/collapsed by default if rule_based planner used
- [ ] Shows which LLM provider was used

---

---

## Epic P2-E7: SLA Risk Alerts

### Goal
Flag orders at risk of missing their delivery time window. Show dispatcher an at-risk panel in real time. No Celery needed — simple polling-based check.

### New Endpoint
```
GET /api/v1/sla/at-risk?plan_date=YYYY-MM-DD
```

Returns orders where:
`last_driver_ping_time + haversine_travel_time > time_window_end`

### Files

| File | Action | Description |
|------|--------|-------------|
| `app/services/sla_service.py` | **New** | Compute at-risk stops |
| `app/api/v1/sla.py` | **New** | `GET /sla/at-risk` endpoint |
| `app/api/router.py` | Update | Register SLA router |
| `src/api/sla.ts` | **New** | Frontend API call |
| Update `src/pages/Dashboard.tsx` | **Update** | At-risk alert panel |

### SLA Risk Logic (`app/services/sla_service.py`)
```python
def get_at_risk_stops(db, tenant_id, plan_date):
    """
    A stop is AT RISK if:
    - It has a time_window_end
    - Its status is still PENDING or IN_TRANSIT
    - Driver's last known location + estimated travel time > time_window_end
    """
    ...returns list of at-risk stops with driver name, order ref, window, eta
```

### Dashboard Panel
Add to `Dashboard.tsx`:
```typescript
// Polled every 60 seconds
const { data: atRisk = [] } = useQuery({
  queryKey: ['sla-at-risk', today],
  queryFn: () => fetchAtRiskStops(today),
  refetchInterval: 60_000,
})

// Render: alert panel with count badge, expandable list
```

### Acceptance Criteria
- [ ] `GET /sla/at-risk` returns list with driver, order, window, estimated ETA
- [ ] Dashboard shows "At-Risk Deliveries" count badge (red if > 0)
- [ ] Badge is 0 when no stops at risk
- [ ] Refreshes every 60 seconds

---

---

## Phase 2 File Checklist

### Backend

| File | Epic | Status |
|------|------|--------|
| `requirements.txt` | P2-E1, P2-E2 | ⬜ |
| `app/core/config.py` | P2-E1 | ⬜ |
| `app/planners/ortools_planner.py` | P2-E1 | ⬜ |
| `app/services/planning_service.py` | P2-E1 | ⬜ |
| `app/core/llm_factory.py` | P2-E2 | ⬜ |
| `app/models/tenant.py` | P2-E2 | ⬜ |
| `app/schemas/tenant.py` | P2-E2 | ⬜ |
| `app/api/v1/tenants.py` | P2-E2 | ⬜ |
| `app/models/agent_log.py` | P2-E3 | ⬜ |
| `app/planners/tools/__init__.py` | P2-E3 | ⬜ |
| `app/planners/langgraph_agent.py` | P2-E3 | ⬜ |
| `app/api/v1/agent_logs.py` | P2-E3 | ⬜ |
| `app/schemas/agent_log.py` | P2-E3 | ⬜ |
| `app/models/tracking.py` | P2-E4 | ⬜ |
| `app/schemas/tracking.py` | P2-E4 | ⬜ |
| `app/api/v1/tracking.py` | P2-E4 | ⬜ |
| `app/services/tracking_service.py` | P2-E4 | ⬜ |
| `app/core/db.py` | P2-E4 | ⬜ |
| `app/services/sla_service.py` | P2-E7 | ⬜ |
| `app/api/v1/sla.py` | P2-E7 | ⬜ |
| `alembic/versions/xxx_p2_ortools_llm_config.py` | P2-E1,E2 | ⬜ |
| `alembic/versions/xxx_p2_tracking_agent_logs.py` | P2-E3,E4 | ⬜ |

### Frontend

| File | Epic | Status |
|------|------|--------|
| `src/api/tracking.ts` | P2-E4 | ⬜ |
| `src/api/agentLogs.ts` | P2-E6 | ⬜ |
| `src/api/sla.ts` | P2-E7 | ⬜ |
| `src/components/map/FleetMap.tsx` | P2-E5 | ⬜ |
| `src/components/map/DriverMarker.tsx` | P2-E5 | ⬜ |
| `src/components/map/RoutePolyline.tsx` | P2-E5 | ⬜ |
| `src/pages/LiveMap.tsx` | P2-E5 | ⬜ |
| `src/components/shared/AgentFeed.tsx` | P2-E6 | ⬜ |
| `src/pages/Planning.tsx` | P2-E6 | ⬜ |
| `src/pages/Dashboard.tsx` | P2-E7 | ⬜ |
| `src/routes/AppRoutes.tsx` | P2-E5 | ⬜ |
| `src/pages/DriverView.tsx` | P2-E4 | ⬜ |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LangChain `BaseChatModel` abstraction | All providers (Gemini/OpenAI/Claude) return same interface — LangGraph nodes don't care which LLM |
| Per-tenant `llm_api_key` in DB | Tenants bring their own keys; platform owner never pays for tenant LLM usage |
| Gemini as default demo provider | Free tier available; `gemini-2.0-flash` is fast and capable |
| Fallback chain: tenant → env → rule_based | Zero crash if no key configured — system degrades gracefully |
| OR-Tools wraps rule_based fallback | If no solution found in 10s, always returns a valid plan |
| Leaflet + OpenStreetMap | Zero cost, no API key, swap to Mapbox = 1 line change |
| Polling over WebSocket | Simpler for Phase 2; WebSocket upgrade in Phase 3 when scale demands it |
| Agent logs in Postgres | Full audit trail of AI decisions; queryable; survives restarts |

---

## Implementation Order

```
Week 1 — Backend Core
  Day 1: P2-E1 — OR-Tools (requirements + planner + service switch + migration)
  Day 2: P2-E2 — LLM Factory (factory + tenant model update + PATCH endpoint + migration)
  Day 3: P2-E3 — LangGraph Agent (models + agent + tools + agent_logs API)
  Day 4: P2-E4 — GPS Tracking (model + service + Redis + endpoints + migration)
  Day 5: P2-E7 — SLA Service + endpoint

Week 2 — Frontend
  Day 1: P2-E5 — Live Map (install leaflet + FleetMap + LiveMap page + routing)
  Day 2: P2-E6 — Agent Feed (AgentFeed component + Planning page update)
  Day 3: P2-E4 FE — Driver geo-ping in DriverView
  Day 4: P2-E7 FE — Dashboard at-risk panel
  Day 5: Integration test + seed data update + polish
```

---

**Document Status:** Active
**Last Updated:** 2026-03-29
