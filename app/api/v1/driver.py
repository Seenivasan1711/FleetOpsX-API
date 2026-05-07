from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db, get_current_user
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

    # Find routes for this driver
    routes = db.execute(
        select(Route).where(
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

    stops.sort(key=lambda s: s["sequence"])

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

    stop = db.execute(
        select(RouteStop).where(
            RouteStop.id == UUID(stop_id),
            RouteStop.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not stop:
        raise HTTPException(404, "Stop not found")

    stop.status = new_status
    order = db.get(Order, stop.order_id)
    if new_status == "DELIVERED":
        if order:
            order.status = "DELIVERED"
    elif new_status == "FAILED":
        if order:
            order.status = "FAILED"

    db.commit()

    # Dispatch webhook event for partner integrations (P4-E2)
    if new_status in ("DELIVERED", "FAILED") and order:
        try:
            from app.integrations.webhook_service import dispatch_event
            event_type = "order.delivered" if new_status == "DELIVERED" else "order.failed"
            dispatch_event(
                event_type=event_type,
                payload={
                    "order_id":  str(order.id),
                    "stop_id":   stop_id,
                    "status":    new_status,
                    "address":   order.delivery_address,
                },
                db=db,
                tenant_id=str(current_user.tenant_id),
            )
        except Exception:
            pass  # webhook dispatch failure must never break the driver endpoint

    return {"stop_id": stop_id, "status": new_status, "message": "Status updated"}
