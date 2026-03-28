# Driver View – Technical Specification

> **For AI Coding Assistants:** This is a mobile-first responsive web page — NOT a separate app. It runs inside the same FleetOpsX-UI React app, behind the `/driver` route. Driver logs in with the same login page and is redirected here. Keep it simple: today's stops, status buttons, nothing else.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Driver View (Basic) |
| **Epic** | P1-E6 |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | P1-E3 RouteStop model, P1-E3-S6 Auth (driver role), P1-E4 Planner (produces assignments), P1-E5 Login page |
| **Implementation Branch** | feat/p1-e6-driver-view |

---

## Executive Summary

**Purpose:** Give drivers a simple mobile web page to see their assigned stops for today and update delivery status. Driver logs in → sees ordered list of today's stops → taps "Delivered", "Failed", or "Issue" per stop. This closes the loop on the demo: plan is generated → driver receives assignment → driver marks deliveries done.

### Key Deliverables

| Component | File | Status |
|-----------|------|--------|
| Driver route stops API | `app/api/v1/driver.py` (backend) | ⬜ |
| Driver view page | `src/pages/DriverView.tsx` | ⬜ |
| Stop card component | `src/components/driver/StopCard.tsx` | ⬜ |

---

## 1. Backend: New Driver Endpoints

### Add to `app/api/v1/driver.py` (new file)

```python
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db, require_driver, get_current_user
from app.models.user import User
from app.models.route_plan import Route, RouteStop
from app.models.order import Order
from app.models.driver import Driver

router = APIRouter(prefix="/driver", tags=["Driver"])


@router.get("/my-stops")
def get_my_stops(
    plan_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns today's assigned stops for the logged-in driver.
    Finds the Driver record matching this user's email, then finds their routes.
    """
    if plan_date is None:
        plan_date = date.today()

    # Find driver record by email
    driver = db.execute(
        select(Driver).where(
            Driver.email == current_user.email,
            Driver.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not driver:
        return {"driver": None, "stops": [], "message": "No driver record linked to this account"}

    # Find routes for this driver on this date
    routes = db.execute(
        select(Route).join(
            Route.plan
        ).where(
            Route.driver_id == driver.id,
            Route.tenant_id == current_user.tenant_id,
        )
    ).scalars().all()

    if not routes:
        return {"driver": {"id": str(driver.id), "name": driver.full_name}, "stops": [], "message": "No routes assigned for today"}

    # Collect all stops across routes, ordered by sequence
    stops = []
    for route in routes:
        route_stops = db.execute(
            select(RouteStop).where(RouteStop.route_id == route.id)
            .order_by(RouteStop.sequence)
        ).scalars().all()

        for rs in route_stops:
            order = db.get(Order, rs.order_id)
            stops.append({
                "stop_id": str(rs.id),
                "sequence": rs.sequence,
                "status": rs.status,
                "order_id": str(rs.order_id),
                "delivery_address": order.delivery_address if order else "Unknown",
                "delivery_latitude": order.delivery_latitude if order else None,
                "delivery_longitude": order.delivery_longitude if order else None,
                "time_window_start": str(order.time_window_start) if order and order.time_window_start else None,
                "time_window_end": str(order.time_window_end) if order and order.time_window_end else None,
                "priority": order.priority if order else "NORMAL",
                "notes": order.notes if order else None,
            })

    return {
        "driver": {"id": str(driver.id), "name": driver.full_name},
        "plan_date": str(plan_date),
        "total_stops": len(stops),
        "stops": stops,
    }


@router.patch("/stops/{stop_id}/status")
def update_stop_status(
    stop_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Driver updates a stop status: ARRIVED | DELIVERED | FAILED | SKIPPED
    Also updates the linked Order status.
    """
    new_status = body.get("status")
    valid_statuses = {"ARRIVED", "DELIVERED", "FAILED", "SKIPPED"}
    if new_status not in valid_statuses:
        raise HTTPException(400, f"Status must be one of: {valid_statuses}")

    from uuid import UUID
    stop = db.execute(
        select(RouteStop).where(
            RouteStop.id == UUID(stop_id),
            RouteStop.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not stop:
        raise HTTPException(404, "Stop not found")

    stop.status = new_status
    if new_status == "DELIVERED":
        order = db.get(Order, stop.order_id)
        if order:
            order.status = "DELIVERED"
    elif new_status == "FAILED":
        order = db.get(Order, stop.order_id)
        if order:
            order.status = "FAILED"

    db.commit()
    return {"stop_id": stop_id, "status": new_status, "message": "Status updated"}
```

**Register in `app/api/router.py`:**
```python
from app.api.v1 import driver as driver_router
api_router.include_router(driver_router.router, prefix="/api/v1")
```

---

## 2. Frontend: `src/api/driver.ts`

```typescript
import client from './client'

export const fetchMyStops = (plan_date?: string) =>
  client.get('/api/v1/driver/my-stops', { params: plan_date ? { plan_date } : {} }).then(r => r.data)

export const updateStopStatus = (stop_id: string, status: string) =>
  client.patch(`/api/v1/driver/stops/${stop_id}/status`, { status }).then(r => r.data)
```

---

## 3. Driver View Page — `src/pages/DriverView.tsx`

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchMyStops, updateStopStatus } from '../api/driver'
import useAppStore from '../store/useAppStore'
import toast from 'react-hot-toast'
import { LogOut, MapPin, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function DriverView() {
  const { user, clearAuth } = useAppStore()
  const qc = useQueryClient()
  const today = new Date().toISOString().split('T')[0]

  const { data, isLoading } = useQuery({
    queryKey: ['my-stops', today],
    queryFn: () => fetchMyStops(today),
  })

  const statusMutation = useMutation({
    mutationFn: ({ stop_id, status }: { stop_id: string; status: string }) =>
      updateStopStatus(stop_id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-stops'] })
      toast.success('Status updated')
    },
    onError: () => toast.error('Failed to update'),
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
        <p className="text-gray-500">Loading your stops...</p>
      </div>
    )
  }

  const stops = data?.stops || []
  const driverName = data?.driver?.name || user?.full_name || 'Driver'
  const delivered = stops.filter((s: any) => s.status === 'DELIVERED').length

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-blue-600 text-white px-4 py-4 flex justify-between items-center sticky top-0 z-10">
        <div>
          <p className="font-bold text-lg">{driverName}</p>
          <p className="text-blue-200 text-sm">{today} · {delivered}/{stops.length} done</p>
        </div>
        <button onClick={() => { clearAuth(); window.location.href = '/login' }} className="p-2">
          <LogOut size={20} />
        </button>
      </div>

      {/* Progress bar */}
      <div className="bg-blue-100 dark:bg-blue-900 h-2">
        <div
          className="bg-blue-500 h-2 transition-all"
          style={{ width: stops.length ? `${(delivered / stops.length) * 100}%` : '0%' }}
        />
      </div>

      {/* Stops list */}
      <div className="p-4 space-y-3 max-w-lg mx-auto">
        {stops.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg font-medium">No stops for today</p>
            <p className="text-sm mt-1">Check back after the dispatcher generates a plan</p>
          </div>
        ) : (
          stops.map((stop: any, idx: number) => (
            <StopCard
              key={stop.stop_id}
              stop={stop}
              index={idx + 1}
              onStatusChange={(status) => statusMutation.mutate({ stop_id: stop.stop_id, status })}
              isUpdating={statusMutation.isPending}
            />
          ))
        )}
      </div>
    </div>
  )
}

function StopCard({ stop, index, onStatusChange, isUpdating }: any) {
  const [expanded, setExpanded] = useState(stop.status === 'PENDING')

  const statusColors: Record<string, string> = {
    PENDING: 'bg-gray-100 border-gray-300',
    ARRIVED: 'bg-blue-50 border-blue-300',
    DELIVERED: 'bg-green-50 border-green-300',
    FAILED: 'bg-red-50 border-red-300',
    SKIPPED: 'bg-yellow-50 border-yellow-300',
  }

  return (
    <div className={`rounded-xl border-2 p-4 transition-colors ${statusColors[stop.status] || statusColors.PENDING}`}>
      <div className="flex justify-between items-start" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start gap-3">
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center font-bold shrink-0">
            {index}
          </span>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100 text-sm leading-tight">{stop.delivery_address}</p>
            {stop.time_window_start && (
              <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                <Clock size={11} /> {stop.time_window_start} – {stop.time_window_end}
              </p>
            )}
          </div>
        </div>
        <StatusIcon status={stop.status} />
      </div>

      {/* Actions — show when expanded and not yet delivered/failed */}
      {expanded && !['DELIVERED', 'FAILED', 'SKIPPED'].includes(stop.status) && (
        <div className="flex gap-2 mt-4">
          {stop.status === 'PENDING' && (
            <button
              className="flex-1 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium"
              onClick={() => onStatusChange('ARRIVED')}
              disabled={isUpdating}
            >
              Arrived
            </button>
          )}
          <button
            className="flex-1 py-2 rounded-lg bg-green-600 text-white text-sm font-medium"
            onClick={() => onStatusChange('DELIVERED')}
            disabled={isUpdating}
          >
            Delivered ✓
          </button>
          <button
            className="flex-1 py-2 rounded-lg bg-red-500 text-white text-sm font-medium"
            onClick={() => onStatusChange('FAILED')}
            disabled={isUpdating}
          >
            Failed ✗
          </button>
        </div>
      )}

      {stop.status === 'DELIVERED' && (
        <p className="text-sm text-green-600 font-medium mt-3 flex items-center gap-1">
          <CheckCircle size={14} /> Delivered
        </p>
      )}
      {stop.status === 'FAILED' && (
        <p className="text-sm text-red-500 font-medium mt-3 flex items-center gap-1">
          <XCircle size={14} /> Marked as failed
        </p>
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'DELIVERED') return <CheckCircle size={18} className="text-green-500 shrink-0" />
  if (status === 'FAILED') return <XCircle size={18} className="text-red-500 shrink-0" />
  if (status === 'ARRIVED') return <MapPin size={18} className="text-blue-500 shrink-0" />
  return <AlertCircle size={18} className="text-gray-400 shrink-0" />
}
```

---

## 4. Link Driver User → Driver Record

In `scripts/seed_data.py`, the demo driver user `driver@demo.com` should have the same email as one of the seeded Driver records. Add this to the seed script:

```python
# After creating driver_user, update the first driver's email to match
if drivers:
    drivers[0].email = "driver@demo.com"
    print(f"  ✅ Driver '{drivers[0].full_name}' linked to driver@demo.com")
```

---

## 5. File Checklist

| Action | File | Status |
|--------|------|--------|
| CREATE | `app/api/v1/driver.py` (backend endpoints) | ⬜ |
| MODIFY | `app/api/router.py` (register driver router) | ⬜ |
| CREATE | `src/api/driver.ts` | ⬜ |
| CREATE | `src/pages/DriverView.tsx` | ⬜ |
| MODIFY | `scripts/seed_data.py` (link driver email) | ⬜ |

---

## 6. Demo Walkthrough (E2E test of full Phase 1)

```bash
# 1. Seed data
python scripts/seed_data.py --start-date 2026-01-15

# 2. Login as dispatcher → generate plan for 2026-01-15
# (via UI or curl)

# 3. Login as driver (driver@demo.com / demo1234 / <tenant_id>)
# Navigate to http://localhost:5173/driver
# Should see assigned stops

# 4. Tap "Arrived" on first stop
# 5. Tap "Delivered" on first stop
# 6. Check dispatcher dashboard — delivered count goes up
```

---

**Document Status:** Not Started  
**Last Updated:** 2026-03-29
