"""
Tracking endpoints — P2-E4

POST /tracking/ping            — driver sends GPS position (driver role)
GET  /tracking/live            — dispatcher sees all active driver positions
GET  /tracking/history/{driver_id} — dispatcher reads full ping history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import get_db, require_dispatcher, require_driver
from app.models.driver import Driver
from app.schemas.tracking import LivePositionOut, PingIn, PingOut
from app.services.tracking_service import (
    get_live_positions,
    get_ping_history,
    record_ping,
)

router = APIRouter(prefix="/tracking", tags=["Tracking"])


def _resolve_driver(db: Session, current_user) -> Driver:
    """Look up Driver record by email — same pattern as /driver/my-stops."""
    driver = db.execute(
        select(Driver).where(
            Driver.email == current_user.email,
            Driver.tenant_id == current_user.tenant_id,
        )
    ).scalars().first()
    if not driver:
        raise HTTPException(404, "No driver record linked to this account")
    return driver


@router.post("/ping", response_model=PingOut, status_code=201)
def ping_location(
    body: PingIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_driver),
):
    """Driver app posts GPS position every 30 s."""
    driver = _resolve_driver(db, current_user)
    ping = record_ping(
        db=db,
        tenant_id=str(current_user.tenant_id),
        driver_id=str(driver.id),
        lat=body.latitude,
        lng=body.longitude,
        accuracy=body.accuracy_m,
        speed=body.speed_kmh,
        heading=body.heading_deg,
        vehicle_id=str(body.vehicle_id) if body.vehicle_id else None,
    )
    return ping


@router.get("/live", response_model=list[LivePositionOut])
def live_positions(
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return latest cached position for every active driver in tenant."""
    return get_live_positions(db=db, tenant_id=str(current_user.tenant_id))


@router.get("/history/{driver_id}", response_model=list[PingOut])
def ping_history(
    driver_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return chronological ping history for a single driver."""
    return get_ping_history(
        db=db,
        tenant_id=str(current_user.tenant_id),
        driver_id=str(driver_id),
        limit=limit,
    )
