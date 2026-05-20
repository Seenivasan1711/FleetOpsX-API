from datetime import date as date_type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.driver_availability import DriverAvailability
from app.models.vehicle_status import VehicleStatus
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.schemas.availability import (
    DriverAvailabilityUpdate,
    VehicleStatusUpdate,
    DriverAvailabilitySummary,
    VehicleStatusSummary,
)


def upsert_driver_availability(
    db: Session,
    tenant_id: str,
    driver_id: UUID,
    for_date: date_type,
    data: DriverAvailabilityUpdate,
) -> DriverAvailability:
    tid = UUID(tenant_id)
    record = db.execute(
        select(DriverAvailability).where(
            DriverAvailability.tenant_id == tid,
            DriverAvailability.driver_id == driver_id,
            DriverAvailability.date == for_date,
        )
    ).scalar_one_or_none()

    if record is None:
        record = DriverAvailability(
            tenant_id=tid,
            driver_id=driver_id,
            date=for_date,
        )
        db.add(record)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


def upsert_vehicle_status(
    db: Session,
    tenant_id: str,
    vehicle_id: UUID,
    data: VehicleStatusUpdate,
) -> VehicleStatus:
    tid = UUID(tenant_id)
    record = db.execute(
        select(VehicleStatus).where(
            VehicleStatus.tenant_id == tid,
            VehicleStatus.vehicle_id == vehicle_id,
        )
    ).scalar_one_or_none()

    if record is None:
        record = VehicleStatus(
            tenant_id=tid,
            vehicle_id=vehicle_id,
        )
        db.add(record)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


def get_fleet_availability(
    db: Session,
    tenant_id: str,
    for_date: date_type,
) -> dict:
    from app.models.route_plan import Route, RoutePlan
    from app.schemas.availability import (
        DriverCountSummary, VehicleCountSummary, FleetAvailabilityResponse,
    )
    tid = UUID(tenant_id)

    # ── Drivers ──────────────────────────────────────────────────────────────────
    drivers = db.execute(
        select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
    ).scalars().all()

    avail_records = {
        r.driver_id: r
        for r in db.execute(
            select(DriverAvailability).where(
                DriverAvailability.tenant_id == tid,
                DriverAvailability.date == for_date,
            )
        ).scalars().all()
    }

    # Drivers who appear in an active route plan for this date
    drivers_on_route: set = set(
        row[0] for row in db.execute(
            select(Route.driver_id)
            .join(RoutePlan, Route.plan_id == RoutePlan.id)
            .where(
                RoutePlan.tenant_id == tid,
                RoutePlan.plan_date == for_date,
            )
        ).all()
        if row[0] is not None
    )

    d_counts = DriverCountSummary(total=len(drivers))
    for d in drivers:
        avail = avail_records.get(d.id)
        status = avail.status if avail else "available"
        if d.id in drivers_on_route:
            d_counts.on_route += 1
        elif status == "on_break":
            d_counts.on_break += 1
        elif status == "off_duty":
            d_counts.off_duty += 1
        else:
            d_counts.available += 1

    # ── Vehicles ──────────────────────────────────────────────────────────────────
    vehicles = db.execute(
        select(Vehicle).where(Vehicle.tenant_id == tid, Vehicle.is_active == True)
    ).scalars().all()

    status_records = {
        r.vehicle_id: r
        for r in db.execute(
            select(VehicleStatus).where(VehicleStatus.tenant_id == tid)
        ).scalars().all()
    }

    v_counts = VehicleCountSummary(total=len(vehicles))
    for v in vehicles:
        vs = status_records.get(v.id)
        status = vs.status if vs else "available"
        fuel = vs.fuel_level_pct if vs else None
        if status == "in_use":
            v_counts.in_use += 1
        elif status == "maintenance":
            v_counts.maintenance += 1
        elif fuel is not None and fuel < 25.0:
            v_counts.low_fuel += 1
        else:
            v_counts.available += 1

    return FleetAvailabilityResponse(drivers=d_counts, vehicles=v_counts)
