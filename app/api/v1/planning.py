from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/plan", tags=["Planning"])


@router.post("/day")
def plan_day(
    plan_date: date = Query(..., description="Date to plan for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Generate a dispatch plan for the given date.

    Planner used is controlled by PLANNER_TYPE in .env:
      - rule_based  →  greedy nearest-driver (Phase 1)
      - ortools     →  VRPTW solver, respects time windows + capacity (Phase 2)
      - langgraph   →  LLM agent wrapping OR-Tools with explanations (Phase 2)

    Returns a DRAFT plan — dispatcher reviews before publishing.
    """
    service = PlanningService()
    return service.plan_day(db=db, tenant_id=str(current_user.tenant_id), plan_date=plan_date)


@router.post("/replan")
def replan(
    plan_date: date = Body(...),
    driver_id: Optional[UUID] = Body(None, description="Replan single driver; omit for full fleet"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Re-optimise remaining (PENDING) stops for one driver or the full fleet.

    - Resets matching PENDING RouteStops' orders back to PENDING.
    - Re-runs OR-Tools to produce a new DRAFT RoutePlan.
    - Returns same shape as /plan/day plus `"replan": true`.
    """
    from app.models.order import Order
    from app.models.route_plan import Route, RouteStop
    from app.planners.ortools_planner import ORToolsPlanner

    tid = current_user.tenant_id

    # Find route_stop rows that are still PENDING for this tenant
    stmt = (
        select(RouteStop)
        .join(Route, RouteStop.route_id == Route.id)
        .where(
            RouteStop.tenant_id == tid,
            RouteStop.status == "PENDING",
        )
    )
    if driver_id is not None:
        stmt = stmt.where(Route.driver_id == driver_id)

    pending_stops = db.execute(stmt).scalars().all()
    order_ids = [s.order_id for s in pending_stops]

    if order_ids:
        db.execute(
            update(Order)
            .where(Order.id.in_(order_ids))
            .values(status="PENDING", assigned_driver_id=None)
        )
        db.commit()

    result = ORToolsPlanner().plan_day(db=db, tenant_id=str(tid), plan_date=plan_date)
    result["replan"] = True
    return result
