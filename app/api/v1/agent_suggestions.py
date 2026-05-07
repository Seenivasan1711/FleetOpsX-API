"""
Agent Suggestions API — P3-E2

GET  /agent/suggestions?plan_date=YYYY-MM-DD&status=PENDING
PATCH /agent/suggestions/{id}
  - ACCEPTED + REPLAN_DRIVER → triggers scoped replan via PlanningService
  - ACCEPTED + EARLY_SLA_WARNING → logs notification (SMS/email in Phase 4)
  - DISMISSED → marks dismissed
"""
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.agent_suggestion import AgentSuggestion
from app.schemas.agent_suggestion import AgentSuggestionOut, AgentSuggestionUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent Suggestions"])


@router.get("/suggestions", response_model=list[AgentSuggestionOut])
def list_suggestions(
    plan_date: date = Query(..., description="Date to filter suggestions (YYYY-MM-DD)"),
    status: str | None = Query(None, description="Filter by status: PENDING | ACCEPTED | DISMISSED"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return agent suggestions for a given plan date, optionally filtered by status."""
    tid = current_user.tenant_id

    stmt = select(AgentSuggestion).where(
        AgentSuggestion.tenant_id == tid,
        AgentSuggestion.plan_date == plan_date,
    )
    if status:
        stmt = stmt.where(AgentSuggestion.status == status.upper())

    rows = db.execute(stmt.order_by(AgentSuggestion.created_at.desc())).scalars().all()
    return rows


@router.patch("/suggestions/{suggestion_id}", response_model=AgentSuggestionOut)
def update_suggestion(
    suggestion_id: UUID,
    body: AgentSuggestionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Accept or dismiss an agent suggestion.

    Accepting a REPLAN_DRIVER suggestion triggers a scoped replan for that driver.
    Accepting an EARLY_SLA_WARNING logs a notification (future: SMS/email).
    """
    tid = current_user.tenant_id
    new_status = body.status.upper()

    if new_status not in ("ACCEPTED", "DISMISSED"):
        raise HTTPException(status_code=422, detail="status must be ACCEPTED or DISMISSED")

    suggestion = db.execute(
        select(AgentSuggestion).where(
            AgentSuggestion.id == suggestion_id,
            AgentSuggestion.tenant_id == tid,
        )
    ).scalar_one_or_none()

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    before = {"status": suggestion.status}
    suggestion.status = new_status
    suggestion.acted_by = current_user.email or str(current_user.id)

    if new_status == "ACCEPTED":
        _handle_accepted(suggestion=suggestion, db=db, tenant_id=str(tid))

    from app.services.audit_service import log_action
    log_action(
        db=db,
        actor=current_user,
        action=f"suggestion.{new_status.lower()}",
        resource_type="agent_suggestion",
        resource_id=suggestion_id,
        before=before,
        after={"status": new_status},
        ai_context={
            "suggestion_type": suggestion.suggestion_type,
            "plan_date": str(suggestion.plan_date),
        },
    )

    db.commit()
    db.refresh(suggestion)
    return suggestion


# ─── Accept handlers ─────────────────────────────────────────────────────────

def _handle_accepted(suggestion: AgentSuggestion, db: Session, tenant_id: str) -> None:
    ctx = suggestion.context or {}

    if suggestion.suggestion_type == "REPLAN_DRIVER":
        driver_id_str = ctx.get("driver_id")
        if driver_id_str:
            _trigger_driver_replan(
                db=db,
                tenant_id=tenant_id,
                plan_date=suggestion.plan_date,
                driver_id=UUID(driver_id_str),
            )

    elif suggestion.suggestion_type == "EARLY_SLA_WARNING":
        _log_sla_notification(suggestion=suggestion, ctx=ctx)


def _trigger_driver_replan(db: Session, tenant_id: str, plan_date: date, driver_id: UUID) -> None:
    """Reset PENDING stops for the driver and re-run OR-Tools."""
    from sqlalchemy import update as sa_update
    from app.models.order import Order
    from app.models.route_plan import Route, RouteStop
    from app.planners.ortools_planner import ORToolsPlanner

    pending_stops = db.execute(
        select(RouteStop)
        .join(Route, RouteStop.route_id == Route.id)
        .where(
            RouteStop.tenant_id == UUID(tenant_id),
            Route.driver_id == driver_id,
            RouteStop.status == "PENDING",
        )
    ).scalars().all()

    order_ids = [s.order_id for s in pending_stops]
    if order_ids:
        db.execute(
            sa_update(Order)
            .where(Order.id.in_(order_ids))
            .values(status="PENDING", assigned_driver_id=None)
        )
        db.flush()

    try:
        result = ORToolsPlanner().plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)
        logger.info(
            "Replan triggered by REPLAN_DRIVER suggestion: driver=%s → %d orders assigned",
            driver_id, result.get("assigned_orders", 0),
        )
    except Exception as exc:
        logger.error("Replan failed for driver=%s: %s", driver_id, exc, exc_info=True)


def _log_sla_notification(suggestion: AgentSuggestion, ctx: dict) -> None:
    """Log SLA warning notification. SMS/email integration is Phase 4."""
    logger.info(
        "SLA WARNING ACCEPTED: driver=%s stop=%s order=%s — notification logged (Phase 4: SMS/email)",
        ctx.get("driver_id"), ctx.get("stop_id"), ctx.get("order_id"),
    )
