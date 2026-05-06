from datetime import date, datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.order import Order
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.driver_availability import DriverAvailability
from app.models.vehicle_status import VehicleStatus
from app.models.route_plan import RoutePlan


def build_fleet_context(db: Session, tenant_id: str, for_date: date) -> str:
    tid = UUID(tenant_id)
    day_start = datetime.combine(for_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    orders = db.execute(
        select(Order).where(
            Order.tenant_id == tid,
            Order.scheduled_date >= day_start,
            Order.scheduled_date < day_end,
        )
    ).scalars().all()

    status_counts: dict[str, int] = {}
    for o in orders:
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    drivers = db.execute(
        select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
    ).scalars().all()

    avail_records = {
        r.driver_id: r.status
        for r in db.execute(
            select(DriverAvailability).where(
                DriverAvailability.tenant_id == tid,
                DriverAvailability.date == for_date,
            )
        ).scalars().all()
    }
    available_driver_count = sum(
        1 for d in drivers if avail_records.get(d.id, "available") == "available"
    )

    vehicles = db.execute(
        select(Vehicle).where(Vehicle.tenant_id == tid, Vehicle.is_active == True)
    ).scalars().all()

    vs_records = {
        r.vehicle_id: r.status
        for r in db.execute(
            select(VehicleStatus).where(VehicleStatus.tenant_id == tid)
        ).scalars().all()
    }
    available_vehicle_count = sum(
        1 for v in vehicles if vs_records.get(v.id, "available") == "available"
    )

    plan = db.execute(
        select(RoutePlan).where(
            RoutePlan.tenant_id == tid,
            RoutePlan.plan_date == for_date,
        ).order_by(RoutePlan.created_at.desc())
    ).scalars().first()

    plan_summary = "No plan generated yet for today."
    if plan:
        plan_summary = (
            f"A route plan exists (status: {plan.status}). "
            f"{plan.assigned_orders}/{plan.total_orders} orders assigned across {plan.total_routes} routes."
        )

    lines = [
        f"Today's date: {for_date}",
        f"Orders today: {len(orders)} total — " + ", ".join(f"{v} {k}" for k, v in status_counts.items()) if orders else "No orders today.",
        f"Drivers: {len(drivers)} active, {available_driver_count} available right now.",
        f"Vehicles: {len(vehicles)} active, {available_vehicle_count} available right now.",
        f"Plan: {plan_summary}",
    ]
    return "\n".join(lines)
