from datetime import date, timedelta
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.driver import Driver
from app.models.analytics import DriverPerformanceScore
from app.models.route_plan import Route, RouteStop
from app.schemas.driver import DriverCreate, DriverUpdate, DriverResponse


def _enrich(db: Session, tenant_id: str, driver: Driver) -> dict:
    tid = UUID(tenant_id)
    data = DriverResponse.model_validate(driver).model_dump()

    # utilization_pct: today's assigned stops / 10 (assumed max) * 100
    today_stops = db.execute(
        select(func.count(RouteStop.id))
        .join(Route, RouteStop.route_id == Route.id)
        .where(Route.driver_id == driver.id, Route.tenant_id == tid)
    ).scalar_one_or_none() or 0
    data["utilization_pct"] = min(round(today_stops / 10 * 100, 1), 100.0)

    # performance_score: avg on_time_rate from last 30 days * 100
    since = date.today() - timedelta(days=30)
    avg_rate = db.execute(
        select(func.avg(DriverPerformanceScore.on_time_rate))
        .where(
            DriverPerformanceScore.driver_id == driver.id,
            DriverPerformanceScore.tenant_id == tid,
            DriverPerformanceScore.score_date >= since,
        )
    ).scalar_one_or_none()
    data["performance_score"] = round(float(avg_rate) * 100, 1) if avg_rate is not None else None

    return data


def create_driver(db: Session, tenant_id: str, data: DriverCreate) -> Driver:
    obj = Driver(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_driver(db: Session, tenant_id: str, driver_id: UUID) -> Optional[Driver]:
    return db.execute(
        select(Driver).where(Driver.id == driver_id, Driver.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()


def get_driver_enriched(db: Session, tenant_id: str, driver_id: UUID) -> Optional[dict]:
    obj = get_driver(db, tenant_id, driver_id)
    return _enrich(db, tenant_id, obj) if obj else None


def list_drivers(
    db: Session,
    tenant_id: str,
    active_only: bool = False,
    depot_id: Optional[UUID] = None,
) -> list[Driver]:
    q = select(Driver).where(Driver.tenant_id == UUID(tenant_id))
    if active_only:
        q = q.where(Driver.is_active == True)
    if depot_id:
        q = q.where(Driver.home_depot_id == depot_id)
    return list(db.execute(q).scalars().all())


def list_drivers_enriched(
    db: Session,
    tenant_id: str,
    active_only: bool = False,
    depot_id: Optional[UUID] = None,
) -> list[dict]:
    drivers = list_drivers(db, tenant_id, active_only, depot_id)
    return [_enrich(db, tenant_id, d) for d in drivers]


def update_driver(db: Session, tenant_id: str, driver_id: UUID, data: DriverUpdate) -> Optional[Driver]:
    obj = get_driver(db, tenant_id, driver_id)
    if not obj:
        return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_driver(db: Session, tenant_id: str, driver_id: UUID) -> bool:
    obj = get_driver(db, tenant_id, driver_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
