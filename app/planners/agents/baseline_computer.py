"""
BaselineComputerAgent — Phase 2 (sequential, runs after ORToolsOptimizerAgent).

Computes the naive unoptimized route distance for the same assignments OR-Tools
produced. The "naive" route visits each driver's stops in insertion order (sorted
by order_id — arbitrary but deterministic), instead of the optimized sequence.

  baseline_km  = sum of naive route distances across all drivers
  km_saved     = baseline_km − optimized_km  (always ≥ 0)
  baseline_hrs = baseline_km / AVG_SPEED_KMH
  hrs_saved    = baseline_hrs − optimized_hrs

This gives the dispatcher a concrete measure of AI value:
  "AI saved 340 km and 3.5 hrs vs unoptimized routing."
"""
from __future__ import annotations

import logging
import math
import time
from collections import defaultdict

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)

AVG_SPEED_KMH = 30
_FALLBACK_LAT = 12.9716
_FALLBACK_LNG = 77.5946


class BaselineComputerAgent:
    name = "BaselineComputerAgent"
    phase = 2
    execution = "sequential"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        plan = ctx["plan_result"]

        assignments = plan.get("assignments", [])
        optimized_km = plan.get("total_distance_km", 0.0) or 0.0
        optimized_min = plan.get("est_duration_min", 0) or 0

        if not assignments or optimized_km == 0:
            # Nothing to compare — plan is empty or OR-Tools fallback didn't compute distances
            baseline_result = _zero_baseline()
            ctx["baseline_result"] = baseline_result
            elapsed = int((time.monotonic() - t0) * 1000)
            log_entry = {
                "step": self.name,
                "role": "tool",
                "content": "Baseline skipped — no assignments or no optimized distance.",
            }
            ctx["logs"].append(log_entry)
            return AgentResult(
                agent_name=self.name,
                status="skipped",
                output=baseline_result,
                warnings=[],
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )

        # Build order_id → (lat, lng) lookup from Phase 1 orders
        order_coords: dict[str, tuple[float, float]] = {}
        for o in ctx.get("orders", []):
            lat = getattr(o, "delivery_latitude", None)
            lng = getattr(o, "delivery_longitude", None)
            if lat is not None and lng is not None:
                order_coords[str(o.id)] = (lat, lng)

        # Get depot coordinates from first driver's home depot (same logic as ORToolsPlanner)
        depot_lat, depot_lng = _FALLBACK_LAT, _FALLBACK_LNG
        for d in ctx.get("drivers", []):
            hd = getattr(d, "home_depot", None)
            if hd and getattr(hd, "latitude", None) and getattr(hd, "longitude", None):
                depot_lat = hd.latitude
                depot_lng = hd.longitude
                break

        # Group assignments by driver, sort by order_id for a deterministic naive order
        driver_orders: dict[str, list[str]] = defaultdict(list)
        for a in assignments:
            driver_orders[a["driver_id"]].append(a["order_id"])
        for oid_list in driver_orders.values():
            oid_list.sort()   # deterministic naive insertion order

        # Compute naive total distance
        baseline_km = 0.0
        for oid_list in driver_orders.values():
            baseline_km += _naive_route_km(depot_lat, depot_lng, oid_list, order_coords)

        baseline_km = round(baseline_km, 2)
        baseline_hrs = round(baseline_km / AVG_SPEED_KMH, 2)
        optimized_hrs = round(optimized_min / 60, 2)
        km_saved = round(max(0.0, baseline_km - optimized_km), 2)
        hrs_saved = round(max(0.0, baseline_hrs - optimized_hrs), 2)

        baseline_result = {
            "baseline_km": baseline_km,
            "baseline_hrs": baseline_hrs,
            "km_saved": km_saved,
            "hrs_saved": hrs_saved,
        }
        ctx["baseline_result"] = baseline_result
        elapsed = int((time.monotonic() - t0) * 1000)

        log_entry = {
            "step": self.name,
            "role": "tool",
            "content": (
                f"Naive baseline: {baseline_km} km / {baseline_hrs} hrs. "
                f"OR-Tools: {optimized_km} km / {optimized_hrs} hrs. "
                f"Saved: {km_saved} km, {hrs_saved} hrs ({elapsed}ms)."
            ),
        }
        ctx["logs"].append(log_entry)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output=baseline_result,
            warnings=[],
            elapsed_ms=elapsed,
            log_entry=log_entry,
        )


def _naive_route_km(
    depot_lat: float,
    depot_lng: float,
    order_ids: list[str],
    order_coords: dict[str, tuple[float, float]],
) -> float:
    """
    Distance for a naive sequential route: depot → id[0] → id[1] → ... → depot.
    Orders with no coordinates are skipped.
    """
    total = 0.0
    cur_lat, cur_lng = depot_lat, depot_lng
    for oid in order_ids:
        coords = order_coords.get(oid)
        if coords is None:
            continue
        lat, lng = coords
        total += _haversine_km(cur_lat, cur_lng, lat, lng)
        cur_lat, cur_lng = lat, lng
    total += _haversine_km(cur_lat, cur_lng, depot_lat, depot_lng)
    return total


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _zero_baseline() -> dict:
    return {"baseline_km": 0.0, "baseline_hrs": 0.0, "km_saved": None, "hrs_saved": None}
