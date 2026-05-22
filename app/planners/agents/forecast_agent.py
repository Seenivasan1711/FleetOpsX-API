"""
Forecast Agent — AI-1 E1 (refactored from P3-E2 node).

Implements PlanningAgent protocol for the unified runner (Phase 1, parallel).
Also keeps _node_forecast() for any remaining LangGraph graph references.

Queries DeliveryAnalytics for the same day-of-week over the last 4 weeks
to produce demand and risk forecasts.

Output structure:
  {
    "expected_order_count": int,
    "recommended_driver_count": int,
    "zones": [{"zone": str, "expected_orders": int, "on_time_rate": float|None}],
    "high_risk_zones": [str],
    "summary": str,
  }
"""
from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.planners.context import AgentContext, AgentResult

if TYPE_CHECKING:
    from app.planners.orchestrator import AgentState

logger = logging.getLogger(__name__)

_HIGH_RISK_THRESHOLD = 0.75
_ORDERS_PER_DRIVER = 12


# ─── PlanningAgent implementation ─────────────────────────────────────────────

class ForecastAgent:
    name = "ForecastAgent"
    phase = 1
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        try:
            forecast = _compute_forecast(
                db=ctx["db"],
                tenant_id=ctx["tenant_id"],
                plan_date=ctx["plan_date"],
            )
            ctx["forecast"] = forecast
            elapsed = int((time.monotonic() - t0) * 1000)
            log_entry = {"step": self.name, "role": "agent", "content": forecast.get("summary", "")}
            ctx["logs"].append(log_entry)
            return AgentResult(
                agent_name=self.name,
                status="completed",
                output=forecast,
                warnings=[],
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.exception("%s failed: %s", self.name, exc)
            log_entry = {"step": self.name, "role": "agent", "content": f"ERROR: {exc}"}
            ctx["logs"].append(log_entry)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                output={},
                warnings=[str(exc)],
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )


# ─── Core forecast logic ──────────────────────────────────────────────────────

def _compute_forecast(*, db: Any, tenant_id: str, plan_date: Any) -> dict:
    """Shared forecast logic used by both the PlanningAgent and the legacy LangGraph node."""
    from uuid import UUID
    from app.models.analytics import DeliveryAnalytics

    tid = UUID(tenant_id)
    target_dow = plan_date.weekday()
    cutoff = plan_date - timedelta(weeks=4)

    rows = db.execute(
        select(DeliveryAnalytics).where(
            DeliveryAnalytics.tenant_id == tid,
            DeliveryAnalytics.day_of_week == target_dow,
            DeliveryAnalytics.delivery_date >= cutoff,
            DeliveryAnalytics.delivery_date < plan_date,
        )
    ).scalars().all()

    if not rows:
        return {
            "expected_order_count": 0,
            "recommended_driver_count": 0,
            "zones": [],
            "high_risk_zones": [],
            "summary": "No historical data available for this day-of-week — using live order count only.",
        }

    zone_totals: dict[str, list[int]] = defaultdict(list)
    zone_counts: dict[str, int] = defaultdict(int)

    for r in rows:
        z = r.zone or "Unknown"
        zone_counts[z] += 1
        zone_totals[z].append(1 if r.was_on_time else 0)

    distinct_dates = len({r.delivery_date for r in rows})
    expected_orders = round(len(rows) / max(distinct_dates, 1))

    zone_stats = []
    high_risk_zones = []
    for zone, on_times in zone_totals.items():
        zone_total = zone_counts[zone]
        expected_zone = round(zone_total / max(distinct_dates, 1))
        on_time_rate = round(sum(on_times) / len(on_times), 4) if on_times else None
        zone_stats.append({"zone": zone, "expected_orders": expected_zone, "on_time_rate": on_time_rate})
        if on_time_rate is not None and on_time_rate < _HIGH_RISK_THRESHOLD:
            high_risk_zones.append(zone)

    zone_stats.sort(key=lambda x: x["expected_orders"], reverse=True)
    recommended_drivers = math.ceil(expected_orders / _ORDERS_PER_DRIVER)
    risk_str = f" High-risk zones: {', '.join(high_risk_zones)}." if high_risk_zones else ""

    return {
        "expected_order_count": expected_orders,
        "recommended_driver_count": recommended_drivers,
        "zones": zone_stats,
        "high_risk_zones": high_risk_zones,
        "summary": (
            f"Historical forecast ({distinct_dates} days sampled): "
            f"~{expected_orders} orders expected, "
            f"{recommended_drivers} drivers recommended.{risk_str}"
        ),
    }


# ─── Legacy LangGraph node (kept for backward compatibility) ──────────────────

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
