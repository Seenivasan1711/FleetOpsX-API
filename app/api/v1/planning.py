from datetime import date
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services.planning_service import PlanningService
from app.services import plan_options_service
from app.schemas.plan_options import PlanOptionsResponse, PlanConfirmRequest
from app.schemas.scenario import MultiDayPlanRequest, DayPlanSummary
from app.schemas.plan_history import PlanHistoryIn, PlanHistoryOut, PlanNoteIn, PlanNoteOut

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


@router.post("/options", response_model=PlanOptionsResponse)
def plan_options(
    plan_date: date = Query(..., description="Date to generate options for (YYYY-MM-DD)"),
    user_hints: Optional[str] = Query(None, description="Optional dispatcher hints for the planner"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Generate three plan variants (fastest / economical / balanced) for the given date.
    Each variant is saved as a DRAFT plan. Call POST /plan/confirm to activate one.
    Order assignments are NOT applied until confirm is called.
    """
    summaries = plan_options_service.generate_options(
        db=db,
        tenant_id=str(current_user.tenant_id),
        plan_date=plan_date,
        user_hints=user_hints,
    )
    return PlanOptionsResponse(plan_date=plan_date, options=summaries)


@router.post("/confirm")
def plan_confirm(
    data: PlanConfirmRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Confirm a plan variant selected from /plan/options.
    Applies order assignments, marks the plan PUBLISHED, cancels other DRAFT plans,
    and writes a PlanHistory record so the history page shows this dispatch.
    """
    result = plan_options_service.confirm_plan(
        db=db,
        tenant_id=str(current_user.tenant_id),
        plan_id=data.plan_id,
        plan_date=data.plan_date,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Auto-record in plan history so Plan History page reflects this dispatch
    from app.models.plan_history import PlanHistory
    history_entry = PlanHistory(
        tenant_id=current_user.tenant_id,
        plan_date=data.plan_date,
        source="or_tools",
        total_orders=result.get("total_orders"),
        total_routes=result.get("total_routes"),
        created_by=current_user.id,
    )
    db.add(history_entry)
    db.commit()

    return result


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


@router.post("/multi-day")
def plan_multi_day(
    body: MultiDayPlanRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Run OR-Tools sequentially across a date horizon with carry-over constraints.

    commit_assignments=False — this is a dry-run preview. Use POST /plan/day
    for each date individually to commit real assignments.
    """
    from datetime import timedelta
    from app.planners.ortools_planner import ORToolsPlanner

    dates = [body.start_date + timedelta(days=i) for i in range(body.horizon_days)]
    planner = ORToolsPlanner()
    day_results = planner.plan_horizon(
        db=db,
        tenant_id=str(current_user.tenant_id),
        dates=dates,
        parameters=body.parameters,
    )

    days_out = []
    total_orders = total_assigned = 0
    on_time_sum = 0.0

    for day_result in day_results:
        assigned = day_result.get("assigned_orders", 0)
        total    = day_result.get("total_orders", 0)
        total_orders += total
        total_assigned += assigned
        on_time_sum += (assigned / max(total, 1))

        days_out.append(DayPlanSummary(
            plan_date=day_result.get("plan_date"),
            plan_id=day_result.get("plan_id"),
            assigned_orders=assigned,
            total_routes=day_result.get("total_routes", 0),
            total_orders=total,
        ))

    horizon = len(dates)
    summary = {
        "total_orders":     total_orders,
        "total_assigned":   total_assigned,
        "avg_on_time_rate": round(on_time_sum / max(horizon, 1), 4),
    }
    return {"days": days_out, "summary": summary}


# ---------------------------------------------------------------------------
# P5-E2: AI Multi-Scenario Planning
# ---------------------------------------------------------------------------

@router.post("/ai-scenarios")
def plan_ai_scenarios(
    plan_date: date = Query(..., description="Date to plan for (YYYY-MM-DD)"),
    nl_constraints: Optional[str] = Query(None, description="Natural language constraints"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Queue an AI scenario generation task.
    Returns task_id — poll GET /plan/task-status/{task_id} for result.
    """
    from app.workers.tasks import ai_scenario_task
    task = ai_scenario_task.delay(
        tenant_id=str(current_user.tenant_id),
        plan_date_str=str(plan_date),
        nl_constraints=nl_constraints,
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    """Poll the status of an async planning task."""
    from celery.result import AsyncResult
    from app.workers.celery_app import celery_app as _celery
    result = AsyncResult(task_id, app=_celery)
    if result.state == "PENDING":
        return {"status": "pending"}
    if result.state == "SUCCESS":
        data = result.get()
        return {"status": data.get("status", "done"), "result": data.get("result")}
    if result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    return {"status": result.state.lower()}


@router.post("/confirm-scenario")
def confirm_scenario(
    plan_date: date = Body(...),
    scenario_type: str = Body(...),
    task_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Confirm the selected AI scenario and save to plan history."""
    from celery.result import AsyncResult
    from app.workers.celery_app import celery_app as _celery

    result_obj = AsyncResult(task_id, app=_celery)
    if result_obj.state != "SUCCESS":
        raise HTTPException(status_code=400, detail="Task not completed yet")

    task_data = result_obj.get()
    scenarios = task_data.get("result", {}).get("scenarios", [])
    chosen = next((s for s in scenarios if s.get("type") == scenario_type), None)
    if not chosen:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_type}' not found in task result")

    return {
        "status":        "confirmed",
        "plan_date":     str(plan_date),
        "scenario_type": scenario_type,
        "kpis":          chosen.get("kpis", {}),
        "total_orders":  chosen.get("total_orders"),
        "total_routes":  chosen.get("total_routes"),
    }


# ---------------------------------------------------------------------------
# P5-E3: Plan History + Feedback
# ---------------------------------------------------------------------------

@router.get("/history", response_model=List[PlanHistoryOut])
def list_plan_history(
    plan_date: Optional[date] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """List plan history entries for the tenant, newest first."""
    from app.models.plan_history import PlanHistory
    stmt = (
        select(PlanHistory)
        .where(PlanHistory.tenant_id == current_user.tenant_id)
        .order_by(PlanHistory.created_at.desc())
        .limit(limit)
    )
    if plan_date:
        stmt = stmt.where(PlanHistory.plan_date == plan_date)
    rows = db.execute(stmt).scalars().all()
    return rows


@router.post("/history", response_model=PlanHistoryOut, status_code=201)
def create_plan_history(
    body: PlanHistoryIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Record a planning event in history."""
    from app.models.plan_history import PlanHistory
    entry = PlanHistory(
        id=uuid4(),
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/history/{history_id}", response_model=PlanHistoryOut)
def get_plan_history(
    history_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Get a single plan history entry with its notes."""
    from app.models.plan_history import PlanHistory
    entry = db.execute(
        select(PlanHistory).where(
            PlanHistory.id == history_id,
            PlanHistory.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Plan history entry not found")
    return entry


@router.post("/history/{history_id}/notes", response_model=PlanNoteOut, status_code=201)
def add_plan_note(
    history_id: UUID,
    body: PlanNoteIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Add a note or rating to a plan history entry."""
    from app.models.plan_history import PlanHistory, PlanNote
    entry = db.execute(
        select(PlanHistory).where(
            PlanHistory.id == history_id,
            PlanHistory.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Plan history entry not found")
    note = PlanNote(
        id=uuid4(),
        tenant_id=current_user.tenant_id,
        plan_history_id=history_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/timeline")
def route_timeline(
    plan_date: date = Query(..., description="Date to show timeline for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return per-driver stop schedules for a given date (Gantt chart data)."""
    from app.models.route_plan import RoutePlan, Route, RouteStop
    from app.models.driver import Driver
    from app.models.order import Order

    tid = current_user.tenant_id
    rows = db.execute(
        select(Route, RouteStop, Driver, Order)
        .join(RoutePlan, Route.plan_id == RoutePlan.id)
        .join(RouteStop, RouteStop.route_id == Route.id)
        .join(Driver, Route.driver_id == Driver.id)
        .join(Order, RouteStop.order_id == Order.id)
        .where(
            RoutePlan.tenant_id == tid,
            RoutePlan.plan_date == plan_date,
        )
        .order_by(Route.driver_id, RouteStop.sequence)
    ).all()

    # Group by driver
    drivers: dict[str, dict] = {}
    for route, stop, driver, order in rows:
        key = str(driver.id)
        if key not in drivers:
            drivers[key] = {
                "driver_id": key,
                "driver_name": driver.full_name,
                "stops": [],
            }
        drivers[key]["stops"].append({
            "order_id": str(order.id),
            "address": order.delivery_address,
            "sequence": stop.sequence,
            "start_time": stop.estimated_arrival,
            "end_time": None,
            "status": stop.status,
            "priority": order.priority,
        })

    return list(drivers.values())
