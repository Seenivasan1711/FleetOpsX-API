"""
P5-E7: Public customer tracking portal.

GET  /public/track/{token}       — public: returns order status + driver position
POST /orders/{order_id}/tracking-token — dispatcher: generate/return tracking token
"""
from uuid import UUID, uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.order import Order

router = APIRouter(tags=["Public Tracking"])


class TrackingOut(BaseModel):
    order_id:         str
    external_ref:     Optional[str]
    delivery_address: str
    status:           str
    driver_name:      Optional[str]
    driver_lat:       Optional[float]
    driver_lng:       Optional[float]
    time_window_start: Optional[str]
    time_window_end:   Optional[str]
    eta_minutes:      Optional[int]

    class Config:
        from_attributes = True


class TrackingTokenOut(BaseModel):
    tracking_token: str
    tracking_url:   str


@router.get("/public/track/{token}", response_model=TrackingOut)
def public_track(token: str, db: Session = Depends(get_db)):
    """No authentication — public customer tracking by token."""
    try:
        token_uuid = UUID(token)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid tracking link")

    order = db.execute(
        select(Order).where(Order.tracking_token == token_uuid)
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Tracking link not found or expired")

    driver_name = None
    driver_lat  = None
    driver_lng  = None
    eta_minutes = None

    if order.assigned_driver_id:
        from app.models.driver import Driver
        driver = db.get(Driver, order.assigned_driver_id)
        if driver:
            driver_name = driver.full_name

        # Latest GPS ping
        from app.models.tracking import DriverLocationPing
        from sqlalchemy import desc
        ping = db.execute(
            select(DriverLocationPing)
            .where(DriverLocationPing.driver_id == order.assigned_driver_id)
            .order_by(desc(DriverLocationPing.recorded_at))
            .limit(1)
        ).scalar_one_or_none()
        if ping:
            driver_lat  = ping.latitude
            driver_lng  = ping.longitude

        # Rough ETA from route stop sequence position
        if order.route_stop:
            eta_minutes = max(order.route_stop.sequence * 12, 5) if order.status not in ('DELIVERED', 'FAILED') else None

    return TrackingOut(
        order_id=str(order.id),
        external_ref=order.external_ref,
        delivery_address=order.delivery_address,
        status=order.status,
        driver_name=driver_name,
        driver_lat=driver_lat,
        driver_lng=driver_lng,
        time_window_start=str(order.time_window_start) if order.time_window_start else None,
        time_window_end=str(order.time_window_end)   if order.time_window_end   else None,
        eta_minutes=eta_minutes,
    )


@router.post("/orders/{order_id}/tracking-token", response_model=TrackingTokenOut)
def get_or_create_tracking_token(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
    base_url: str = "https://fleetopsx.example.com",
):
    """Generate (or return existing) public tracking token for an order."""
    order = db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.tracking_token:
        order.tracking_token = uuid4()
        db.commit()

    token_str = str(order.tracking_token)
    return TrackingTokenOut(
        tracking_token=token_str,
        tracking_url=f"{base_url}/track/{token_str}",
    )
