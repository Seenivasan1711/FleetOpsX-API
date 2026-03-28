from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import require_dispatcher, get_db
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/plan", tags=["Planning"])


@router.post("/day")
def plan_day(
    plan_date: date = Query(..., description="Date to plan for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Phase 1: Rule-based planner.
    Assigns unassigned orders to available drivers for the given date.
    Returns a DRAFT plan — dispatcher must confirm before it goes live.
    """
    service = PlanningService()
    return service.plan_day(db=db, tenant_id=str(current_user.tenant_id), plan_date=plan_date)
