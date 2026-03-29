"""
Tracking service — P2-E4

record_ping      — write to Postgres + cache latest position in Redis
get_live_positions — read latest positions for all active drivers from Redis
get_ping_history  — read historical pings for a driver from Postgres
"""
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_redis
from app.models.tracking import DriverLocationPing

REDIS_TTL_SECONDS = 3600  # 1 hour


def record_ping(
    db: Session,
    tenant_id: str,
    driver_id: str,
    lat: float,
    lng: float,
    accuracy: Optional[float] = None,
    speed: Optional[float] = None,
    heading: Optional[float] = None,
    vehicle_id: Optional[str] = None,
) -> DriverLocationPing:
    ping = DriverLocationPing(
        tenant_id=UUID(tenant_id),
        driver_id=UUID(driver_id),
        vehicle_id=UUID(vehicle_id) if vehicle_id else None,
        latitude=lat,
        longitude=lng,
        accuracy_m=accuracy,
        speed_kmh=speed,
        heading_deg=heading,
        recorded_at=datetime.utcnow(),
    )
    db.add(ping)
    db.commit()
    db.refresh(ping)

    # Cache latest position in Redis
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
    """Return latest position for every active driver in the tenant (from Redis)."""
    from app.models.driver import Driver

    drivers = db.execute(
        select(Driver).where(
            Driver.tenant_id == UUID(tenant_id),
            Driver.is_active == True,
        )
    ).scalars().all()

    redis = get_redis()
    positions = []
    for driver in drivers:
        raw = redis.get(f"driver:{driver.id}:location")
        if raw:
            pos = json.loads(raw)
            pos["driver_name"] = driver.full_name
            positions.append(pos)
    return positions


def get_ping_history(
    db: Session,
    tenant_id: str,
    driver_id: str,
    limit: int = 100,
) -> list[DriverLocationPing]:
    return db.execute(
        select(DriverLocationPing)
        .where(
            DriverLocationPing.tenant_id == UUID(tenant_id),
            DriverLocationPing.driver_id == UUID(driver_id),
        )
        .order_by(DriverLocationPing.recorded_at.desc())
        .limit(limit)
    ).scalars().all()
