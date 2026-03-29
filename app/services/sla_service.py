"""
SLA Risk Service — P2-E7

A stop is AT RISK when:
  current_time + estimated_travel_minutes > time_window_end

Travel time is estimated from the driver's last Redis-cached GPS position
to the order's delivery coordinates at AVG_SPEED_KMH.

Returns an empty list when no stops are at risk or when no GPS data is available
(so the dashboard is never noisy on day-1 before drivers start pinging).
"""
import json
import math
from datetime import datetime, date, time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_redis
from app.models.driver import Driver
from app.models.order import Order
from app.models.route_plan import Route, RoutePlan, RouteStop

AVG_SPEED_KMH = 30
_AT_RISK_STATUSES = {"PENDING", "IN_TRANSIT"}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _travel_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    km = _haversine_km(lat1, lng1, lat2, lng2)
    return (km / AVG_SPEED_KMH) * 60


def _time_to_minutes(t: time | None) -> int | None:
    if t is None:
        return None
    return t.hour * 60 + t.minute


def get_at_risk_stops(db: Session, tenant_id: str, plan_date: date) -> list[dict[str, Any]]:
    """Return at-risk stops for the given plan date and tenant."""
    tid = UUID(tenant_id)
    redis = get_redis()

    # Fetch all PENDING/IN_TRANSIT stops for this tenant + date
    rows = db.execute(
        select(RouteStop, Route, Order, Driver)
        .join(Route, RouteStop.route_id == Route.id)
        .join(RoutePlan, Route.plan_id == RoutePlan.id)
        .join(Order, RouteStop.order_id == Order.id)
        .join(Driver, Route.driver_id == Driver.id)
        .where(
            RouteStop.tenant_id == tid,
            RoutePlan.plan_date == plan_date,
            RouteStop.status.in_(_AT_RISK_STATUSES),
        )
    ).all()

    now_minutes = datetime.utcnow().hour * 60 + datetime.utcnow().minute
    at_risk: list[dict] = []

    for stop, route, order, driver in rows:
        # Skip stops without a time window end
        if order.time_window_end is None:
            continue

        tw_end_minutes = _time_to_minutes(order.time_window_end)

        # Get driver's last cached position from Redis
        raw = redis.get(f"driver:{driver.id}:location")
        if raw is None:
            continue  # no ping yet — can't assess risk

        pos = json.loads(raw)
        driver_lat = pos["latitude"]
        driver_lng = pos["longitude"]

        # Skip stops without delivery coordinates
        if order.delivery_latitude is None or order.delivery_longitude is None:
            continue

        travel_min = _travel_minutes(
            driver_lat, driver_lng,
            order.delivery_latitude, order.delivery_longitude,
        )
        eta_minutes = now_minutes + travel_min

        if eta_minutes > tw_end_minutes:
            at_risk.append({
                "stop_id": str(stop.id),
                "order_id": str(order.id),
                "driver_id": str(driver.id),
                "driver_name": driver.full_name,
                "delivery_address": order.delivery_address,
                "time_window_end": str(order.time_window_end),
                "eta_minutes": round(eta_minutes),
                "overdue_by_minutes": round(eta_minutes - tw_end_minutes),
                "stop_status": stop.status,
                "priority": order.priority,
            })

    # Sort by most overdue first
    at_risk.sort(key=lambda x: x["overdue_by_minutes"], reverse=True)
    return at_risk
