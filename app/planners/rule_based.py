import math
from datetime import date, datetime, timedelta
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
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class RuleBasedPlanner(PlannerInterface):

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        tid = UUID(tenant_id)
        day_start = datetime.combine(plan_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        # 1. Fetch unassigned orders for the date
        orders = list(db.execute(
            select(Order).where(
                Order.tenant_id == tid,
                Order.scheduled_date >= day_start,
                Order.scheduled_date < day_end,
                Order.status == "PENDING",
                Order.assigned_driver_id.is_(None),
            )
        ).scalars().all())

        if not orders:
            return {"message": "No unassigned orders for this date", "assignments": [], "plan_id": None}

        # Sort by priority: CRITICAL first
        orders = sorted(orders, key=lambda o: PRIORITY_ORDER.get(o.priority, 99))

        # 2. Fetch active drivers
        drivers = list(db.execute(
            select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
        ).scalars().all())

        # Check shift records for unavailability
        shifts = list(db.execute(
            select(DriverShift).where(
                DriverShift.tenant_id == tid,
                DriverShift.shift_date == plan_date,
            )
        ).scalars().all())
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

        # 4. Assign orders to drivers (greedy nearest)
        driver_routes: dict[UUID, Route] = {}
        driver_stops: dict[UUID, list] = {}
        assignments = []

        for order in orders:
            best_driver = None
            best_dist = float("inf")

            for driver in available_drivers:
                if order.delivery_latitude and order.delivery_longitude:
                    if driver.home_depot and driver.home_depot.latitude and driver.home_depot.longitude:
                        dist = haversine_km(
                            driver.home_depot.latitude, driver.home_depot.longitude,
                            order.delivery_latitude, order.delivery_longitude,
                        )
                    else:
                        dist = 9999
                else:
                    dist = 9999

                if dist < best_dist:
                    best_dist = dist
                    best_driver = driver

            if not best_driver:
                best_driver = available_drivers[0]

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

            # Update order status
            order.assigned_driver_id = best_driver.id
            order.status = "ASSIGNED"

            assignments.append({
                "order_id": str(order.id),
                "driver_id": str(best_driver.id),
                "driver_name": best_driver.full_name,
                "sequence": seq,
            })

        # 5. Update plan totals
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

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict[str, Any]) -> dict[str, Any]:
        # Phase 2 — not implemented in Phase 1
        return {"message": "Replan not available in Phase 1"}
