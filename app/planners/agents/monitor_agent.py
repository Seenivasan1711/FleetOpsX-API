"""
Monitor Agent — P3-E2

Standalone background function called by APScheduler every 5 min (07:00–20:00).
Scans active PENDING/IN_TRANSIT stops and creates AgentSuggestion rows when
a driver is likely to miss a time window.

Does NOT run inside the LangGraph plan_day graph — intentionally separate so
monitoring and planning are independently testable.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_redis
from app.models.agent_suggestion import AgentSuggestion
from app.models.driver import Driver
from app.models.order import Order
from app.models.route_plan import Route, RoutePlan, RouteStop

logger = logging.getLogger(__name__)

AVG_SPEED_KMH = 30
WARN_BEFORE_MINUTES = 30
_ACTIVE_STATUSES = {"PENDING", "IN_TRANSIT"}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _travel_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return (_haversine_km(lat1, lng1, lat2, lng2) / AVG_SPEED_KMH) * 60


def run_monitor_scan(db: Session, tenant_id: str, plan_date: date) -> int:
    """
    Scan active stops for the given plan_date and create EARLY_SLA_WARNING
    AgentSuggestion rows where the driver is likely to miss the time window.

    Returns the number of new suggestions created.
    """
    tid = UUID(tenant_id)
    redis = get_redis()
    now = datetime.utcnow()
    now_minutes = now.hour * 60 + now.minute
    created = 0

    # Fetch all active stops with a time window for this date
    rows = db.execute(
        select(RouteStop, Route, Order, Driver)
        .join(Route, RouteStop.route_id == Route.id)
        .join(RoutePlan, Route.plan_id == RoutePlan.id)
        .join(Order, RouteStop.order_id == Order.id)
        .join(Driver, Route.driver_id == Driver.id)
        .where(
            RouteStop.tenant_id == tid,
            RoutePlan.plan_date == plan_date,
            RouteStop.status.in_(_ACTIVE_STATUSES),
            Order.time_window_end.isnot(None),
        )
    ).all()

    for stop, route, order, driver in rows:
        # Get driver's last GPS ping from Redis
        raw = redis.get(f"driver:{driver.id}:location")
        if raw is None:
            continue

        pos = json.loads(raw)
        driver_lat = pos.get("latitude")
        driver_lng = pos.get("longitude")
        if driver_lat is None or driver_lng is None:
            continue

        if order.delivery_latitude is None or order.delivery_longitude is None:
            continue

        travel_min = _travel_minutes(
            driver_lat, driver_lng,
            order.delivery_latitude, order.delivery_longitude,
        )
        eta_minutes = now_minutes + travel_min
        tw_end = order.time_window_end
        tw_end_minutes = tw_end.hour * 60 + tw_end.minute

        # Fire warning if ETA > window_end - WARN_BEFORE_MINUTES
        if eta_minutes <= tw_end_minutes - WARN_BEFORE_MINUTES:
            continue

        # Check if a PENDING suggestion already exists for this stop
        existing = db.execute(
            select(AgentSuggestion).where(
                AgentSuggestion.tenant_id == tid,
                AgentSuggestion.status == "PENDING",
                AgentSuggestion.suggestion_type == "EARLY_SLA_WARNING",
                AgentSuggestion.plan_date == plan_date,
            )
        ).scalars().all()

        existing_stop_ids = {
            str(s.context.get("stop_id"))
            for s in existing
            if s.context and s.context.get("stop_id")
        }
        if str(stop.id) in existing_stop_ids:
            continue

        overdue_by = round(eta_minutes - tw_end_minutes)
        expires_at = now + timedelta(minutes=30)

        suggestion = AgentSuggestion(
            tenant_id=tid,
            plan_date=plan_date,
            suggestion_type="EARLY_SLA_WARNING",
            status="PENDING",
            priority="HIGH" if overdue_by > 15 else "NORMAL",
            title=f"{driver.full_name} may miss delivery by {str(tw_end)[:5]}",
            detail=(
                f"Driver is ~{round(travel_min)} min from the stop. "
                f"Time window closes at {str(tw_end)[:5]}. "
                f"Estimated arrival is {round(overdue_by)} min late."
            ),
            context={
                "driver_id": str(driver.id),
                "stop_id": str(stop.id),
                "order_id": str(order.id),
                "eta_minutes": round(eta_minutes),
                "tw_end_minutes": tw_end_minutes,
            },
            expires_at=expires_at,
        )
        db.add(suggestion)
        created += 1

    if created:
        db.commit()
        logger.info("Monitor scan [%s][%s]: created %d suggestions", tenant_id[:8], plan_date, created)

    return created
