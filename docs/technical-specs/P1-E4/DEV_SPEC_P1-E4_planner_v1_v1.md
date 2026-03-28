# Rule-Based Planner v1 – Technical Specification

> **For AI Coding Assistants:** This is a Phase 1 planner — rule-based only, no LLM, no OR-Tools yet. The architecture must use `PlannerInterface` so Phase 2 can swap in a LangGraph agent behind the same endpoint. Do not add AI/LLM logic here.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Rule-Based Planner v1 |
| **Epic** | P1-E4 |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Author** | Antigravity |
| **Reference** | Blueprint Section 8 Phase 1 – Assisted Dispatch |
| **Depends On** | P1-E3 (Domain Models) – orders, drivers, vehicles must exist |
| **Implementation Branch** | feat/p1-e4-planner-v1 |

---

## Executive Summary

**Purpose:** Build the first version of the FleetOpsX planning engine. Given a date and tenant, it fetches unassigned orders and available drivers, and assigns the nearest available driver to each order using simple rule-based logic. The result is written back to the DB as assignments and a RoutePlan. A human dispatcher reviews before confirming.

### Key Deliverables

| Component | File | Priority | Status |
|-----------|------|----------|--------|
| RuleBasedPlanner | `app/planners/rule_based.py` | P0 | ⬜ |
| Planning service | `app/services/planning_service.py` | P0 | ⬜ |
| Maps API client | `app/core/maps.py` | P1 | ⬜ |
| /plan/day endpoint | `app/api/v1/planning.py` | P0 | ⬜ |
| Router registration | `app/api/router.py` | P0 | ⬜ |

### Success Criteria

- [ ] `POST /api/v1/plan/day?plan_date=2026-01-15` assigns unassigned orders to available drivers
- [ ] A `RoutePlan` record is created with status `DRAFT`
- [ ] Each assignment creates a `Route` and `RouteStop`
- [ ] Orders are updated with `assigned_driver_id`
- [ ] Endpoint returns structured plan summary

---

## 2. Functional Requirements

### FR-1: Driver Availability Check

**Logic:**
1. For a given `plan_date`, fetch all drivers belonging to the tenant that are `is_active = True`
2. Check `DriverShift` table for that date:
   - If shift record exists with `status = WORKING` → driver is available
   - If shift record exists with `status != WORKING` → driver is NOT available
   - If NO shift record exists → fall back to driver's `default_shift_start/end`
   - If driver has no default shift either → skip (treat as unavailable)

### FR-2: Order Filtering

**Logic:**
- Fetch orders where `tenant_id = :tid` AND `scheduled_date = :plan_date` AND `status = PENDING` AND `assigned_driver_id IS NULL`

### FR-3: Assignment Algorithm (Phase 1 – Simple)

**Logic (greedy nearest):**
```
for each unassigned order (sorted by priority: CRITICAL > HIGH > NORMAL > LOW):
    find available drivers not yet over-capacity for the day
    if driver has lat/long and order has delivery lat/long:
        pick driver with minimum Haversine distance to delivery point
    else:
        pick first available driver (round-robin)
    assign order to driver
    mark order as ASSIGNED
```

**Haversine distance formula:**
```python
import math

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371  # Earth radius km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))
```

### FR-4: Route & RoutePlan Creation

**Logic:**
```
1. Create RoutePlan(plan_date, status=DRAFT, tenant_id)
2. For each driver that received assignments:
   a. Create Route(plan_id, driver_id, status=PLANNED)
   b. For each order assigned to this driver (sorted by delivery lat/long cluster):
      Create RouteStop(route_id, order_id, sequence=i)
3. Update RoutePlan totals (total_orders, assigned_orders, total_routes)
4. Return plan summary
```

### FR-5: Maps API Integration (Optional for Phase 1)

If `MAPS_API_KEY` is set in environment, use Google Maps Distance Matrix API to get ETAs. If not set, skip ETA calculation (null ETAs are acceptable in Phase 1).

**File:** `app/core/maps.py`

```python
import httpx
import os
from typing import Optional

MAPS_API_KEY = os.getenv("MAPS_API_KEY")

async def get_distance_km(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float
) -> Optional[float]:
    if not MAPS_API_KEY:
        return None
    # call Google Maps Distance Matrix API
    # return distance in km
    ...
```

---

## 3. Architecture

```
POST /api/v1/plan/day?plan_date=YYYY-MM-DD
          │
          ▼
    PlanningRouter
    (app/api/v1/planning.py)
          │
          ▼
    PlanningService
    (app/services/planning_service.py)
          │
          └── calls PlannerInterface.plan_day(db, tenant_id, plan_date)
                    │
                    ▼
          RuleBasedPlanner
          (app/planners/rule_based.py)
                    │
          ┌─────────┼──────────────┐
          ▼         ▼              ▼
     fetch orders  fetch drivers  write RoutePlan
     (order_svc)   (driver_svc)   + Routes + RouteStops
                                  update Order.status
```

---

## 4. File Specifications

### `app/planners/rule_based.py`

```python
import math
from datetime import date
from typing import Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.planners.interface import PlannerInterface
from app.models.order import Order
from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.route_plan import RoutePlan, Route, RouteStop

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

class RuleBasedPlanner(PlannerInterface):
    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        tid = UUID(tenant_id)

        # 1. Fetch unassigned orders
        orders = db.execute(
            select(Order).where(
                Order.tenant_id == tid,
                Order.scheduled_date >= plan_date,
                Order.scheduled_date < date(plan_date.year, plan_date.month, plan_date.day + 1)
                    if plan_date.day < 28 else Order.scheduled_date == plan_date,
                Order.status == "PENDING",
                Order.assigned_driver_id.is_(None),
            )
        ).scalars().all()

        if not orders:
            return {"message": "No unassigned orders for this date", "assignments": [], "plan_id": None}

        # Sort by priority
        orders = sorted(orders, key=lambda o: PRIORITY_ORDER.get(o.priority, 99))

        # 2. Fetch available drivers
        drivers = db.execute(
            select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
        ).scalars().all()

        # Check shift availability
        shifts = db.execute(
            select(DriverShift).where(
                DriverShift.tenant_id == tid,
                DriverShift.shift_date == plan_date,
            )
        ).scalars().all()
        unavailable_ids = {s.driver_id for s in shifts if s.status != "WORKING"}
        available_drivers = [d for d in drivers if d.id not in unavailable_ids]

        if not available_drivers:
            return {"message": "No available drivers for this date", "assignments": [], "plan_id": None}

        # 3. Create RoutePlan
        plan = RoutePlan(
            plan_date=plan_date,
            status="DRAFT",
            tenant_id=tid,
            total_orders=len(orders),
            planner_version="rule_based_v1",
        )
        db.add(plan)
        db.flush()

        # 4. Assign orders to drivers
        driver_routes: dict[UUID, Route] = {}
        driver_stops: dict[UUID, list] = {}
        assignments = []

        for order in orders:
            # Pick nearest driver
            best_driver = None
            best_dist = float("inf")

            for driver in available_drivers:
                if order.delivery_latitude and order.delivery_longitude:
                    if driver.home_depot and driver.home_depot.latitude:
                        dist = haversine_km(
                            driver.home_depot.latitude, driver.home_depot.longitude,
                            order.delivery_latitude, order.delivery_longitude
                        )
                    else:
                        dist = 9999
                else:
                    dist = 9999

                if dist < best_dist:
                    best_dist = dist
                    best_driver = driver

            if not best_driver:
                best_driver = available_drivers[0]  # fallback

            # Get or create route for this driver
            if best_driver.id not in driver_routes:
                route = Route(
                    plan_id=plan.id,
                    driver_id=best_driver.id,
                    status="PLANNED",
                    tenant_id=tid,
                    total_stops=0,
                )
                db.add(route)
                db.flush()
                driver_routes[best_driver.id] = route
                driver_stops[best_driver.id] = []

            route = driver_routes[best_driver.id]
            seq = len(driver_stops[best_driver.id]) + 1
            stop = RouteStop(
                route_id=route.id,
                order_id=order.id,
                sequence=seq,
                tenant_id=tid,
            )
            db.add(stop)
            driver_stops[best_driver.id].append(stop)
            route.total_stops = seq

            # Update order
            order.assigned_driver_id = best_driver.id
            order.status = "ASSIGNED"

            assignments.append({
                "order_id": str(order.id),
                "driver_id": str(best_driver.id),
                "driver_name": best_driver.full_name,
                "sequence": seq,
            })

        # 5. Update plan summary
        plan.assigned_orders = len(assignments)
        plan.total_routes = len(driver_routes)

        db.commit()

        return {
            "plan_id": str(plan.id),
            "plan_date": str(plan_date),
            "status": "DRAFT",
            "total_orders": len(orders),
            "assigned_orders": len(assignments),
            "total_routes": len(driver_routes),
            "assignments": assignments,
        }

    def replan(self, db, tenant_id, plan_date, context):
        # Phase 2 — not implemented in Phase 1
        return {"message": "Replan not available in Phase 1"}
```

### `app/services/planning_service.py`

```python
from datetime import date
from typing import Any
from sqlalchemy.orm import Session
from app.planners.interface import PlannerInterface
from app.planners.rule_based import RuleBasedPlanner


class PlanningService:
    def __init__(self, planner: PlannerInterface | None = None):
        self.planner = planner or RuleBasedPlanner()

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        return self.planner.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict) -> dict[str, Any]:
        return self.planner.replan(db=db, tenant_id=tenant_id, plan_date=plan_date, context=context)
```

### `app/api/v1/planning.py`

```python
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import require_tenant_id, get_db
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/plan", tags=["Planning"])


@router.post("/day")
def plan_day(
    plan_date: date = Query(..., description="Date to plan for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    """
    Phase 1: Rule-based planner.
    Assigns unassigned orders to available drivers for the given date.
    Returns a DRAFT plan — dispatcher must confirm before it goes live.
    """
    service = PlanningService()
    return service.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)
```

---

## 5. File Checklist

| Action | File | Status |
|--------|------|--------|
| CREATE | `app/planners/rule_based.py` | ⬜ |
| CREATE | `app/services/planning_service.py` | ⬜ |
| CREATE | `app/core/maps.py` | ⬜ |
| CREATE | `app/api/v1/planning.py` | ⬜ |
| MODIFY | `app/api/router.py` (add planning router) | ⬜ |

---

## 6. Verification

```bash
TENANT_ID="<your-tenant-uuid>"
DATE="2026-01-15"

# First seed some data (use P1-E7 synthetic data script, or manual inserts)

# Run planner
curl -s -X POST "http://localhost:8000/api/v1/plan/day?plan_date=$DATE" \
  -H "X-Tenant-ID: $TENANT_ID" | jq .

# Expected response:
# {
#   "plan_id": "uuid...",
#   "plan_date": "2026-01-15",
#   "status": "DRAFT",
#   "total_orders": 10,
#   "assigned_orders": 10,
#   "total_routes": 3,
#   "assignments": [...]
# }

# Verify orders updated
curl -s "http://localhost:8000/api/v1/orders/?plan_date=$DATE" \
  -H "X-Tenant-ID: $TENANT_ID" | jq '[.[] | {id, status, assigned_driver_id}]'
```

---

**Document Status:** Not Started  
**Last Updated:** 2026-03-29  
**Implementation Status:** ⬜ Not Started
