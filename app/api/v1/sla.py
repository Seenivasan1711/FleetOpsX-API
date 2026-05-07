"""
SLA Risk endpoint — P2-E7

GET /sla/at-risk?plan_date=YYYY-MM-DD
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services.sla_service import get_at_risk_stops

router = APIRouter(prefix="/sla", tags=["SLA"])


@router.get("/at-risk")
def at_risk_stops(
    plan_date: date = Query(..., description="Date to check (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Return stops at risk of missing their delivery time window.

    A stop is at risk when:
      current_time + estimated_travel_time > time_window_end

    Travel time is based on the driver's last GPS ping (Redis cache).
    Stops without GPS data or without a time_window_end are excluded.
    """
    return get_at_risk_stops(
        db=db,
        tenant_id=str(current_user.tenant_id),
        plan_date=plan_date,
    )
