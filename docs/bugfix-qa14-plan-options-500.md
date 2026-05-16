# QA-14 Bug Fix: `POST /plan/options` returns HTTP 500

**Date:** 2026-05-17  
**Severity:** High — feature completely broken  
**Endpoint:** `POST /api/v1/plan/options`  
**File changed:** `app/planners/ortools_planner.py`

---

## Summary

`POST /plan/options` returned HTTP 500 whenever it was called. The endpoint is meant to run OR-Tools three times (one per mode: `fastest`, `economical`, `balanced`) and return a comparison of the three draft plans so the dispatcher can pick one.

---

## Root Cause

### Primary: SQLAlchemy `uselist=False` back-populates eviction → NOT NULL violation

`plan_options_service.generate_options` calls `ORToolsPlanner.plan_day(commit_assignments=False)` in a loop — once per mode — passing the same SQLAlchemy `db` session each time.

`ORToolsPlanner.plan_day` creates `RouteStop` rows via the ORM:

```python
stop = RouteStop(route_id=route.id, order_id=order.id, ...)
db.add(stop)
```

The `Order` model declares a one-to-one back-reference:

```python
# app/models/order.py
route_stop = relationship("RouteStop", back_populates="order", uselist=False)
```

**What happens on iteration 2 (mode = "economical"):**

1. After `db.commit()` from iteration 1, all session objects are expired.
2. Fresh `select(Order)` query re-loads the same orders (still `PENDING` because `commit_assignments=False`).
3. `RouteStop(order_id=order.id)` is created and `db.add(stop)` is called.
4. SQLAlchemy's `back_populates` machinery detects that `order.route_stop` is being replaced. It lazy-loads the current value — finding the `RouteStop` from iteration 1 (`stop1`).
5. To "evict" `stop1`, SQLAlchemy issues:
   ```sql
   UPDATE route_stops SET order_id = NULL WHERE id = <stop1.id>
   ```
6. `order_id` is `NOT NULL` in the DB → `IntegrityError` → **HTTP 500**.

This only manifests in `plan/options` (not `plan/day`) because `plan/day` never calls `plan_day` more than once in the same request, so there is never a second `RouteStop` for the same `order_id` in the same session.

### Secondary: `RuleBasedPlanner` fallback commits assignments

When OR-Tools cannot find a solution, the old code fell back to `RuleBasedPlanner.plan_day`, which always commits `order.status = "ASSIGNED"`. If mode 1 fell back, modes 2 and 3 would find zero `PENDING` orders and return nothing.

---

## Fix

### 1. Use SQLAlchemy Core `INSERT` for `RouteStop` rows

Replace `db.add(RouteStop(...))` with a direct Core INSERT. This bypasses ORM instrumentation and relationship management entirely — SQLAlchemy never attempts the uselist=False eviction.

```python
# Before
stop = RouteStop(
    route_id=route.id,
    order_id=order.id,
    sequence=seq,
    tenant_id=tid,
    status="PENDING",
)
db.add(stop)

# After
from sqlalchemy import insert as sa_insert

now = datetime.utcnow()
db.execute(
    sa_insert(RouteStop).values(
        id=uuid4(),
        route_id=route.id,
        order_id=order.id,
        sequence=seq,
        tenant_id=tid,
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
)
```

Core inserts are fully visible to subsequent ORM queries (they flush to the DB), so `confirm_plan` can still read the stops via `select(RouteStop).where(...)` as before.

### 2. Skip `RuleBasedPlanner` fallback when `commit_assignments=False`

```python
if not solution:
    if not commit_assignments:
        # Return empty result — this mode is skipped in the options summary.
        # Do NOT fall back to RuleBasedPlanner: it always commits assignments,
        # which would prevent the remaining modes from seeing pending orders.
        return {
            "plan_id": None,
            "total_distance_km": 0.0,
            "est_duration_min": 0,
            "est_fuel_cost": 0.0,
            ...
        }
    from app.planners.rule_based import RuleBasedPlanner
    result = RuleBasedPlanner().plan_day(db, tenant_id, plan_date)
    result["planner"] = "rule_based_fallback"
    return result
```

---

## Why Core INSERT is safe here

| Concern | Answer |
|---|---|
| `confirm_plan` reads RouteStops via `select(RouteStop)...` | ✅ Core INSERT rows are fully visible to ORM queries |
| `route_timeline` endpoint joins Route → RouteStop → Order | ✅ All FK columns are set correctly |
| `replan` endpoint queries PENDING RouteStops | ✅ `status="PENDING"` is set explicitly |
| `plan/day` (normal flow, `commit_assignments=True`) | ✅ Also uses Core INSERT now — no regression |
| `Order.route_stop` lazy-load | ✅ Still works — Core INSERT writes the FK; ORM reads it on demand |

---

## How to verify the fix

```bash
# 1. Ensure there are PENDING orders for the date
# 2. Call the endpoint
curl -X POST "http://localhost:8000/api/v1/plan/options?plan_date=2026-05-17" \
  -H "Authorization: Bearer <token>"

# Expected: 200 OK with {"plan_date": "...", "options": [...]} containing up to 3 modes
# Before fix: 500 Internal Server Error (sqlalchemy.exc.IntegrityError: NOT NULL violation)
```

---

## Files changed

| File | Change |
|---|---|
| `app/planners/ortools_planner.py` | `sa_insert` added to imports; `db.add(RouteStop(...))` replaced with `db.execute(sa_insert(RouteStop).values(...))` in the stop-creation loop; OR-Tools no-solution path returns empty dict when `commit_assignments=False` |
