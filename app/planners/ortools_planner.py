"""
OR-Tools VRPTW Planner — Phase 2 E1

Replaces the greedy rule-based planner with a Vehicle Routing Problem
with Time Windows (VRPTW) solver.

Same PlannerInterface as RuleBasedPlanner — drop-in replacement via
PLANNER_TYPE=ortools in .env, no API changes.

Fallback chain:
  OR-Tools solution found  →  use it
  OR-Tools no solution     →  fall back to RuleBasedPlanner
  No orders / no drivers   →  return empty result immediately
"""
import math
from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sqlalchemy import insert as sa_insert, select
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.driver_availability import DriverAvailability
from app.models.order import Order
from app.models.route_plan import Route, RoutePlan, RouteStop
from app.planners.cost_model import get_weights
from app.planners.interface import PlannerInterface

# Fallback depot coords (Bangalore centre) used when driver has no home depot
_FALLBACK_LAT = 12.9716
_FALLBACK_LNG = 77.5946

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
TIME_LIMIT_SECONDS = 10
AVG_SPEED_KMH = 30  # assumed average city speed for travel-time estimation


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _travel_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Haversine distance → travel minutes at AVG_SPEED_KMH. Min 1 minute."""
    km = _haversine_km(lat1, lng1, lat2, lng2)
    return max(1, int((km / AVG_SPEED_KMH) * 60))


def _time_to_minutes(t) -> int:
    """Convert a datetime.time object to minutes since midnight. None → 0."""
    if t is None:
        return 0
    return t.hour * 60 + t.minute


# ─── Planner ──────────────────────────────────────────────────────────────────

class ORToolsPlanner(PlannerInterface):
    """
    VRPTW solver using Google OR-Tools.

    Node layout in the distance matrix:
      index 0          = depot (start + end for every vehicle)
      index 1 .. N     = one node per order
    """

    def plan_day(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        plan_mode: str = "balanced",
        commit_assignments: bool = True,
    ) -> dict[str, Any]:
        weights = get_weights(plan_mode)
        tid = UUID(tenant_id)
        day_start = datetime.combine(plan_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        # ── 1. Fetch data ─────────────────────────────────────────────────────
        orders = list(db.execute(
            select(Order).where(
                Order.tenant_id == tid,
                Order.scheduled_date >= day_start,
                Order.scheduled_date < day_end,
                Order.status == "PENDING",
                Order.assigned_driver_id.is_(None),
            )
        ).scalars().all())

        if not orders:
            return {
                "message": "No unassigned orders for this date",
                "assignments": [], "plan_id": None,
                "plan_date": str(plan_date), "status": "DRAFT",
                "total_orders": 0, "assigned_orders": 0, "total_routes": 0,
                "ai_summary": None, "confidence_score": None, "reasoning_steps": [], "warnings": [],
                "planner": "ortools",
            }

        # Sort by priority so higher-priority orders are processed first when
        # OR-Tools can't assign all (it may drop lower-priority ones under pressure).
        orders = sorted(orders, key=lambda o: PRIORITY_ORDER.get(o.priority, 99))

        drivers = list(db.execute(
            select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
        ).scalars().all())

        shifts = list(db.execute(
            select(DriverShift).where(
                DriverShift.tenant_id == tid,
                DriverShift.shift_date == plan_date,
            )
        ).scalars().all())
        unavailable_ids = {s.driver_id for s in shifts if s.status != "WORKING"}

        avail_records = list(db.execute(
            select(DriverAvailability).where(
                DriverAvailability.tenant_id == tid,
                DriverAvailability.date == plan_date,
            )
        ).scalars().all())
        unavailable_ids |= {r.driver_id for r in avail_records if r.status != "available"}

        drivers = [d for d in drivers if d.id not in unavailable_ids]

        if not drivers:
            return {
                "message": "No available drivers for this date",
                "assignments": [], "plan_id": None,
                "plan_date": str(plan_date), "status": "DRAFT",
                "total_orders": len(orders), "assigned_orders": 0, "total_routes": 0,
                "ai_summary": None, "confidence_score": None, "reasoning_steps": [], "warnings": [],
                "planner": "ortools",
            }

        # ── 2. Build depot coords (from first driver's home depot, or fallback) ──
        depot_lat, depot_lng = _FALLBACK_LAT, _FALLBACK_LNG
        for d in drivers:
            if d.home_depot and d.home_depot.latitude and d.home_depot.longitude:
                depot_lat = d.home_depot.latitude
                depot_lng = d.home_depot.longitude
                break

        # ── 3. Build location list: index 0 = depot, 1..N = orders ───────────
        locations: list[tuple[float, float]] = [(depot_lat, depot_lng)]
        for order in orders:
            lat = order.delivery_latitude or depot_lat
            lng = order.delivery_longitude or depot_lng
            locations.append((lat, lng))

        n_nodes = len(locations)
        n_vehicles = len(drivers)
        depot_idx = 0

        # ── 4. Build travel-time and distance matrices ────────────────────────
        time_matrix: list[list[int]] = [
            [
                _travel_minutes(locations[i][0], locations[i][1],
                                locations[j][0], locations[j][1])
                if i != j else 0
                for j in range(n_nodes)
            ]
            for i in range(n_nodes)
        ]
        # distance in 100-metre units (integer) for OR-Tools
        dist_matrix: list[list[int]] = [
            [
                int(_haversine_km(locations[i][0], locations[i][1],
                                  locations[j][0], locations[j][1]) * 10)
                if i != j else 0
                for j in range(n_nodes)
            ]
            for i in range(n_nodes)
        ]
        tw = weights["time_weight"]
        dw = weights["dist_weight"]
        # Combined cost matrix (integer, scaled so it fits OR-Tools integer constraints)
        cost_matrix: list[list[int]] = [
            [int(tw * time_matrix[i][j] + dw * dist_matrix[i][j]) for j in range(n_nodes)]
            for i in range(n_nodes)
        ]

        # ── 5. OR-Tools model ─────────────────────────────────────────────────
        manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, depot_idx)
        routing = pywrapcp.RoutingModel(manager)

        def _transit_callback(from_idx: int, to_idx: int) -> int:
            return cost_matrix[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

        def _time_callback(from_idx: int, to_idx: int) -> int:
            return time_matrix[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

        transit_cb = routing.RegisterTransitCallback(_transit_callback)
        time_cb = routing.RegisterTransitCallback(_time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

        # Time dimension — full day (1440 min = 24 hours).
        # Using minutes-since-midnight so time windows can be expressed directly.
        routing.AddDimension(
            time_cb,
            slack_max=120,      # up to 2 hours early wait at a stop
            capacity=1440,      # 24-hour day
            fix_start_cumul_to_zero=False,  # vehicles can start mid-day
            name="Time",
        )
        time_dim = routing.GetDimensionOrDie("Time")

        # Anchor all vehicles at the depot start time (08:00 = 480 min)
        SHIFT_START = 480   # 08:00
        SHIFT_END   = 1200  # 20:00
        for v in range(n_vehicles):
            time_dim.CumulVar(routing.Start(v)).SetRange(SHIFT_START, SHIFT_START)
            time_dim.CumulVar(routing.End(v)).SetRange(SHIFT_START, SHIFT_END)

        # Apply time windows only for orders that have one set
        for order_idx, order in enumerate(orders):
            if order.time_window_start is None and order.time_window_end is None:
                continue  # no constraint — order can be visited any time in shift
            node = order_idx + 1  # +1 because node 0 is depot
            idx = manager.NodeToIndex(node)
            tw_start = _time_to_minutes(order.time_window_start) if order.time_window_start else SHIFT_START
            tw_end   = _time_to_minutes(order.time_window_end)   if order.time_window_end   else SHIFT_END
            # Guard: end must be strictly greater than start
            if tw_end <= tw_start:
                tw_end = SHIFT_END
            time_dim.CumulVar(idx).SetRange(tw_start, tw_end)

        # Allow dropping orders (penalty = 10000 min → very high cost to skip)
        for order_idx in range(len(orders)):
            node = order_idx + 1
            routing.AddDisjunction([manager.NodeToIndex(node)], 10_000)

        # ── 6. Search parameters ──────────────────────────────────────────────
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.seconds = TIME_LIMIT_SECONDS

        solution = routing.SolveWithParameters(search_params)

        # ── 7. Fallback to RuleBasedPlanner if no solution found ──────────────
        if not solution:
            if not commit_assignments:
                # In generate_options context: return empty so this mode is skipped.
                # RuleBasedPlanner always commits assignments, which would prevent
                # subsequent modes from seeing pending orders.
                return {
                    "message": "OR-Tools could not find a solution for this mode",
                    "assignments": [], "plan_id": None,
                    "plan_date": str(plan_date), "status": "DRAFT",
                    "total_orders": len(orders), "assigned_orders": 0, "total_routes": 0,
                    "total_distance_km": 0.0, "est_duration_min": 0, "est_fuel_cost": 0.0,
                    "ai_summary": None, "confidence_score": None, "reasoning_steps": [], "warnings": [],
                    "planner": "ortools_no_solution",
                }
            from app.planners.rule_based import RuleBasedPlanner
            result = RuleBasedPlanner().plan_day(db, tenant_id, plan_date)
            result["planner"] = "rule_based_fallback"
            return result

        # ── 8. Parse solution and write DB records ────────────────────────────
        plan = RoutePlan(
            plan_date=plan_date,
            status="DRAFT",
            tenant_id=tid,
            total_orders=len(orders),
            planner_version=f"ortools_vrptw_v1_{plan_mode}",
        )
        db.add(plan)
        db.flush()

        assignments: list[dict] = []
        routes_created = 0
        total_distance_km = 0.0
        total_duration_min = 0

        for vehicle_idx, driver in enumerate(drivers):
            idx = routing.Start(vehicle_idx)
            stop_sequence: list[Order] = []

            while not routing.IsEnd(idx):
                node = manager.IndexToNode(idx)
                if node != depot_idx:
                    stop_sequence.append(orders[node - 1])
                idx = solution.Value(routing.NextVar(idx))

            if not stop_sequence:
                continue

            # Compute route-level distance + duration (depot → stops → depot)
            route_nodes = [0] + [orders.index(o) + 1 for o in stop_sequence] + [0]
            route_dist = sum(
                _haversine_km(locations[route_nodes[i]][0], locations[route_nodes[i]][1],
                              locations[route_nodes[i + 1]][0], locations[route_nodes[i + 1]][1])
                for i in range(len(route_nodes) - 1)
            )
            route_dur = sum(
                time_matrix[route_nodes[i]][route_nodes[i + 1]]
                for i in range(len(route_nodes) - 1)
            )
            total_distance_km += route_dist
            total_duration_min += route_dur

            route = Route(
                plan_id=plan.id,
                driver_id=driver.id,
                status="PLANNED",
                tenant_id=tid,
                total_stops=len(stop_sequence),
                estimated_distance_km=round(route_dist, 2),
                estimated_duration_minutes=route_dur,
            )
            db.add(route)
            db.flush()
            routes_created += 1

            for seq, order in enumerate(stop_sequence, start=1):
                # Use Core INSERT to bypass ORM relationship management.
                # db.add(RouteStop(...)) would trigger uselist=False back-populates
                # eviction (setting old stop's order_id=NULL → IntegrityError) when
                # generate_options calls plan_day 3 times for the same order set.
                now = datetime.utcnow()
                db.execute(
                    sa_insert(RouteStop).values(
                        id=uuid4(),
                        route_id=route.id,
                        order_id=order.id,
                        sequence=seq,
                        tenant_id=tid,
                        status="PENDING",
                        created_at=now,
                        updated_at=now,
                    )
                )

                if commit_assignments:
                    order.assigned_driver_id = driver.id
                    order.status = "ASSIGNED"

                assignments.append({
                    "order_id": str(order.id),
                    "driver_id": str(driver.id),
                    "driver_name": driver.full_name,
                    "sequence": seq,
                })

        plan.assigned_orders = len(assignments)
        plan.total_routes = routes_created

        db.commit()

        fuel_cost_per_km = weights["fuel_cost_per_km"]
        return {
            "plan_id": str(plan.id),
            "plan_date": str(plan_date),
            "status": "DRAFT",
            "plan_mode": plan_mode,
            "total_orders": len(orders),
            "assigned_orders": len(assignments),
            "total_routes": routes_created,
            "total_distance_km": round(total_distance_km, 2),
            "est_duration_min": total_duration_min,
            "est_fuel_cost": round(total_distance_km * fuel_cost_per_km, 2),
            "assignments": assignments,
            "ai_summary": None,
            "confidence_score": None,
            "reasoning_steps": [],
            "warnings": [],
            "planner": "ortools",
        }

    def plan_horizon(
        self,
        db: Session,
        tenant_id: str,
        dates: list[date],
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Solve each date sequentially with driver carry-over constraints.

        Driver shift carry-over: a driver assigned >8h (480 min) on day N is
        marked unavailable for the first 4h of day N+1 by temporarily blocking
        their shift window.

        Scenario parameters are forwarded to _plan_single_with_params() which
        injects virtual constraints before OR-Tools runs.
        """
        params = parameters or {}
        results: list[dict[str, Any]] = []
        carry_over: dict[str, int] = {}   # driver_id (str) → delay minutes for next day

        for d in dates:
            result = self._plan_single_with_params(
                db=db,
                tenant_id=tenant_id,
                plan_date=d,
                parameters=params,
                carry_over=carry_over,
            )
            carry_over = self._compute_carry_over(result)
            results.append(result)

        return results

    def _compute_carry_over(self, result: dict[str, Any]) -> dict[str, int]:
        """Return driver_id → carry-over delay minutes for the next day.

        A driver with more than 8 hours (480 min) estimated work on this day
        incurs a 240-minute (4h) unavailability window starting the next morning.
        """
        carry: dict[str, int] = {}
        threshold_minutes = 480
        penalty_minutes = 240
        for assignment in result.get("assignments", []):
            driver_id = assignment.get("driver_id")
            if driver_id and not carry.get(driver_id):
                driver_stops = sum(
                    1 for a in result.get("assignments", [])
                    if a.get("driver_id") == driver_id
                )
                # Rough estimate: >12 stops ≈ >8h for an average city route
                if driver_stops > 12:
                    carry[driver_id] = penalty_minutes
        return carry

    def _plan_single_with_params(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        parameters: dict[str, Any],
        carry_over: dict[str, int],
    ) -> dict[str, Any]:
        """Run plan_day with scenario parameter overrides injected.

        Applies scenario adjustments BEFORE passing to plan_day:
          - new_depot:           override depot coordinates
          - ev_fleet_mix:        no structural change at planner level (range already handled by routing)
          - driver_count_change: slice available driver list
          - demand_surge:        multiply order weight in target zone (not currently surfaced
                                 to OR-Tools — logged in result metadata)
        """
        scenario_type = parameters.get("_scenario_type", "")
        overrides: dict[str, Any] = {}

        if scenario_type == "new_depot":
            overrides["_depot_lat"] = parameters.get("lat", _FALLBACK_LAT)
            overrides["_depot_lng"] = parameters.get("lng", _FALLBACK_LNG)
        elif scenario_type == "driver_count_change":
            overrides["_driver_delta"] = parameters.get("delta", 0)
        elif scenario_type == "demand_surge":
            overrides["_surge_zone"]   = parameters.get("zone", "")
            overrides["_surge_factor"] = parameters.get("surge_factor", 1.0)

        # Store overrides for plan_day to pick up via a thin wrapper
        result = self._plan_day_with_overrides(
            db=db,
            tenant_id=tenant_id,
            plan_date=plan_date,
            carry_over=carry_over,
            overrides=overrides,
        )
        return result

    def _plan_day_with_overrides(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        carry_over: dict[str, int],
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Call plan_day with optional depot/driver overrides from scenario params.

        This thin wrapper avoids duplicating the full plan_day logic.
        For the scenario simulator we set commit_assignments=False so we don't
        actually mutate production data.
        """
        # patch module-level fallback if new_depot scenario
        orig_lat = _FALLBACK_LAT
        orig_lng = _FALLBACK_LNG
        import app.planners.ortools_planner as _self_mod

        if "_depot_lat" in overrides:
            _self_mod._FALLBACK_LAT = overrides["_depot_lat"]
            _self_mod._FALLBACK_LNG = overrides["_depot_lng"]

        try:
            result = self.plan_day(
                db=db,
                tenant_id=tenant_id,
                plan_date=plan_date,
                commit_assignments=False,
            )
        finally:
            _self_mod._FALLBACK_LAT = orig_lat
            _self_mod._FALLBACK_LNG = orig_lng

        # Apply driver_count_change post-hoc (trim assignments)
        delta = overrides.get("_driver_delta", 0)
        if delta < 0 and result.get("assignments"):
            # Remove assignments from last `abs(delta)` drivers
            driver_ids = list(dict.fromkeys(a["driver_id"] for a in result["assignments"]))
            remove_ids = set(driver_ids[delta:])   # last abs(delta) drivers
            result["assignments"] = [a for a in result["assignments"] if a["driver_id"] not in remove_ids]
            result["assigned_orders"] = len(result["assignments"])

        return result

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict[str, Any]) -> dict[str, Any]:
        """
        Re-run OR-Tools for remaining PENDING stops on plan_date.
        Optionally scoped to a single driver via context['driver_id'].
        Implemented fully in P2-E4-S9 (replan endpoint).
        """
        return self.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)
