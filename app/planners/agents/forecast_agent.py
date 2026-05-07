"""
Forecast Agent node — P3-E2

Queries DeliveryAnalytics for the same day-of-week over the last 4 weeks
to produce demand and risk forecasts used by the Planner Agent.

Output added to state["forecast"]:
  {
    "expected_order_count": int,
    "recommended_driver_count": int,
    "zones": [{"zone": str, "expected_orders": int, "on_time_rate": float|None}],
    "high_risk_zones": [str],         # zones with on_time_rate < 0.75
    "summary": str,                   # human-readable one-liner
  }
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

if TYPE_CHECKING:
    from app.planners.orchestrator import AgentState

logger = logging.getLogger(__name__)

_HIGH_RISK_THRESHOLD = 0.75
_ORDERS_PER_DRIVER = 12


def _node_forecast(state: AgentState) -> AgentState:
    db = state["db"]
    tenant_id = state["tenant_id"]
    plan_date = state["plan_date"]

    from uuid import UUID
    from app.models.analytics import DeliveryAnalytics

    tid = UUID(tenant_id)
    target_dow = plan_date.weekday()  # 0=Mon … 6=Sun

    # Query last 4 occurrences of same day-of-week
    cutoff = plan_date - timedelta(weeks=4)
    rows = db.execute(
        select(DeliveryAnalytics).where(
            DeliveryAnalytics.tenant_id == tid,
            DeliveryAnalytics.day_of_week == target_dow,
            DeliveryAnalytics.delivery_date >= cutoff,
            DeliveryAnalytics.delivery_date < plan_date,
        )
    ).scalars().all()

    forecast: dict[str, Any]

    if not rows:
        # No historical data yet — return neutral forecast
        forecast = {
            "expected_order_count": 0,
            "recommended_driver_count": 0,
            "zones": [],
            "high_risk_zones": [],
            "summary": "No historical data available for this day-of-week — using live order count only.",
        }
        log_content = "Forecast: no historical data for day-of-week baseline."
    else:
        # Aggregate by zone
        zone_totals: dict[str, list[int]] = defaultdict(list)     # zone → [was_on_time]
        zone_counts: dict[str, int] = defaultdict(int)

        for r in rows:
            z = r.zone or "Unknown"
            zone_counts[z] += 1
            zone_totals[z].append(1 if r.was_on_time else 0)

        total_deliveries = len(rows)
        distinct_dates = len({r.delivery_date for r in rows})
        expected_orders = round(total_deliveries / max(distinct_dates, 1))

        zone_stats = []
        high_risk_zones = []

        for zone, on_times in zone_totals.items():
            zone_total = zone_counts[zone]
            expected_zone = round(zone_total / max(distinct_dates, 1))
            on_time_rate = round(sum(on_times) / len(on_times), 4) if on_times else None
            zone_stats.append({
                "zone": zone,
                "expected_orders": expected_zone,
                "on_time_rate": on_time_rate,
            })
            if on_time_rate is not None and on_time_rate < _HIGH_RISK_THRESHOLD:
                high_risk_zones.append(zone)

        zone_stats.sort(key=lambda x: x["expected_orders"], reverse=True)
        recommended_drivers = math.ceil(expected_orders / _ORDERS_PER_DRIVER)

        risk_str = f" High-risk zones: {', '.join(high_risk_zones)}." if high_risk_zones else ""
        summary = (
            f"Historical forecast ({distinct_dates} days sampled): "
            f"~{expected_orders} orders expected, "
            f"{recommended_drivers} drivers recommended.{risk_str}"
        )

        forecast = {
            "expected_order_count": expected_orders,
            "recommended_driver_count": recommended_drivers,
            "zones": zone_stats,
            "high_risk_zones": high_risk_zones,
            "summary": summary,
        }
        log_content = summary

    log = {"step": "forecast", "role": "agent", "content": log_content}
    return {**state, "forecast": forecast, "logs": state["logs"] + [log]}
