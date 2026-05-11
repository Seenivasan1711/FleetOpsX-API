"""
Analytics API endpoints — P3-E1

GET  /analytics/kpis?since=YYYY-MM-DD&until=YYYY-MM-DD
GET  /analytics/driver-performance?since=YYYY-MM-DD
POST /analytics/run-etl?plan_date=YYYY-MM-DD
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services.analytics_service import get_kpis, get_driver_performance, run_etl, get_kpi_trend

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/kpis")
def analytics_kpis(
    since: date = Query(default=None, description="Start date (YYYY-MM-DD), defaults to 30 days ago"),
    until: date = Query(default=None, description="End date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return aggregated delivery KPIs for the given date range."""
    today = date.today()
    since = since or (today - timedelta(days=30))
    until = until or today
    return get_kpis(db=db, tenant_id=str(current_user.tenant_id), since=since, until=until)


@router.get("/driver-performance")
def driver_performance(
    since: date = Query(default=None, description="Start date (YYYY-MM-DD), defaults to 30 days ago"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return per-driver performance aggregates since the given date."""
    since = since or (date.today() - timedelta(days=30))
    return get_driver_performance(db=db, tenant_id=str(current_user.tenant_id), since=since)


@router.get("/kpi-trend")
def kpi_trend(
    days: int = Query(default=7, ge=1, le=90, description="Number of days of history"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return per-day KPI values for dashboard sparklines."""
    return get_kpi_trend(db=db, tenant_id=str(current_user.tenant_id), days=days)


@router.post("/run-etl")
def trigger_etl(
    plan_date: date = Query(..., description="Date to run ETL for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Manually trigger the analytics ETL for a specific date (dispatcher only)."""
    result = run_etl(db=db, tenant_id=str(current_user.tenant_id), etl_date=plan_date)
    return {"plan_date": str(plan_date), **result}
