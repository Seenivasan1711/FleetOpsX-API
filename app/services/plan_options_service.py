from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.planners.cost_model import PLAN_MODES
from app.models.route_plan import RoutePlan, Route, RouteStop
from app.models.order import Order
from app.schemas.plan_options import PlanSummary


def generate_options(db: Session, tenant_id: str, plan_date: date) -> list[PlanSummary]:
    """
    Run OR-Tools with each plan_mode without committing order assignments.
    Returns a summary for each mode so the dispatcher can compare and confirm one.
    """
    from app.planners.ortools_planner import ORToolsPlanner
    planner = ORToolsPlanner()
    summaries: list[PlanSummary] = []

    for mode in PLAN_MODES:
        result = planner.plan_day(
            db=db,
            tenant_id=tenant_id,
            plan_date=plan_date,
            plan_mode=mode,
            commit_assignments=False,
        )
        if result.get("plan_id"):
            summaries.append(PlanSummary(
                mode=mode,
                plan_id=result["plan_id"],
                total_distance_km=result.get("total_distance_km", 0.0),
                est_duration_min=result.get("est_duration_min", 0),
                est_fuel_cost=result.get("est_fuel_cost", 0.0),
                orders_covered=result.get("assigned_orders", 0),
            ))

    return summaries


def confirm_plan(db: Session, tenant_id: str, plan_id: UUID, plan_date: date) -> dict:
    """
    Apply order assignments from the selected plan, mark it PUBLISHED,
    and CANCEL other DRAFT plans for the same date.
    """
    tid = UUID(tenant_id)

    plan = db.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.tenant_id == tid,
        )
    ).scalar_one_or_none()

    if plan is None:
        return None

    # Apply order assignments from this plan's routes
    routes = db.execute(
        select(Route).where(Route.plan_id == plan_id, Route.tenant_id == tid)
    ).scalars().all()

    assignments = []
    for route in routes:
        stops = db.execute(
            select(RouteStop).where(
                RouteStop.route_id == route.id,
                RouteStop.tenant_id == tid,
            ).order_by(RouteStop.sequence)
        ).scalars().all()

        for stop in stops:
            order = db.get(Order, stop.order_id)
            if order:
                order.assigned_driver_id = route.driver_id
                order.status = "ASSIGNED"
                assignments.append({
                    "order_id": str(order.id),
                    "driver_id": str(route.driver_id),
                    "sequence": stop.sequence,
                })

    # Publish selected plan
    plan.status = "PUBLISHED"

    # Cancel other DRAFT plans for same date
    db.execute(
        update(RoutePlan)
        .where(
            RoutePlan.tenant_id == tid,
            RoutePlan.plan_date == plan_date,
            RoutePlan.id != plan_id,
            RoutePlan.status == "DRAFT",
        )
        .values(status="CANCELLED")
    )

    db.commit()

    return {
        "plan_id": str(plan.id),
        "plan_date": str(plan_date),
        "status": "PUBLISHED",
        "total_orders": plan.total_orders,
        "assigned_orders": plan.assigned_orders,
        "total_routes": plan.total_routes,
        "assignments": assignments,
    }
