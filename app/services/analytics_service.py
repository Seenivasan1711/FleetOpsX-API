"""
Analytics Service — P3-E1

run_etl(): idempotent ETL from operational tables → delivery_analytics + driver_performance_scores
get_kpis(): aggregate KPI query for date range
get_driver_performance(): per-driver aggregate for date range
"""
import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.analytics import DeliveryAnalytics, DriverPerformanceScore
from app.models.driver import Driver
from app.models.order import Order
from app.models.route_plan import Route, RoutePlan, RouteStop, DeliveryEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_zone(address: str | None) -> str:
    """Return first comma-separated token of the address as the zone label."""
    if not address:
        return "Unknown"
    return address.split(",")[0].strip()


def _time_str_to_datetime(base_date: date, time_str: str | None) -> datetime | None:
    """Parse 'HH:MM:SS' or 'HH:MM' into a datetime on base_date."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        h, m = int(parts[0]), int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        return datetime(base_date.year, base_date.month, base_date.day, h, m, s)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ETL
# ---------------------------------------------------------------------------

def run_etl(db: Session, tenant_id: str, etl_date: date) -> dict[str, int]:
    """
    Read all DELIVERED route stops for etl_date and upsert analytics rows.

    Returns {"upserted": N, "driver_scores_upserted": M}
    """
    tid = UUID(tenant_id)

    # 1. Find all DELIVERED route_stops for the given date (via route_plan.plan_date)
    rows = db.execute(
        select(RouteStop, Route, RoutePlan, Order)
        .join(Route, RouteStop.route_id == Route.id)
        .join(RoutePlan, Route.plan_id == RoutePlan.id)
        .join(Order, RouteStop.order_id == Order.id)
        .where(
            RouteStop.tenant_id == tid,
            RoutePlan.plan_date == etl_date,
            RouteStop.status == "DELIVERED",
        )
    ).all()

    if not rows:
        logger.info("ETL[%s][%s]: no DELIVERED stops found", tenant_id[:8], etl_date)
        return {"upserted": 0, "driver_scores_upserted": 0}

    # Build a lookup of DELIVERED events keyed by route_stop_id
    stop_ids = [str(rs.id) for rs, _, _, _ in rows]
    events = db.execute(
        select(DeliveryEvent)
        .where(
            DeliveryEvent.tenant_id == tid,
            DeliveryEvent.route_stop_id.in_([UUID(s) for s in stop_ids]),
            DeliveryEvent.event_type == "DELIVERED",
        )
    ).scalars().all()
    event_by_stop: dict[str, DeliveryEvent] = {str(e.route_stop_id): e for e in events}

    # 2. Delete existing analytics rows for these order_ids (idempotent upsert = delete + insert)
    order_ids = [rs_order.id for _, _, _, rs_order in rows]
    db.execute(
        delete(DeliveryAnalytics).where(
            DeliveryAnalytics.tenant_id == tid,
            DeliveryAnalytics.order_id.in_(order_ids),
        )
    )

    # 3. Build and insert DeliveryAnalytics rows
    analytics_rows: list[DeliveryAnalytics] = []
    driver_deliveries: dict[str, list[dict]] = defaultdict(list)

    for stop, route, plan, order in rows:
        event = event_by_stop.get(str(stop.id))
        actual_arrival: datetime | None = event.created_at if event else None

        # Compute delay
        planned_dt = _time_str_to_datetime(etl_date, str(order.time_window_end) if order.time_window_end else None)
        delay_minutes: int | None = None
        was_on_time: bool | None = None

        if planned_dt and actual_arrival:
            diff = (actual_arrival - planned_dt).total_seconds() / 60
            delay_minutes = max(0, math.floor(diff))
            was_on_time = delay_minutes == 0
        elif planned_dt is None:
            # No time window — treat as on-time for metrics
            was_on_time = True
            delay_minutes = 0

        row = DeliveryAnalytics(
            tenant_id=tid,
            order_id=order.id,
            driver_id=route.driver_id,
            route_plan_id=plan.id,
            delivery_date=etl_date,
            day_of_week=etl_date.weekday(),
            hour_of_day=actual_arrival.hour if actual_arrival else None,
            zone=_extract_zone(order.delivery_address),
            planned_eta=str(order.time_window_end) if order.time_window_end else None,
            actual_arrival=actual_arrival,
            delay_minutes=delay_minutes,
            was_on_time=was_on_time,
            priority=order.priority,
        )
        analytics_rows.append(row)

        if route.driver_id:
            driver_deliveries[str(route.driver_id)].append({
                "delay_minutes": delay_minutes or 0,
                "was_on_time": was_on_time if was_on_time is not None else True,
            })

    db.add_all(analytics_rows)

    # 4. Upsert DriverPerformanceScore rows
    dps_upserted = 0
    for driver_id_str, deliveries in driver_deliveries.items():
        driver_uuid = UUID(driver_id_str)
        total = len(deliveries)
        on_time = sum(1 for d in deliveries if d["was_on_time"])
        delayed = [d["delay_minutes"] for d in deliveries if d["delay_minutes"] > 0]
        avg_delay = sum(delayed) / len(delayed) if delayed else None
        total_delay = sum(delayed)

        # Delete existing score for this driver+date
        db.execute(
            delete(DriverPerformanceScore).where(
                DriverPerformanceScore.tenant_id == tid,
                DriverPerformanceScore.driver_id == driver_uuid,
                DriverPerformanceScore.score_date == etl_date,
            )
        )
        dps = DriverPerformanceScore(
            tenant_id=tid,
            driver_id=driver_uuid,
            score_date=etl_date,
            total_deliveries=total,
            on_time_count=on_time,
            on_time_rate=round(on_time / total, 4) if total > 0 else None,
            avg_delay_min=round(avg_delay, 2) if avg_delay is not None else None,
            total_delay_min=total_delay,
        )
        db.add(dps)
        dps_upserted += 1

    db.commit()
    logger.info("ETL[%s][%s]: upserted %d delivery rows, %d driver scores",
                tenant_id[:8], etl_date, len(analytics_rows), dps_upserted)
    return {"upserted": len(analytics_rows), "driver_scores_upserted": dps_upserted}


# ---------------------------------------------------------------------------
# KPI Aggregation
# ---------------------------------------------------------------------------

def get_kpis(db: Session, tenant_id: str, since: date, until: date) -> dict[str, Any]:
    """Aggregate delivery KPIs for a date range."""
    tid = UUID(tenant_id)

    rows = db.execute(
        select(DeliveryAnalytics)
        .where(
            DeliveryAnalytics.tenant_id == tid,
            DeliveryAnalytics.delivery_date >= since,
            DeliveryAnalytics.delivery_date <= until,
        )
    ).scalars().all()

    if not rows:
        return {
            "period": {"since": str(since), "until": str(until)},
            "total_deliveries": 0,
            "on_time_rate": None,
            "avg_delay_minutes": None,
            "deliveries_by_day": [],
            "deliveries_by_zone": [],
        }

    total = len(rows)
    on_time_rows = [r for r in rows if r.was_on_time is True]
    on_time_rate = round(len(on_time_rows) / total, 4) if total > 0 else None

    delayed = [r.delay_minutes for r in rows if r.delay_minutes and r.delay_minutes > 0]
    avg_delay = round(sum(delayed) / len(delayed), 2) if delayed else None

    # Group by date
    by_day: dict[str, dict] = {}
    for r in rows:
        key = str(r.delivery_date)
        if key not in by_day:
            by_day[key] = {"date": key, "total": 0, "on_time": 0}
        by_day[key]["total"] += 1
        if r.was_on_time:
            by_day[key]["on_time"] += 1

    # Group by zone
    by_zone: dict[str, dict] = {}
    for r in rows:
        z = r.zone or "Unknown"
        if z not in by_zone:
            by_zone[z] = {"zone": z, "total": 0, "on_time": 0}
        by_zone[z]["total"] += 1
        if r.was_on_time:
            by_zone[z]["on_time"] += 1

    zone_list = []
    for v in by_zone.values():
        v["on_time_rate"] = round(v["on_time"] / v["total"], 4) if v["total"] > 0 else None
        zone_list.append(v)
    zone_list.sort(key=lambda x: x["total"], reverse=True)

    return {
        "period": {"since": str(since), "until": str(until)},
        "total_deliveries": total,
        "on_time_rate": on_time_rate,
        "avg_delay_minutes": avg_delay,
        "deliveries_by_day": sorted(by_day.values(), key=lambda x: x["date"]),
        "deliveries_by_zone": zone_list,
    }


# ---------------------------------------------------------------------------
# Driver Performance
# ---------------------------------------------------------------------------

def get_driver_performance(db: Session, tenant_id: str, since: date) -> list[dict[str, Any]]:
    """Return per-driver aggregated performance since a given date."""
    tid = UUID(tenant_id)

    rows = db.execute(
        select(DriverPerformanceScore, Driver)
        .join(Driver, DriverPerformanceScore.driver_id == Driver.id)
        .where(
            DriverPerformanceScore.tenant_id == tid,
            DriverPerformanceScore.score_date >= since,
        )
    ).all()

    if not rows:
        return []

    # Aggregate across multiple dates per driver
    agg: dict[str, dict] = {}
    for score, driver in rows:
        key = str(score.driver_id)
        if key not in agg:
            agg[key] = {
                "driver_id": key,
                "driver_name": driver.full_name,
                "total_deliveries": 0,
                "on_time_count": 0,
                "_delays": [],
            }
        agg[key]["total_deliveries"] += score.total_deliveries
        agg[key]["on_time_count"] += score.on_time_count
        if score.avg_delay_min is not None and score.avg_delay_min > 0:
            # weight average delay by number of delayed deliveries
            delayed_count = score.total_deliveries - score.on_time_count
            agg[key]["_delays"].extend([score.avg_delay_min] * delayed_count)

    result = []
    for v in agg.values():
        total = v["total_deliveries"]
        on_time = v["on_time_count"]
        delays = v["_delays"]
        result.append({
            "driver_id": v["driver_id"],
            "driver_name": v["driver_name"],
            "total_deliveries": total,
            "on_time_rate": round(on_time / total, 4) if total > 0 else None,
            "avg_delay_minutes": round(sum(delays) / len(delays), 2) if delays else None,
        })

    result.sort(key=lambda x: (x["on_time_rate"] or 0), reverse=True)
    return result


# ---------------------------------------------------------------------------
# KPI Trend (Phase 6 — sparklines)
# ---------------------------------------------------------------------------

def get_kpi_trend(db: Session, tenant_id: str, days: int = 7) -> list[dict[str, Any]]:
    """Return per-day KPI values for the last N days (for dashboard sparklines)."""
    tid = UUID(tenant_id)
    today = date.today()
    since = today - timedelta(days=days - 1)

    rows = db.execute(
        select(DeliveryAnalytics)
        .where(
            DeliveryAnalytics.tenant_id == tid,
            DeliveryAnalytics.delivery_date >= since,
            DeliveryAnalytics.delivery_date <= today,
        )
    ).scalars().all()

    # Build per-date buckets
    buckets: dict[str, dict] = {}
    for d in range(days):
        day = since + timedelta(days=d)
        buckets[str(day)] = {
            "date": str(day),
            "orders_count": 0,
            "on_time_count": 0,
            "driver_ids": set(),
        }

    for r in rows:
        key = str(r.delivery_date)
        if key not in buckets:
            continue
        buckets[key]["orders_count"] += 1
        if r.was_on_time:
            buckets[key]["on_time_count"] += 1
        if r.driver_id:
            buckets[key]["driver_ids"].add(str(r.driver_id))

    result = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        total = b["orders_count"]
        on_time = b["on_time_count"]
        active_drivers = len(b["driver_ids"])
        on_time_pct = round(on_time / total * 100, 1) if total > 0 else None
        fleet_efficiency = on_time_pct  # simplified: efficiency = on-time %
        result.append({
            "date": key,
            "orders_count": total,
            "on_time_pct": on_time_pct,
            "active_drivers": active_drivers,
            "fleet_efficiency": fleet_efficiency,
        })

    return result
